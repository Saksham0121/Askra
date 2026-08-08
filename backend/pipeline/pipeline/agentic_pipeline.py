"""
AgenticPipeline adapted for GroqManager.
Full 7-layer orchestrator.
"""
from __future__ import annotations
import time
from pipeline.agent.base_tool import BaseTool
from pipeline.agent.router import AgentRouter
from pipeline.pipeline.online_pipeline import OnlinePipeline
from pipeline.pipeline.pipeline_result import AnswerSource, PipelineResult
from pipeline.reflection.reflector import Reflector
from pipeline.tools.chat_tool import ChatTool
from pipeline.tools.code_tool import CodeTool
from pipeline.tools.rag_tool import RAGTool
from pipeline.validation.guardrail import Guardrail
from pipeline.validation.models import QueryIntent
from pipeline.validation.query_rewriter import QueryRewriter
from pipeline.validation.validation_layer import ValidationLayer, ValidationResult
from pipeline.core.logging import LoggerManager

logger = LoggerManager.get_logger()

_REWRITE_INTENTS: frozenset[QueryIntent] = frozenset({QueryIntent.DOCUMENT, QueryIntent.UNKNOWN})
_NO_VALIDATE_TOOLS: frozenset[str] = frozenset({"chat", "code"})


def _fast_path_validation(tool_name: str = "rag") -> ValidationResult:
    is_rag = tool_name == "rag"
    return ValidationResult(
        confidence_score=8.0,
        correctness=8.0,
        completeness=8.0,
        has_citations=is_rag,
        reasoning=(
            "Validation skipped — Direct RAG fast path."
            if is_rag
            else f"Validation skipped — {tool_name} tool."
        ),
        threshold=5.5,
    )


class AgenticPipeline:
    """Orchestrates the full 7-layer agentic RAG flow."""

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
        self.guardrail = guardrail
        self.router = router
        self.chat_tool = chat_tool
        self.code_tool = code_tool
        self.rag_tool = rag_tool
        self.validator = validator
        self.reflector = reflector
        self.query_rewriter = query_rewriter
        self._tool_map: dict[str, BaseTool] = {
            "chat": chat_tool,
            "code": code_tool,
            "rag": rag_tool,
        }

    def run(self, query: str, direct_rag: bool = False) -> PipelineResult:
        start = time.perf_counter()
        logger.info(f"AgenticPipeline.run | direct_rag={direct_rag} | query={query!r}")

        # L0 — Safety Guardrail
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

        # L1 — Query Rewriting (RAG/UNKNOWN intents only)
        if guard.intent in _REWRITE_INTENTS or direct_rag:
            rewrite = self.query_rewriter.rewrite(normalized_query)
            if rewrite.was_rewritten:
                logger.info(f"Query rewritten: {normalized_query!r} → {rewrite.rewritten_query!r}")
            normalized_query = rewrite.rewritten_query

        # L2 — Decision Router
        if direct_rag:
            tool_name, tool = "rag", self.rag_tool
        else:
            tool_name = self.router.route(normalized_query)
            tool = self._tool_map.get(tool_name, self.rag_tool)
            logger.info(f"AgenticPipeline: Router selected '{tool_name}'.")

        # L3 — Tool Execution
        try:
            tool_result = tool.execute(normalized_query)
        except Exception as exc:
            logger.error(f"Tool execution failed: {exc}")
            return PipelineResult(
                answer=f"Sorry, an error occurred: {exc}",
                answer_source=AnswerSource.LLM,
                confidence_score=0.0,
                validation_reasoning=str(exc),
                latency_ms=self._elapsed(start),
            )

        # L4 — Validation
        is_fast_path = direct_rag or tool_name in _NO_VALIDATE_TOOLS
        if is_fast_path:
            validation = _fast_path_validation(tool_name)
        else:
            validation = self.validator.validate(
                query=normalized_query, answer=tool_result.answer, context=tool_result.context
            )

        # L5 — Reflection
        iterations = 1
        if not is_fast_path and not validation.passed:
            logger.info(f"Score {validation.confidence_score:.1f} < threshold — entering reflection.")
            tool_result, validation, iterations = self.reflector.reflect(
                tool=tool, query=normalized_query,
                initial_result=tool_result, initial_validation=validation,
            )

        # L6 — Response Assembly
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
            f"AgenticPipeline done: score={result.confidence_score:.1f}, "
            f"tool={tool_name!r}, iterations={iterations}, latency={result.latency_ms}ms"
        )
        return result

    def run_stream(self, query: str, direct_rag: bool = False):
        start = time.perf_counter()
        logger.info(f"AgenticPipeline.run_stream | direct_rag={direct_rag} | query={query!r}")

        yield {"type": "status", "message": "🛡️ Checking safety guidelines..."}
        guard = self.guardrail.validate(query)
        if not guard.allowed:
            yield {"type": "result", "data": PipelineResult(
                answer=f"⛔ {guard.reason}", answer_source=AnswerSource.LLM,
                confidence_score=0.0, validation_reasoning=guard.reason,
                latency_ms=self._elapsed(start),
            )}
            return
        normalized_query = guard.normalized_query

        if guard.intent in _REWRITE_INTENTS or direct_rag:
            yield {"type": "status", "message": "✏️ Refining your query..."}
            rewrite = self.query_rewriter.rewrite(normalized_query)
            normalized_query = rewrite.rewritten_query

        if direct_rag:
            tool_name, tool = "rag", self.rag_tool
        else:
            yield {"type": "status", "message": "🤔 Deciding how to answer..."}
            tool_name = self.router.route(normalized_query)
            tool = self._tool_map.get(tool_name, self.rag_tool)

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
                answer=f"Sorry, an error occurred: {exc}",
                answer_source=AnswerSource.LLM, confidence_score=0.0,
                validation_reasoning=str(exc), latency_ms=self._elapsed(start),
            )}
            return

        if tool_result is None:
            return

        is_fast_path = direct_rag or tool_name in _NO_VALIDATE_TOOLS
        if is_fast_path:
            validation = _fast_path_validation(tool_name)
        else:
            yield {"type": "status", "message": "🔬 Evaluating answer quality..."}
            validation = self.validator.validate(
                query=normalized_query, answer=tool_result.answer, context=tool_result.context
            )

        iterations = 1
        if not is_fast_path and not validation.passed:
            reflect_events = self.reflector.reflect_stream(
                tool=tool, query=normalized_query,
                initial_result=tool_result, initial_validation=validation,
            )
            try:
                while True:
                    yield next(reflect_events)
            except StopIteration as exc:
                tool_result, validation, iterations = exc.value

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
            f"AgenticPipeline stream done: score={result.confidence_score:.1f}, "
            f"tool={tool_name!r}, latency={result.latency_ms}ms"
        )
        yield {"type": "result", "data": result}

    @staticmethod
    def _elapsed(start: float) -> int:
        return int((time.perf_counter() - start) * 1000)
