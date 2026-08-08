"""
Embedded Chunk Mapper.

Converts EmbeddedChunk objects to and from JSON-compatible dictionaries.
"""

from datetime import datetime

from pipeline.models import (
    Chunk,
    DocumentMetadata,
    EmbeddedChunk,
)


# Maps EmbeddedChunk objects to dictionaries.
class EmbeddedChunkMapper:
    """
    Maps EmbeddedChunk objects to dictionaries and back.
    """

    @staticmethod
    # Converts an EmbeddedChunk object to a dictionary.
    def to_dict(
        embedded_chunk: EmbeddedChunk,
    ) -> dict:

        chunk = embedded_chunk.chunk

        metadata = chunk.metadata

        return {

            "chunk": {

                "chunk_id": chunk.chunk_id,

                "document_id": chunk.document_id,

                "page_number": chunk.page_number,

                "chunk_number": chunk.chunk_number,

                "text": chunk.text,

                "source": chunk.source,

                "metadata": {

                    "title": metadata.title,

                    "author": metadata.author,

                    "subject": metadata.subject,

                    "keywords": metadata.keywords,

                    "publication_date": (
                        metadata.publication_date.isoformat()
                        if metadata.publication_date
                        else None
                    ),

                    "effective_date": (
                        metadata.effective_date.isoformat()
                        if metadata.effective_date
                        else None
                    ),

                    "version": metadata.version,

                    "language": metadata.language,
                },
            }
        }

    @staticmethod
    # Creates an EmbeddedChunk object from dictionary data.
    def from_dict(
        data: dict,
        embedding: list[float],
    ) -> EmbeddedChunk:

        chunk_data = data["chunk"]

        metadata_data = chunk_data["metadata"]

        metadata = DocumentMetadata(

            title=metadata_data["title"],

            author=metadata_data["author"],

            subject=metadata_data["subject"],

            keywords=metadata_data["keywords"],

            publication_date=(
                datetime.fromisoformat(
                    metadata_data["publication_date"]
                )
                if metadata_data["publication_date"]
                else None
            ),

            effective_date=(
                datetime.fromisoformat(
                    metadata_data["effective_date"]
                )
                if metadata_data["effective_date"]
                else None
            ),

            version=metadata_data["version"],

            language=metadata_data["language"],
        )

        chunk = Chunk(

            chunk_id=chunk_data["chunk_id"],

            document_id=chunk_data["document_id"],

            page_number=chunk_data["page_number"],

            chunk_number=chunk_data["chunk_number"],

            text=chunk_data["text"],

            source=chunk_data["source"],

            metadata=metadata,
        )

        return EmbeddedChunk(

            chunk=chunk,

            embedding=embedding,
        )