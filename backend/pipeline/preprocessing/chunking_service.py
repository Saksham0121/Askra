"""
Chunking Service.

Creates retrieval-ready chunks from cleaned documents.
"""

from uuid import uuid4

from langchain_text_splitters import RecursiveCharacterTextSplitter

from pipeline.models import Chunk
from pipeline.models import Document
from pipeline.models import DocumentContent


# Splits documents into manageable chunks.
class ChunkingService:
    """
    Enterprise Chunking Service.
    """

    # Initializes the text splitting component.
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> None:

        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    # Splits the document into manageable chunks.
    def chunk_document(
        self,
        document: Document,
        content: DocumentContent,
    ) -> list[Chunk]:
        """
        Split document into chunks.
        """

        chunks = []

        chunk_number = 1

        for page in content.pages:

            page_chunks = self.splitter.split_text(
                page.text
            )

            for text in page_chunks:

                chunks.append(

                    Chunk(
                        chunk_id=str(uuid4()),

                        document_id=document.document_id,

                        source=document.filename,

                        page_number=page.page_number,

                        chunk_number=chunk_number,

                        text=text,

                        metadata=content.metadata,
                    )

                )

                chunk_number += 1

        return chunks