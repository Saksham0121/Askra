"""
Pipeline Factory.

Builds a fully configured OnlinePipeline.
"""

from pipeline.context import ContextBuilder
from pipeline.core.config import ApplicationConfig
from pipeline.embeddings import EmbeddingManager
from pipeline.generation import PromptBuilder
from pipeline.llm.groq_manager import GroqManager
from .online_pipeline import OnlinePipeline
from pipeline.reranking import CrossEncoderReranker
from pipeline.retrieval import (
    BM25Manager,
    DenseRetriever,
    FAISSManager,
    HybridRetriever,
    SparseRetriever,
)


# Creates an OnlinePipeline based on configuration.
class PipelineFactory:
    """
    Factory for creating an OnlinePipeline.
    """

    @staticmethod
    # Sets up and initializes retrieval components.
    def create() -> OnlinePipeline:

        config = ApplicationConfig()

        embedding_manager = EmbeddingManager(
            model_name=config.models["embeddings"]["model"],
        )

        faiss_manager = FAISSManager(
            dimension=config.models["embeddings"]["dimension"],
            index_path=config.storage["faiss"]["index_path"],
            metadata_path=config.storage["faiss"]["metadata_path"],
        )

        faiss_manager.load()

        bm25_manager = BM25Manager(
            index_path=config.storage["bm25"]["index_path"],
        )

        bm25_manager.load()

        dense = DenseRetriever(
            embedding_manager,
            faiss_manager,
        )

        sparse = SparseRetriever(
            bm25_manager,
        )

        hybrid = HybridRetriever(
            dense,
            sparse,
        )

        reranker = CrossEncoderReranker(
            model_name=config.models["reranker"]["model"],
        )

        context_builder = ContextBuilder()

        prompt_builder = PromptBuilder()

        ollama_manager = OllamaManager(
            host=config.models["ollama"]["host"],
        )

        return OnlinePipeline(
            retriever=hybrid,
            reranker=reranker,
            context_builder=context_builder,
            prompt_builder=prompt_builder,
            groq_manager=groq_manager,
            config=config,
        )