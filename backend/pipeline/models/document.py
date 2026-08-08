"""
Document Model.

Represents one uploaded document.
"""

from dataclasses import dataclass

from pipeline.models.enums import DocumentStatus

from datetime import datetime


@dataclass(slots=True, frozen=True)
# Represents an uploaded documents metadata.
class Document:
    """
    Represents one uploaded document.
    """

    document_id: str

    filename: str

    file_hash: str

    upload_timestamp: datetime

    indexed_timestamp: datetime | None

    publication_date: datetime | None

    effective_date: datetime | None

    document_version: str | None

    total_pages: int

    total_chunks: int

    language: str

    embedding_model: str

    embedding_version: str

    index_version: str

    status: DocumentStatus