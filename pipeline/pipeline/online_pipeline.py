"""
Online RAG Pipeline.

Coordinates the online retrieval pipeline.
"""

from src.retrieval import HybridRetriever
from src.reranking import CrossEncoderReranker
from src.context import ContextBuilder
from src.generation import PromptBuilder
from src.llm import OllamaManager
from src.core.config import ApplicationConfig
from src.models import EmbeddedChunk
from src.core.logging import LoggerManager

logger = LoggerManager.get_logger()


# Retrieves relevant context chunks for queries.
class OnlinePipeline:
    """
    Coordinates the online RAG pipeline.
    """

    # Sets up components for retrieval and ranking.
    def __init__(
        self,
        retriever: HybridRetriever,
        reranker: CrossEncoderReranker,
        context_builder: ContextBuilder,
        prompt_builder: PromptBuilder,
        ollama_manager: OllamaManager,
        config: ApplicationConfig,
    ) -> None:

        self.retriever = retriever

        self.reranker = reranker

        self.context_builder = context_builder

        self.prompt_builder = prompt_builder

        self.ollama_manager = ollama_manager

        self.chat_model = config.models["chat"]["model"]

    # Retrieves candidate documents based on query.
    def retrieve_candidates(
        self,
        query: str,
    ) -> list[EmbeddedChunk]:
        """
        Dense + sparse hybrid retrieval (no reranking).
        """
        return self.retriever.retrieve(
            query,
            top_k=10,
        )

    # Reranks retrieved chunks based on query.
    def rerank_candidates(
        self,
        query: str,
        chunks: list[EmbeddedChunk],
    ) -> list[EmbeddedChunk]:
        """
        Cross-encoder reranking of retrieved candidates.
        """
        return self.reranker.rerank(
            query=query,
            chunks=chunks,
            top_k=5,
        )

    # Retrieves and reranks relevant search chunks.
    def _retrieve(
        self,
        query: str,
    ) -> list[EmbeddedChunk]:
        """
        Retrieve and rerank relevant chunks (combined, used by non-streaming path).
        """
        chunks = self.retrieve_candidates(query)
        return self.rerank_candidates(query, chunks)
    
    # Builds LLM context from provided chunks.
    def _build_context(
        self,
        chunks: list[EmbeddedChunk],
    ) -> str:
        """
        Build LLM context.
        """

        return self.context_builder.build(
            chunks
        )
    
    # Constructs the prompt for the language model.
    def _build_prompt(
        self,
        query: str,
        context: str,
    ) -> str:
        """
        Build the final prompt.
        """

        return self.prompt_builder.build(
            query=query,
            context=context,
        )
    
    # Generates the final answer from the LLM.
    def _generate(
        self,
        prompt: str,
    ) -> str:
        """
        Generate the final answer.
        """

        return self.ollama_manager.generate(
            model=self.chat_model,
            prompt=prompt,
        )

    # Executes the online RAG pipeline for answers.
    def ask(
        self,
        query: str,
    ) -> str:
        """
        Execute the online RAG pipeline.
        """
        logger.info(
            f"Received query: {query}"
        )

        chunks = self._retrieve(
            query
        )

        context = self._build_context(
            chunks
        )

        prompt = self._build_prompt(
            query,
            context,
        )

        answer = self._generate(
            prompt
        )

        logger.info(
            "Online pipeline completed successfully."
        )

        return answer

    # Executes RAG pipeline and returns detailed results.
    def ask_with_details(
        self,
        query: str,
    ) -> tuple[str, list[EmbeddedChunk], str]:
        """
        Execute the online RAG pipeline and return full details.

        Returns
        -------
        tuple of:
            answer   : str                  — generated answer text
            chunks   : list[EmbeddedChunk]  — retrieved + reranked chunks
            context  : str                  — LLM context string built from chunks
        """
        logger.info(f"Received query (with details): {query}")

        chunks = self._retrieve(query)
        context = self._build_context(chunks)
        prompt = self._build_prompt(query, context)
        answer = self._generate(prompt)

        logger.info("Online pipeline (with details) completed.")
        return answer, chunks, context

    # Executes RAG pipeline, yielding answer chunks.
    def ask_stream(
        self,
        query: str,
    ):
        """
        Execute the online RAG pipeline and yield chunks of the answer.

        Returns
        -------
        tuple of:
            stream   : Generator            — yields answer chunks
            chunks   : list[EmbeddedChunk]  — retrieved + reranked chunks
            context  : str                  — LLM context string built from chunks
        """
        logger.info(f"Received query (streaming): {query}")

        chunks = self._retrieve(query)
        context = self._build_context(chunks)
        prompt = self._build_prompt(query, context)
        
        stream = self.ollama_manager.generate_stream(
            model=self.chat_model,
            prompt=prompt,
        )

        return stream, chunks, context

