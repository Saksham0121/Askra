"""
FAISS Manager.

Responsible for storing and retrieving vector embeddings.
"""

import json
from pathlib import Path

import faiss
import numpy as np

from src.core.logging import LoggerManager
from src.models import EmbeddedChunk
from src.storage.mappers import EmbeddedChunkMapper

logger = LoggerManager.get_logger()


# Manages FAISS index creation and data loading.
class FAISSManager:
    """
    Enterprise FAISS Manager.
    """

    # Initializes FAISS index and related paths.
    def __init__(
        self,
        dimension: int,
        index_path: str,
        metadata_path: str,
    ) -> None:

        self.dimension = dimension

        self.index_path = Path(index_path)

        self.metadata_path = Path(metadata_path)

        self.index = faiss.IndexFlatIP(
            dimension
        )

        self.embedded_chunks: list[
            EmbeddedChunk
        ] = []

    # Adds new chunks to the index.
    def add(
        self,
        embedded_chunks: list[
            EmbeddedChunk
        ],
    ) -> None:

        vectors = np.array(
            [
                chunk.embedding
                for chunk in embedded_chunks
            ],
            dtype=np.float32,
        )

        self.index.add(vectors)

        self.embedded_chunks.extend(
            embedded_chunks
        )

        logger.info(
            f"Indexed {len(embedded_chunks)} chunk(s)."
        )

    # Retrieves top chunks based on query embedding.
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[EmbeddedChunk]:

        query = np.array(
            [query_embedding],
            dtype=np.float32,
        )

        _, indices = self.index.search(
            query,
            top_k,
        )

        results = []

        for idx in indices[0]:

            if idx == -1:
                continue

            results.append(
                self.embedded_chunks[idx]
            )

        logger.info(
            f"Retrieved {len(results)} chunk(s)."
        )

        return results

    # Saves FAISS index and associated metadata files.
    def save(self) -> None:

        self.index_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.metadata_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        faiss.write_index(
            self.index,
            str(self.index_path),
        )

        metadata = [

            EmbeddedChunkMapper.to_dict(chunk)

            for chunk in self.embedded_chunks

        ]

        with open(
            self.metadata_path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                metadata,
                file,
                indent=4,
            )

        logger.info(
            "FAISS index and metadata saved successfully."
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
            
        self.index.reset()
        if self.embedded_chunks:
            vectors = np.array(
                [chunk.embedding for chunk in self.embedded_chunks],
                dtype=np.float32,
            )
            self.index.add(vectors)
            
        self.save()
        logger.info(f"Deleted chunks for document {document_id} from FAISS. Remaining: {len(self.embedded_chunks)}")

    # Loads FAISS index and associated metadata data.
    def load(self) -> None:

        if not self.index_path.exists():

            logger.warning(
                "No FAISS index found."
            )

            return

        self.index = faiss.read_index(
            str(self.index_path)
        )

        if not self.metadata_path.exists():

            logger.warning(
                "No metadata file found."
            )

            return

        with open(
            self.metadata_path,
            "r",
            encoding="utf-8",
        ) as file:

            metadata = json.load(file)

        vectors = self.index.reconstruct_n(
            0,
            self.index.ntotal,
        )

        self.embedded_chunks = []

        for data, vector in zip(
            metadata,
            vectors,
        ):

            self.embedded_chunks.append(

                EmbeddedChunkMapper.from_dict(
                    data,
                    vector.tolist(),
                )

            )

        logger.info(
            f"Loaded {len(self.embedded_chunks)} embedded chunks."
        )