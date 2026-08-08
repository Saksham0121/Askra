"""
Document Mapper.

Converts between Document domain objects
and SQLite rows.
"""

from datetime import datetime
from sqlite3 import Row

from src.models import Document
from src.models import DocumentStatus


# Transforms document data to a database dictionary.
class DocumentMapper:

    @staticmethod
    # Transforms Document object to a dictionary.
    def to_database(document: Document) -> dict:

        return {
            "document_id": document.document_id,
            "filename": document.filename,
            "file_hash": document.file_hash,
            "upload_timestamp": document.upload_timestamp.isoformat(),
            "indexed_timestamp": (
                document.indexed_timestamp.isoformat()
                if document.indexed_timestamp
                else None
            ),
            "publication_date": (
                document.publication_date.isoformat()
                if document.publication_date
                else None
            ),
            "effective_date": (
                document.effective_date.isoformat()
                if document.effective_date
                else None
            ),
            "document_version": document.document_version,
            "total_pages": document.total_pages,
            "total_chunks": document.total_chunks,
            "language": document.language,
            "embedding_model": document.embedding_model,
            "embedding_version": document.embedding_version,
            "index_version": document.index_version,
            "status": document.status.value,
        }

    @staticmethod
    # Transforms database row into a Document object.
    def from_database(row: Row) -> Document | None:

        if row is None:
            return None

        return Document(
            document_id=row["document_id"],
            filename=row["filename"],
            file_hash=row["file_hash"],
            upload_timestamp=datetime.fromisoformat(
                row["upload_timestamp"]
            ),
            indexed_timestamp=(
                datetime.fromisoformat(row["indexed_timestamp"])
                if row["indexed_timestamp"]
                else None
            ),
            publication_date=(
                datetime.fromisoformat(row["publication_date"])
                if row["publication_date"]
                else None
            ),
            effective_date=(
                datetime.fromisoformat(row["effective_date"])
                if row["effective_date"]
                else None
            ),
            document_version=row["document_version"],
            total_pages=row["total_pages"],
            total_chunks=row["total_chunks"],
            language=row["language"],
            embedding_model=row["embedding_model"],
            embedding_version=row["embedding_version"],
            index_version=row["index_version"],
            status=DocumentStatus(row["status"]),
        )