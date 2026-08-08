"""
Ingestion Factory.

Builds a fully configured IngestionOrchestrator.
"""

from pipeline.core.config import ApplicationConfig

from pipeline.embeddings import EmbeddingManager

from pipeline.ingestion.ingestion_orchestrator import (
    IngestionOrchestrator,
)

from pipeline.ingestion.metadata_enricher import (
    MetadataEnricher,
)

from pipeline.ingestion.metadata_extractor import (
    MetadataExtractor,
)

from pipeline.ingestion.pdf_loader import (
    PDFDocumentLoader,
)

from pipeline.preprocessing.chunking_service import (
    ChunkingService,
)

from pipeline.preprocessing.text_cleaner import (
    TextCleaner,
)

from pipeline.retrieval import (
    BM25Manager,
    FAISSManager,
)

from pipeline.storage.repositories.sqlite_document_repository import (
    SQLiteDocumentRepository,
)


# Creates an IngestionOrchestrator based on config.
class IngestionFactory:
    """
    Factory for creating an IngestionOrchestrator.
    """

    @staticmethod
    # Sets up and loads necessary components.
    def create() -> IngestionOrchestrator:

        config = ApplicationConfig()

        repository = SQLiteDocumentRepository()

        pdf_loader = PDFDocumentLoader()

        metadata_extractor = MetadataExtractor()

        metadata_enricher = MetadataEnricher()

        text_cleaner = TextCleaner()

        chunking_service = ChunkingService()

        embedding_manager = EmbeddingManager(
            model_name=config.models["embeddings"]["model"],
        )

        faiss_manager = FAISSManager(
            dimension=config.models["embeddings"]["dimension"],
            index_path=config.storage["faiss"]["index_path"],
            metadata_path=config.storage["faiss"]["metadata_path"],
        )

        faiss_manager.load()

        bm25_manager = BM25Manager(
            index_path=config.storage["bm25"]["index_path"],
        )

        try:
            bm25_manager.load()

        except FileNotFoundError:
            pass

        return IngestionOrchestrator(
            repository=repository,
            pdf_loader=pdf_loader,
            metadata_extractor=metadata_extractor,
            metadata_enricher=metadata_enricher,
            text_cleaner=text_cleaner,
            chunking_service=chunking_service,
            embedding_manager=embedding_manager,
            faiss_manager=faiss_manager,
            bm25_manager=bm25_manager,
        )