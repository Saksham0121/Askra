"""
Offline Ingestion Orchestrator.

Coordinates the complete offline ingestion pipeline.
"""

from pathlib import Path

from pipeline.core.logging import LoggerManager

from pipeline.embeddings import EmbeddingManager

from pipeline.ingestion.metadata_enricher import MetadataEnricher
from pipeline.ingestion.metadata_extractor import MetadataExtractor
from pipeline.ingestion.pdf_loader import PDFDocumentLoader

from pipeline.preprocessing.chunking_service import ChunkingService
from pipeline.preprocessing.text_cleaner import TextCleaner

from pipeline.retrieval.faiss_manager import FAISSManager
from pipeline.retrieval.bm25_manager import BM25Manager

from pipeline.storage.repositories.sqlite_document_repository import (
    SQLiteDocumentRepository,
)

from datetime import datetime
from uuid import uuid4

from pipeline.models import (
    Document,
    DocumentStatus,
)

from pipeline.utils import calculate_sha256
from pipeline.models import EmbeddedChunk

from dataclasses import replace

logger = LoggerManager.get_logger()


# Coordinates the offline document ingestion pipeline.
class IngestionOrchestrator:
    """
    Coordinates the complete offline ingestion pipeline.
    """

    # Sets up dependencies for document processing pipeline
    def __init__(
        self,
        repository: SQLiteDocumentRepository,
        pdf_loader: PDFDocumentLoader,
        metadata_extractor: MetadataExtractor,
        metadata_enricher: MetadataEnricher,
        text_cleaner: TextCleaner,
        chunking_service: ChunkingService,
        embedding_manager: EmbeddingManager,
        faiss_manager: FAISSManager,
        bm25_manager: BM25Manager,
    ) -> None:

        self.repository = repository

        self.pdf_loader = pdf_loader

        self.metadata_extractor = metadata_extractor

        self.metadata_enricher = metadata_enricher

        self.text_cleaner = text_cleaner

        self.chunking_service = chunking_service

        self.embedding_manager = embedding_manager

        self.faiss_manager = faiss_manager

        self.bm25_manager = bm25_manager

    # Registers a new document in the registry.
    def _register_document(
        self,
        pdf_path: Path,
    ) -> Document:
        """
        Register a new document in the registry.

        Calculates the SHA256 hash, checks for duplicates,
        creates the Document object and stores it in the
        registry.

        Returns:
            The newly created Document.

        Raises:
            FileExistsError:
                If the document has already been indexed.
        """

        file_hash = calculate_sha256(pdf_path)

        if self.repository.exists_by_hash(file_hash):

            raise FileExistsError(
                f"{pdf_path.name} has already been indexed."
            )

        document = Document(

            document_id=str(uuid4()),

            filename=pdf_path.name,

            file_hash=file_hash,

            upload_timestamp=datetime.now(),

            indexed_timestamp=None,

            publication_date=None,

            effective_date=None,

            document_version=None,

            total_pages=0,

            total_chunks=0,

            language=None,

            embedding_model=None,

            embedding_version=None,

            index_version=None,

            status=DocumentStatus.INDEXING,
        )

        self.repository.add(document)

        logger.info(
            f"Registered document: {document.filename}"
        )

        return document
    
    # Loads and prepares the document content.
    def _load_document(
        self,
        pdf_path: Path,
    ):
        """
        Load and prepare a document.
        """

        content = self.pdf_loader.load(
            pdf_path
        )

        logger.info(
            "PDF loaded."
        )

        content = self.metadata_extractor.extract(
            content
        )

        logger.info(
            "Metadata extracted."
        )

        content = self.metadata_enricher.enrich(
            content
        )

        logger.info(
            "Metadata enriched."
        )

        content = self.text_cleaner.clean(
            content
        )

        logger.info(
            "Text cleaned."
        )

        return content
    

    # Prepares document metadata and creates content chunks.
    def _prepare_document(
        self,
        document: Document,
        content,
    ) -> tuple[Document, list]:
        """
        Update document metadata and create chunks.
        """

        document = replace(
            document,
            publication_date=content.metadata.publication_date,
            effective_date=content.metadata.effective_date,
            document_version=content.metadata.version,
            language=content.metadata.language,
            total_pages=len(content.pages),
        )

        chunks = self.chunking_service.chunk_document(
            document,
            content,
        )

        document = replace(
            document,
            total_chunks=len(chunks),
        )

        self.repository.update(
            document
        )

        logger.info(
            f"Created {len(chunks)} chunks."
        )

        return document, chunks
    

    # Generates embeddings and creates EmbeddedChunk objects.
    def _embed_chunks(
        self,
        chunks,
    ) -> list[EmbeddedChunk]:
        """
        Generate embeddings for chunks.
        """

        embeddings = self.embedding_manager.embed_batch(
            [chunk.text for chunk in chunks]
        )

        logger.info(
            "Embeddings generated."
        )

        embedded_chunks = [

            EmbeddedChunk(
                chunk=chunk,
                embedding=embedding,
            )

            for chunk, embedding in zip(
                chunks,
                embeddings,
            )
        ]

        logger.info(
            f"Created {len(embedded_chunks)} embedded chunks."
        )

        return embedded_chunks
    
    # Indexes documents using FAISS and BM25.
    def _index_document(
        self,
        embedded_chunks: list[EmbeddedChunk],
    ) -> None:
        """
        Index embedded chunks in FAISS and BM25.
        """

        # --------------------------------------------------
        # FAISS
        # --------------------------------------------------

        self.faiss_manager.add(
            embedded_chunks
        )

        self.faiss_manager.save()

        logger.info(
            "FAISS updated."
        )

        # --------------------------------------------------
        # BM25
        # --------------------------------------------------

        self.bm25_manager.build(
            embedded_chunks
        )

        self.bm25_manager.save()

        logger.info(
            "BM25 updated."
        )

    # Marks document as indexed and updates repository.
    def _finalize_document(
        self,
        document: Document,
    ) -> None:
        """
        Mark the document as successfully indexed.
        """

        document = replace(
            document,
            indexed_timestamp=datetime.now(),
            status=DocumentStatus.INDEXED,
        )

        self.repository.update(
            document
        )

        logger.info(
            f"{document.filename} indexed successfully."
        )

    # Marks a document as failed and updates repository.
    def _mark_document_failed(
        self,
        document: Document,
    ) -> None:
        """
        Mark the document as failed.
        """

        document = replace(
            document,
            status=DocumentStatus.FAILED,
        )

        self.repository.update(
            document
        )

        logger.info(
            f"{document.filename} marked as FAILED."
        )

    # Ingests a PDF document for indexing.
    def ingest_document(
        self,
        pdf_path: str | Path,
    ) -> None:
        """
        Ingest a single PDF.
        """

        pdf_path = Path(pdf_path)

        document = None

        logger.info(
            f"Starting ingestion: {pdf_path.name}"
        )

        try:

            # --------------------------------------------------
            # SHA256
            # --------------------------------------------------

            try:

                document = self._register_document(
                    pdf_path
                )

            except FileExistsError:

                logger.info(
                    f"{pdf_path.name} already indexed."
                )

                return

            # --------------------------------------------------
            # Load & Prepare Document
            # --------------------------------------------------

            content = self._load_document(
                pdf_path
            )

            # --------------------------------------------------
            # Prepare Document
            # --------------------------------------------------

            document, chunks = self._prepare_document(
                document,
                content,
            )

            # --------------------------------------------------
            # Generate Embeddings
            # --------------------------------------------------

            embedded_chunks = self._embed_chunks(
                chunks
            )

            # --------------------------------------------------
            # Index Document
            # --------------------------------------------------

            self._index_document(
                embedded_chunks
            )

            # --------------------------------------------------
            # Finalize Document
            # --------------------------------------------------


            self._finalize_document(
                document
            )

        except Exception as error:

            logger.exception(
                f"Failed to ingest {pdf_path.name}: {error}"
            )

            if document is not None:

                self._mark_document_failed(
                    document
                )

            raise