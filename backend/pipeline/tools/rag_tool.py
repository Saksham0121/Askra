"""
RAG Tool — uses GroqManager and OnlinePipeline.
"""
from __future__ import annotations
from pipeline.agent.base_tool import BaseTool, ToolResult
from pipeline.core.logging import LoggerManager
from pipeline.llm.groq_manager import GroqManager
from pipeline.models import EmbeddedChunk
from pipeline.pipeline.online_pipeline import OnlinePipeline
from pipeline.pipeline.pipeline_result import AnswerSource

logger = LoggerManager.get_logger()

_FALLBACK_PHRASES = (
    "i could not find",
    "not found in the provided",
    "no relevant information",
    "the context does not",
    "cannot find the answer",
    "not mentioned in the documents",
)

_FALLBACK_PROMPT = """You are Askrab, a helpful enterprise assistant.

The user asked a question but no relevant information was found in the indexed documents.
Answer using your own general knowledge and clearly state that the answer is not from the documents.

IMPORTANT: Start your answer with this exact phrase:
"This answer is based on general knowledge, not your documents."

Question: {query}

Answer:"""


class RAGTool(BaseTool):
    """Document-grounded answer tool using hybrid retrieval + reranking."""

    name = "rag"

    def __init__(
        self,
        online_pipeline: OnlinePipeline,
        groq_manager: GroqManager,
        fallback_model: str,
    ) -> None:
        self.online_pipeline = online_pipeline
        self.groq_manager = groq_manager
        self.fallback_model = fallback_model

    def execute(self, query: str) -> ToolResult:
        logger.info(f"RAGTool executing for query: {query!r}")
        answer, chunks, context = self.online_pipeline.ask_with_details(query)
        sources = self._extract_sources(chunks)

        if self._is_fallback(answer, chunks):
            logger.info("RAGTool: no grounded answer — falling back to LLM knowledge.")
            answer = self._generate_fallback(query)
            return ToolResult(answer=answer, answer_source=AnswerSource.RAG_FALLBACK, sources=[], context="")

        logger.info(f"RAGTool completed with {len(sources)} source(s).")
        return ToolResult(answer=answer, answer_source=AnswerSource.RAG, sources=sources, context=context)

    def execute_stream(self, query: str):
        logger.info(f"RAGTool execute_stream for query: {query!r}")

        yield {"type": "status", "message": "🔍 Scanning document index..."}
        raw_chunks = self.online_pipeline.retrieve_candidates(query)

        yield {"type": "status", "message": "📊 Ranking the most relevant passages..."}
        chunks = self.online_pipeline.rerank_candidates(query, raw_chunks)
        sources = self._extract_sources(chunks)

        yield {"type": "status", "message": "📖 Reading key sections from your documents..."}
        context = self.online_pipeline._build_context(chunks)
        prompt = self.online_pipeline._build_prompt(query, context)

        yield {"type": "status", "message": "✍️ Drafting your answer..."}
        stream = self.online_pipeline.groq_manager.generate_stream(
            model=self.online_pipeline.chat_model, prompt=prompt
        )

        full_chunks: list[str] = []
        for chunk in stream:
            full_chunks.append(chunk)
            yield {"type": "chunk", "content": chunk}

        answer = "".join(full_chunks)

        if self._is_fallback(answer, chunks):
            logger.info("RAGTool: fallback detected. Streaming fallback now.")
            yield {"type": "status", "message": "💡 No relevant doc found — drawing on general knowledge..."}
            yield {"type": "clear_chunks"}
            prompt = _FALLBACK_PROMPT.format(query=query)
            fallback_stream = self.groq_manager.generate_stream(model=self.fallback_model, prompt=prompt)
            fallback_chunks: list[str] = []
            for chunk in fallback_stream:
                fallback_chunks.append(chunk)
                yield {"type": "chunk", "content": chunk}
            answer = "".join(fallback_chunks)
            yield {"type": "result", "data": ToolResult(
                answer=answer, answer_source=AnswerSource.RAG_FALLBACK, sources=[], context=""
            )}
        else:
            logger.info(f"RAGTool streaming done with {len(sources)} source(s).")
            yield {"type": "result", "data": ToolResult(
                answer=answer, answer_source=AnswerSource.RAG, sources=sources, context=context
            )}

    def _is_fallback(self, answer: str, chunks: list[EmbeddedChunk]) -> bool:
        if not chunks:
            return True
        return any(phrase in answer.lower() for phrase in _FALLBACK_PHRASES)

    def _extract_sources(self, chunks: list[EmbeddedChunk]) -> list[str]:
        seen: set[str] = set()
        sources: list[str] = []
        for chunk in chunks:
            src = chunk.chunk.source
            if src not in seen:
                seen.add(src)
                sources.append(src)
        return sources

    def _generate_fallback(self, query: str) -> str:
        return self.groq_manager.generate(
            model=self.fallback_model,
            prompt=_FALLBACK_PROMPT.format(query=query),
        )
