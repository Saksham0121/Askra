"""
Chunk Model.

Represents a chunk generated from a document.
"""

from dataclasses import dataclass

from pipeline.models.metadata import DocumentMetadata


@dataclass(slots=True, frozen=True)
# Represents a single document segment of data.
class Chunk:
    """
    Represents one document chunk.
    """

    chunk_id: str

    source: str

    document_id: str

    page_number: int

    chunk_number: int

    text: str

    metadata: DocumentMetadata