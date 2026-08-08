"""
RAG Tool.

Retrieves relevant document chunks and generates a grounded answer.

Fallback logic (in Answer Generation Layer):
  If the LLM says it could not find the answer in the documents,
  a second call is made without context (LLM knowledge fallback),
  and the answer is labelled as AnswerSource.RAG_FALLBACK.
"""

from __future__ import annotations

from src.agent.base_tool import BaseTool, ToolResult
from src.core.logging import LoggerManager
from src.llm import OllamaManager
from src.models import EmbeddedChunk
from src.pipeline.online_pipeline import OnlinePipeline
from src.pipeline.pipeline_result import AnswerSource

logger = LoggerManager.get_logger()

# Phrases that indicate the RAG model could not find an answer
_FALLBACK_PHRASES = (
    "i could not find",
    "not found in the provided",
    "no relevant information",
    "the context does not",
    "cannot find the answer",
    "not mentioned in the documents",
)

_FALLBACK_PROMPT = """You are SAARTHI, a helpful enterprise assistant.

The user asked a question but no relevant information was found in the indexed documents.
Answer using your own general knowledge and clearly state that the answer is not from the documents.

IMPORTANT: Start your answer with this exact phrase:
"This answer is based on general knowledge, not your documents."

Question: {query}

Answer:"""


# Generates answers grounded in retrieved documents.
class RAGTool(BaseTool):
    """
    Document-grounded answer tool using hybrid retrieval + reranking.
    Falls back to LLM knowledge if no relevant chunks are found.
    """

    name = "rag"

    # Sets up necessary components for operation
    def __init__(
        self,
        online_pipeline: OnlinePipeline,
        ollama_manager: OllamaManager,
        fallback_model: str,
    ) -> None:
        self.online_pipeline = online_pipeline
        self.ollama_manager = ollama_manager
        self.fallback_model = fallback_model

    # Executes RAG pipeline for grounded answers.
    def execute(self, query: str) -> ToolResult:
        """
        Run the full RAG pipeline and return a grounded answer.
        Falls back to LLM knowledge if RAG cannot find relevant information.
        """

        logger.info(f"RAGTool executing for query: {query!r}")

        # ----------------------------------------------------------------
        # Step 1: Run the RAG pipeline (retrieve → rerank → generate)
        # ----------------------------------------------------------------

        answer, chunks, context = self.online_pipeline.ask_with_details(query)

        sources = self._extract_sources(chunks)

        # ----------------------------------------------------------------
        # Step 2: Detect whether the answer was grounded or a fallback
        # ----------------------------------------------------------------

        if self._is_fallback(answer, chunks):

            logger.info(
                "RAGTool: no grounded answer found — falling back to LLM knowledge."
            )

            answer = self._generate_fallback(query)

            return ToolResult(
                answer=answer,
                answer_source=AnswerSource.RAG_FALLBACK,
                sources=[],
                context="",
            )

        logger.info(f"RAGTool completed with {len(sources)} source(s).")

        return ToolResult(
            answer=answer,
            answer_source=AnswerSource.RAG,
            sources=sources,
            context=context,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    # Checks if RAG fell back to fallback knowledge.
    def _is_fallback(
        self,
        answer: str,
        chunks: list[EmbeddedChunk],
    ) -> bool:
        """
        Determine whether the RAG model fell back to its own knowledge.

        Two signals:
        1. No chunks were retrieved (empty index or very low similarity).
        2. The answer text contains a known fallback phrase.
        """

        if not chunks:
            return True

        lower = answer.lower()

        return any(phrase in lower for phrase in _FALLBACK_PHRASES)

    # Extracts unique source document filenames from chunks.
    def _extract_sources(
        self,
        chunks: list[EmbeddedChunk],
    ) -> list[str]:
        """Return a deduplicated list of source document filenames."""

        seen: set[str] = set()
        sources: list[str] = []

        for chunk in chunks:
            src = chunk.chunk.source
            if src not in seen:
                seen.add(src)
                sources.append(src)

        return sources

    # Generates a fallback answer using the LLM.
    def _generate_fallback(self, query: str) -> str:
        """Generate a fallback answer from LLM knowledge."""

        prompt = _FALLBACK_PROMPT.format(query=query)

        return self.ollama_manager.generate(
            model=self.fallback_model,
            prompt=prompt,
        )

    # Executes the RAG pipeline with status updates.
    def execute_stream(self, query: str):
        """
        Run the full RAG pipeline step-by-step, yielding a status message before
        each stage so the UI stays active throughout the wait.
        Falls back to LLM knowledge if RAG cannot find relevant information.
        """
        logger.info(f"RAGTool executing_stream for query: {query!r}")

        # ── Step 1: Dense + sparse retrieval ────────────────────────────
        yield {"type": "status", "message": "🔍 Scanning document index..."}
        raw_chunks = self.online_pipeline.retrieve_candidates(query)
        logger.info(f"RAGTool: retrieved {len(raw_chunks)} candidate chunk(s).")

        # ── Step 2: Cross-encoder reranking ─────────────────────────────
        yield {"type": "status", "message": "📊 Ranking the most relevant passages..."}
        chunks = self.online_pipeline.rerank_candidates(query, raw_chunks)
        sources = self._extract_sources(chunks)
        logger.info(f"RAGTool: reranked to {len(chunks)} chunk(s).")

        # ── Step 3: Build context + prompt ──────────────────────────────
        yield {"type": "status", "message": "📖 Reading key sections from your documents..."}
        context = self.online_pipeline._build_context(chunks)
        prompt  = self.online_pipeline._build_prompt(query, context)

        # ── Step 4: Stream the answer ────────────────────────────────────
        yield {"type": "status", "message": "✍️ Drafting your answer..."}
        stream = self.online_pipeline.ollama_manager.generate_stream(
            model=self.online_pipeline.chat_model,
            prompt=prompt,
        )

        full_answer_chunks: list[str] = []
        for chunk in stream:
            full_answer_chunks.append(chunk)
            yield {"type": "chunk", "content": chunk}

        answer = "".join(full_answer_chunks)

        # ── Fallback detection ───────────────────────────────────────────
        if self._is_fallback(answer, chunks):
            logger.info("RAGTool: fallback detected after streaming. Streaming fallback now.")
            yield {"type": "status", "message": "💡 No relevant document found — drawing on general knowledge..."}
            yield {"type": "clear_chunks"}

            prompt = _FALLBACK_PROMPT.format(query=query)
            fallback_stream = self.ollama_manager.generate_stream(
                model=self.fallback_model,
                prompt=prompt,
            )

            full_fallback_chunks: list[str] = []
            for chunk in fallback_stream:
                full_fallback_chunks.append(chunk)
                yield {"type": "chunk", "content": chunk}

            answer = "".join(full_fallback_chunks)

            yield {"type": "result", "data": ToolResult(
                answer=answer,
                answer_source=AnswerSource.RAG_FALLBACK,
                sources=[],
                context="",
            )}
        else:
            logger.info(f"RAGTool streaming completed with {len(sources)} source(s).")
            yield {"type": "result", "data": ToolResult(
                answer=answer,
                answer_source=AnswerSource.RAG,
                sources=sources,
                context=context,
            )}
