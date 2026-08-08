"""
Dense Retriever.

Retrieves relevant chunks using dense vector search (FAISS).
"""

from pipeline.embeddings import EmbeddingManager
from pipeline.models import EmbeddedChunk
from pipeline.retrieval.faiss_manager import FAISSManager


# Retrieves relevant chunks based on embeddings.
class DenseRetriever:
    """
    Dense retriever backed by FAISS.
    """

    # Initializes embedding and FAISS manager instances.
    def __init__(
        self,
        embedding_manager: EmbeddingManager,
        faiss_manager: FAISSManager,
    ) -> None:

        self.embedding_manager = embedding_manager

        self.faiss_manager = faiss_manager

    # Retrieves relevant chunks based on similarity.
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[EmbeddedChunk]:
        """
        Retrieve the most relevant chunks using
        dense vector similarity.
        """

        query_embedding = self.embedding_manager.embed_text(
            query
        )

        return self.faiss_manager.search(
            query_embedding=query_embedding,
            top_k=top_k,
        )