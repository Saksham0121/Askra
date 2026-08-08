"""
BM25 Manager.

Responsible for sparse retrieval using BM25.
"""

import pickle
from pathlib import Path

from rank_bm25 import BM25Okapi

from src.core.logging import LoggerManager
from src.models import EmbeddedChunk

logger = LoggerManager.get_logger()


# Manages BM25 indexing and search operations.
class BM25Manager:
    """
    Enterprise BM25 Manager.
    """

    # Initializes the index and BM25 parameters.
    def __init__(
        self,
        index_path: str,
    ) -> None:

        self.index_path = Path(index_path)

        self.bm25: BM25Okapi | None = None

        self.embedded_chunks: list[EmbeddedChunk] = []

    # Builds the BM25 index from chunks.
    def build(
        self,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        """
        Build BM25 index.
        """

        self.embedded_chunks = embedded_chunks

        corpus = [
            chunk.chunk.text.split()
            for chunk in embedded_chunks
        ]

        self.bm25 = BM25Okapi(corpus)

        logger.info(
            f"Built BM25 index with {len(corpus)} chunk(s)."
        )

    # Searches the BM25 index for relevant chunks.
    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[EmbeddedChunk]:
        """
        Search BM25 index.
        """

        if self.bm25 is None:

            raise RuntimeError(
                "BM25 index has not been built."
            )

        scores = self.bm25.get_scores(
            query.split()
        )

        ranked = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        results = [
            self.embedded_chunks[index]
            for index, _ in ranked
        ]

        logger.info(
            f"Retrieved {len(results)} chunk(s)."
        )

        return results

    # Saves the BM25 index to storage.
    def save(self) -> None:
        """
        Save BM25 index.
        """

        self.index_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with open(
            self.index_path,
            "wb",
        ) as file:

            pickle.dump(
                (
                    self.bm25,
                    self.embedded_chunks,
                ),
                file,
            )

        logger.info(
            "BM25 index saved."
        )

    # Deletes chunks associated with a document ID.
    def delete_by_document_id(self, document_id: str) -> None:
        original_count = len(self.embedded_chunks)
        self.embedded_chunks = [
            chunk for chunk in self.embedded_chunks
            if chunk.chunk.document_id != document_id
        ]
        
        if len(self.embedded_chunks) == original_count:
            return
            
        if not self.embedded_chunks:
            self.bm25 = None
            self.save()
            logger.info(f"Deleted all chunks for document {document_id} from BM25. Index is now empty.")
            return
            
        corpus = [
            chunk.chunk.text.split()
            for chunk in self.embedded_chunks
        ]
        self.bm25 = BM25Okapi(corpus)
        self.save()
        logger.info(f"Deleted chunks for document {document_id} from BM25. Remaining: {len(self.embedded_chunks)}")

    # Loads the BM25 index and embedded chunks.
    def load(self) -> None:
        """
        Load BM25 index from disk.

        If the index file does not exist (e.g. fresh clone, cleared data
        directory, or first run before any document has been ingested) this
        method returns silently without raising an exception.  The manager
        stays in its empty initial state (self.bm25 = None), and any call to
        search() will raise a clear RuntimeError rather than a confusing
        FileNotFoundError.
        """

        if not self.index_path.exists():
            logger.warning(
                f"No BM25 index found at '{self.index_path}'. "
                "Starting with an empty index — ingest a document first."
            )
            return

        with open(
            self.index_path,
            "rb",
        ) as file:

            (
                self.bm25,
                self.embedded_chunks,
            ) = pickle.load(file)

        logger.info(
            f"Loaded {len(self.embedded_chunks)} chunk(s)."
        )