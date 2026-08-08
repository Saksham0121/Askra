"""
Sparse Retriever.

Retrieves relevant chunks using BM25.
"""

from src.models import EmbeddedChunk
from src.retrieval.bm25_manager import BM25Manager


# Retrieves relevant chunks using BM25 search.
class SparseRetriever:
    """
    Sparse retriever backed by BM25.
    """

    # Initializes the BM25 search manager instance.
    def __init__(
        self,
        bm25_manager: BM25Manager,
    ) -> None:

        self.bm25_manager = bm25_manager

    # Retrieves relevant chunks based on a query.
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[EmbeddedChunk]:
        """
        Retrieve the most relevant chunks using
        BM25 retrieval.
        """

        return self.bm25_manager.search(
            query=query,
            top_k=top_k,
        )