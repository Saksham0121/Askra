"""
Agentic Pipeline.

Full end-to-end orchestrator for the agentic RAG system.

Flow
----
Query
  → Guardrail (block harmful/injections)
  → QueryRewriter  ← RAG/UNKNOWN intents only (skipped for chat & code — saves ~1-2 s)
  → Direct RAG toggle check
      YES → RAGTool directly
      NO  → AgentRouter → tool selection → tool.execute()
  → ValidationLayer  ← RAG only (skipped for chat & code — saves ~1-2 s)
  → ReflectionLayer (up to 2 retries if score < threshold, RAG only)
  → PipelineResult (answer + confidence + source label + citations)

Speed notes
-----------
  • chat / code paths skip QueryRewriter and ValidationLayer entirely.
  • Both are no-ops for non-RAG answers and only add latency.
  • The fast-path uses _fast_path_validation() (fixed score 8.0, no LLM call).
"""

from __future__ import annotations

import time

from src.agent.base_tool import BaseTool
from src.agent.router import AgentRouter
from src.core.config import ApplicationConfig
from src.core.logging import LoggerManager
from src.llm import OllamaManager
from src.pipeline.online_pipeline import OnlinePipeline
from src.pipeline.pipeline_result import AnswerSource, PipelineResult
from src.reflection.reflector import Reflector
from src.tools.chat_tool import ChatTool
from src.tools.code_tool import CodeTool
from src.tools.rag_tool import RAGTool
from src.validation.guardrail import Guardrail
from src.validation.models import QueryIntent
from src.validation.query_rewriter import QueryRewriter
from src.validation.validation_layer import ValidationLayer, ValidationResult

# Intents that benefit from query rewriting (retrieval-bound paths only).
_REWRITE_INTENTS: frozenset[QueryIntent] = frozenset({
    QueryIntent.DOCUMENT,
    QueryIntent.UNKNOWN,
})

# Tool names whose answers don't need LLM-as-judge validation.
_NO_VALIDATE_TOOLS: frozenset[str] = frozenset({"chat", "code"})


# Returns pre-validated result for fast chat/code/RAG path.
def _fast_path_validation(tool_name: str = "rag") -> ValidationResult:
    """Return a pre-built passing ValidationResult for fast paths.
    Skips the LLM-as-judge round-trip to cut latency.
    has_citations reflects whether the tool actually cites sources."""
    is_rag = tool_name == "rag"
    return ValidationResult(
        confidence_score=8.0,
        correctness=8.0,
        completeness=8.0,
        has_citations=is_rag,
        reasoning=(
            "Validation skipped — Direct RAG fast path."
            if is_rag
            else f"Validation skipped — {tool_name} tool (no retrieved context)."
        ),
        threshold=5.5,
    )

logger = LoggerManager.get_logger()


