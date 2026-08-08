"""
Hybrid Retriever.

Combines dense and sparse retrieval using
Reciprocal Rank Fusion (RRF).
"""

from collections import defaultdict

from pipeline.models import EmbeddedChunk
from .dense_retriever import DenseRetriever
from .sparse_retriever import SparseRetriever


# Combines dense and sparse retrieval results.
class HybridRetriever:
    """
    Hybrid retriever using Reciprocal Rank Fusion.
    """

    # Initializes retrievers and RRFK parameter values.
    def __init__(
        self,
        dense_retriever: DenseRetriever,
        sparse_retriever: SparseRetriever,
        rrf_k: int = 60,
    ) -> None:

        self.dense_retriever = dense_retriever

        self.sparse_retriever = sparse_retriever

        self.rrf_k = rrf_k

    # Retrieves relevant documents based on the query.
    def retrieve(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[EmbeddedChunk]:
        """
        Retrieve documents using hybrid retrieval.
        """

        dense_results = self.dense_retriever.retrieve(
            query,
            top_k=top_k,
        )

        sparse_results = self.sparse_retriever.retrieve(
            query,
            top_k=top_k,
        )

        scores = defaultdict(float)

        chunk_lookup = {}

        for rank, chunk in enumerate(
            dense_results,
            start=1,
        ):

            scores[chunk.chunk.chunk_id] += (
                1 / (self.rrf_k + rank)
            )

            chunk_lookup[
                chunk.chunk.chunk_id
            ] = chunk

        for rank, chunk in enumerate(
            sparse_results,
            start=1,
        ):

            scores[chunk.chunk.chunk_id] += (
                1 / (self.rrf_k + rank)
            )

            chunk_lookup[
                chunk.chunk.chunk_id
            ] = chunk

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        return [
            chunk_lookup[chunk_id]
            for chunk_id, _ in ranked[:top_k]
        ]