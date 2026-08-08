"""
Online RAG Pipeline.

Coordinates the online retrieval pipeline with GroqManager.
"""

from __future__ import annotations

from pipeline.retrieval import HybridRetriever
from pipeline.reranking import CrossEncoderReranker
from pipeline.context import ContextBuilder
from pipeline.generation import PromptBuilder
from pipeline.llm.groq_manager import GroqManager
from pipeline.models import EmbeddedChunk
from pipeline.core.logging import LoggerManager

logger = LoggerManager.get_logger()


class OnlinePipeline:
    """
    Coordinates the online RAG pipeline.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        groq_manager: GroqManager,
        chat_model: str,
    ) -> None:
        self.retriever = retriever
        self.reranker = reranker
        self.context_builder = context_builder
        self.prompt_builder = prompt_builder
        self.groq_manager = groq_manager
        self.chat_model = chat_model

    def retrieve_candidates(self, query: str) -> list[EmbeddedChunk]:
        """Dense + sparse hybrid retrieval (no reranking)."""
        return self.retriever.retrieve(query, top_k=10)

    def rerank_candidates(self, query: str, chunks: list[EmbeddedChunk]) -> list[EmbeddedChunk]:
        """Cross-encoder reranking of retrieved candidates."""
        return self.reranker.rerank(query=query, chunks=chunks, top_k=5)

    def _retrieve(self, query: str) -> list[EmbeddedChunk]:
        """Retrieve and rerank relevant chunks."""
        chunks = self.retrieve_candidates(query)
        return self.rerank_candidates(query, chunks)

    def _build_context(self, chunks: list[EmbeddedChunk]) -> str:
        return self.context_builder.build(chunks)

    def _build_prompt(self, query: str, context: str) -> str:
        return self.prompt_builder.build(query=query, context=context)

    def _generate(self, prompt: str) -> str:
        return self.groq_manager.generate(model=self.chat_model, prompt=prompt)

    def ask(self, query: str) -> str:
        logger.info(f"Received query: {query}")
        chunks = self._retrieve(query)
        context = self._build_context(chunks)
        prompt = self._build_prompt(query, context)
        answer = self._generate(prompt)
        logger.info("Online pipeline completed successfully.")
        return answer

    def ask_with_details(self, query: str) -> tuple[str, list[EmbeddedChunk], str]:
        logger.info(f"Received query (with details): {query}")
        chunks = self._retrieve(query)
        context = self._build_context(chunks)
        prompt = self._build_prompt(query, context)
        answer = self._generate(prompt)
        logger.info("Online pipeline (with details) completed.")
        return answer, chunks, context

    def ask_stream(self, query: str):
        logger.info(f"Received query (streaming): {query}")
        chunks = self._retrieve(query)
        context = self._build_context(chunks)
        prompt = self._build_prompt(query, context)
        stream = self.groq_manager.generate_stream(model=self.chat_model, prompt=prompt)
        return stream, chunks, context