# Orchestrates the agentic RAG workflow process.
class AgenticPipeline:
    """
    Orchestrates the full agentic RAG flow.
    """

    # Sets up and initializes core tool dependencies.
    def __init__(
        self,
        guardrail: Guardrail,
        router: AgentRouter,
        chat_tool: ChatTool,
        code_tool: CodeTool,
        rag_tool: RAGTool,
        validator: ValidationLayer,
        reflector: Reflector,
        query_rewriter: QueryRewriter,
    ) -> None:
        self.guardrail      = guardrail
        self.router         = router
        self.chat_tool      = chat_tool
        self.code_tool      = code_tool
        self.rag_tool       = rag_tool
        self.validator      = validator
        self.reflector      = reflector
        self.query_rewriter = query_rewriter

        self._tool_map: dict[str, BaseTool] = {
            "chat": chat_tool,
            "code": code_tool,
            "rag":  rag_tool,
        }

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    # Executes the complete agentic pipeline process.
    def run(
        self,
        query: str,
        direct_rag: bool = False,
    ) -> PipelineResult:
        """
        Execute the full agentic pipeline.

        Parameters
        ----------
        query      : User's question.
        direct_rag : If True, skip the agent and go directly to the RAG tool.

        Returns
        -------
        PipelineResult
        """

        start = time.perf_counter()

        logger.info(f"AgenticPipeline.run | direct_rag={direct_rag} | query={query!r}")

        # ----------------------------------------------------------------
        # Step 1 — Guardrail
        # ----------------------------------------------------------------

        guard = self.guardrail.validate(query)

        if not guard.allowed:
            logger.warning(f"Query blocked by guardrail: {guard.reason}")
            return PipelineResult(
                answer=f"⛔ {guard.reason}",
                answer_source=AnswerSource.LLM,
                confidence_score=0.0,
                validation_reasoning=guard.reason,
                latency_ms=self._elapsed(start),
            )

        normalized_query = guard.normalized_query

        # ----------------------------------------------------------------
        # Step 1.5 — Query Rewriting (RAG/UNKNOWN intents only)
        # Skipped for GREETING / GENERAL_CHAT / CODE — saves ~1-2 s per call.
        # The rewriter is a retrieval optimizer; it adds zero value for direct
        # LLM answers where no vector search is performed.
        # ----------------------------------------------------------------

        if guard.intent in _REWRITE_INTENTS or direct_rag:
            rewrite = self.query_rewriter.rewrite(normalized_query)
            if rewrite.was_rewritten:
                logger.info(
                    f"AgenticPipeline: query rewritten "
                    f"{normalized_query!r} → {rewrite.rewritten_query!r}"
                )
            normalized_query = rewrite.rewritten_query
        else:
            logger.info(
                f"AgenticPipeline: QueryRewriter skipped "
                f"(intent={guard.intent.value!r} — non-retrieval path)."
            )

        # ----------------------------------------------------------------
        # Step 2 — Tool selection
        # ----------------------------------------------------------------

        if direct_rag:
            tool_name = "rag"
            tool = self.rag_tool
            logger.info("AgenticPipeline: Direct RAG mode — skipping router.")
        else:
            tool_name = self.router.route(normalized_query)
            tool = self._tool_map.get(tool_name, self.rag_tool)
            logger.info(f"AgenticPipeline: Router selected '{tool_name}'.")

        # ----------------------------------------------------------------
        # Step 3 — Tool execution
        # ----------------------------------------------------------------

        try:
            tool_result = tool.execute(normalized_query)
        except Exception as exc:
            logger.error(f"Tool execution failed: {exc}")
            return PipelineResult(
                answer=f"Sorry, an error occurred while generating your answer: {exc}",
                answer_source=AnswerSource.LLM,
                confidence_score=0.0,
                validation_reasoning=str(exc),
                latency_ms=self._elapsed(start),
            )

        # ----------------------------------------------------------------
        # Step 4 — Validation
        # Skipped for Direct RAG, chat, and code tools — saves ~1-2 s per call.
        # Validation is only meaningful when retrieved context exists to verify.
        # ----------------------------------------------------------------

        is_fast_path = direct_rag or tool_name in _NO_VALIDATE_TOOLS

        if is_fast_path:
            logger.info(
                f"AgenticPipeline: Validation skipped "
                f"(tool={tool_name!r} — fast path)."
            )
            validation = _fast_path_validation(tool_name)
        else:
            validation = self.validator.validate(
                query=normalized_query,
                answer=tool_result.answer,
                context=tool_result.context,
            )

        # ----------------------------------------------------------------
        # Step 5 — Reflection (RAG only, only if score < threshold)
        # ----------------------------------------------------------------

        iterations = 1

        if not is_fast_path and not validation.passed:
            logger.info(
                f"AgenticPipeline: score {validation.confidence_score:.1f} "
                f"< threshold {self.validator.threshold} — entering reflection."
            )
            tool_result, validation, iterations = self.reflector.reflect(
                tool=tool,
                query=normalized_query,
                initial_result=tool_result,
                initial_validation=validation,
            )

        # ----------------------------------------------------------------
        # Step 6 — Build final result
        # ----------------------------------------------------------------

        result = PipelineResult(
            answer=tool_result.answer,
            sources=tool_result.sources,
            confidence_score=validation.confidence_score,
            answer_source=tool_result.answer_source,
            validation_reasoning=validation.reasoning,
            iterations=iterations,
            latency_ms=self._elapsed(start),
        )

        logger.info(
            f"AgenticPipeline completed: "
            f"score={result.confidence_score:.1f}, "
            f"source={result.answer_source}, "
            f"tool={tool_name!r}, "
            f"iterations={iterations}, "
            f"latency={result.latency_ms}ms"
        )

        return result

    # Executes the agentic pipeline stream process.
    def run_stream(
        self,
        query: str,
        direct_rag: bool = False,
    ):
        """
        Execute the full agentic pipeline and yield a stream of events.
        """
        start = time.perf_counter()
        logger.info(f"AgenticPipeline.run_stream | direct_rag={direct_rag} | query={query!r}")

        # Step 1: Guardrail
        yield {"type": "status", "message": "Checking safety guidelines..."}
        guard = self.guardrail.validate(query)

        if not guard.allowed:
            logger.warning(f"Query blocked by guardrail: {guard.reason}")
            yield {"type": "result", "data": PipelineResult(
                answer=f"⛔ {guard.reason}",
                answer_source=AnswerSource.LLM,
                confidence_score=0.0,
                validation_reasoning=guard.reason,
                latency_ms=self._elapsed(start),
            )}
            return

        normalized_query = guard.normalized_query

        # Step 1.5: Query Rewriting — RAG/UNKNOWN intents only.
        # Skipped for GREETING / GENERAL_CHAT / CODE to save ~1-2 s per call.
        if guard.intent in _REWRITE_INTENTS or direct_rag:
            yield {"type": "status", "message": "Refining your query..."}
            rewrite = self.query_rewriter.rewrite(normalized_query)
            if rewrite.was_rewritten:
                logger.info(
                    f"AgenticPipeline: query rewritten "
                    f"{normalized_query!r} → {rewrite.rewritten_query!r}"
                )
            normalized_query = rewrite.rewritten_query
        else:
            logger.info(
                f"AgenticPipeline: QueryRewriter skipped "
                f"(intent={guard.intent.value!r} — non-retrieval path)."
            )

        # Step 2: Tool selection
        if direct_rag:
            tool_name = "rag"
            tool = self.rag_tool
            logger.info("AgenticPipeline: Direct RAG mode — skipping router.")
        else:
            yield {"type": "status", "message": "Deciding how to answer..."}
            tool_name = self.router.route(normalized_query)
            tool = self._tool_map.get(tool_name, self.rag_tool)
            logger.info(f"AgenticPipeline: Router selected '{tool_name}'.")

        # Step 3: Tool execution (streaming)
        try:
            stream = tool.execute_stream(normalized_query)
            tool_result = None

            for event in stream:
                if event["type"] == "result":
                    tool_result = event["data"]
                else:
                    yield event

        except Exception as exc:
            logger.error(f"Tool execution failed: {exc}")
            yield {"type": "result", "data": PipelineResult(
                answer=f"Sorry, an error occurred while generating your answer: {exc}",
                answer_source=AnswerSource.LLM,
                confidence_score=0.0,
                validation_reasoning=str(exc),
                latency_ms=self._elapsed(start),
            )}
            return

        if tool_result is None:
            return

        # Step 4: Validation — skipped for Direct RAG, chat, and code tools.
        # Validation only adds value when retrieved context exists to verify.
        is_fast_path = direct_rag or tool_name in _NO_VALIDATE_TOOLS

        if is_fast_path:
            logger.info(
                f"AgenticPipeline: Validation skipped "
                f"(tool={tool_name!r} — fast path)."
            )
            validation = _fast_path_validation(tool_name)
        else:
            yield {"type": "status", "message": "Evaluating answer quality..."}
            validation = self.validator.validate(
                query=normalized_query,
                answer=tool_result.answer,
                context=tool_result.context,
            )

        iterations = 1

        # Step 5: Reflection — RAG only, only if score < threshold.
        if not is_fast_path and not validation.passed:
            logger.info(
                f"AgenticPipeline: score {validation.confidence_score:.1f} "
                f"< threshold {self.validator.threshold} — entering reflection."
            )

            reflect_events = self.reflector.reflect_stream(
                tool=tool,
                query=normalized_query,
                initial_result=tool_result,
                initial_validation=validation,
            )
            try:
                while True:
                    yield next(reflect_events)
            except StopIteration as exc:
                tool_result, validation, iterations = exc.value

        # Step 6: Build final result
        result = PipelineResult(
            answer=tool_result.answer,
            sources=tool_result.sources,
            confidence_score=validation.confidence_score,
            answer_source=tool_result.answer_source,
            validation_reasoning=validation.reasoning,
            iterations=iterations,
            latency_ms=self._elapsed(start),
        )

        logger.info(
            f"AgenticPipeline streaming completed: "
            f"score={result.confidence_score:.1f}, "
            f"source={result.answer_source}, "
            f"tool={tool_name!r}, "
            f"iterations={iterations}, "
            f"latency={result.latency_ms}ms"
        )

        yield {"type": "result", "data": result}


    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    # Builds an AgenticPipeline from application configuration
    def create(online_pipeline: OnlinePipeline) -> "AgenticPipeline":
        """
        Build a fully wired AgenticPipeline from config.

        Parameters
        ----------
        online_pipeline:
            A pre-built OnlinePipeline (shared with RAGPipeline singleton).
        """

        config = ApplicationConfig()

        ollama_cfg   = config.models["ollama"]
        chat_model   = config.models["chat"]["model"]
        code_model   = config.models["code_tool"]["model"]
        router_model = config.models["planner"]["model"]
        val_cfg      = config.models["validation"]
        val_model    = val_cfg["model"]
        threshold    = float(val_cfg.get("confidence_threshold", 7.0))
        weights      = val_cfg.get("weights", {
            "correctness":  0.5,
            "completeness": 0.3,
            "citations":    0.2,
        })

        ollama = OllamaManager(host=ollama_cfg["host"])

        # Warn if the code model is not available
        AgenticPipeline._warn_if_model_missing(ollama, code_model)

        guardrail = Guardrail()

        router = AgentRouter(
            ollama_manager=ollama,
            model=router_model,
        )

        chat_tool = ChatTool(
            ollama_manager=ollama,
            model=chat_model,
        )

        code_tool = CodeTool(
            ollama_manager=ollama,
            model=code_model,
        )

        rag_tool = RAGTool(
            online_pipeline=online_pipeline,
            ollama_manager=ollama,
            fallback_model=chat_model,
        )

        validator = ValidationLayer(
            ollama_manager=ollama,
            model=val_model,
            threshold=threshold,
            weights=weights,
        )

        reflector = Reflector(validator=validator)

        # Query rewriter — uses a dedicated config section if present,
        # otherwise falls back to the chat model.
        rewriter_cfg = config.models.get("query_rewriter", {})
        rewriter_model = rewriter_cfg.get("model", chat_model)
        query_rewriter = QueryRewriter(
            ollama_manager=ollama,
            model=rewriter_model,
        )

        return AgenticPipeline(
            guardrail=guardrail,
            router=router,
            chat_tool=chat_tool,
            code_tool=code_tool,
            rag_tool=rag_tool,
            validator=validator,
            reflector=reflector,
            query_rewriter=query_rewriter,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    # Warns if an Ollama model is missing.
    def _warn_if_model_missing(
        ollama: OllamaManager,
        model: str,
    ) -> None:
        """Log a warning if a required Ollama model is not installed."""
        try:
            installed = ollama.list_models()
            # Normalize: strip ":latest" suffix for comparison
            normalized = [m.split(":")[0] for m in installed]
            model_base = model.split(":")[0]
            if model_base not in normalized:
                logger.warning(
                    f"Model '{model}' is not installed in Ollama. "
                    f"Run: ollama pull {model}"
                )
        except Exception:
            pass  # Ollama might not be running yet

    @staticmethod
    # Calculates and returns elapsed time in milliseconds.
    def _elapsed(start: float) -> int:
        return int((time.perf_counter() - start) * 1000)
