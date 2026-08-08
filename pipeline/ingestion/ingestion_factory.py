"""
Ingestion Factory.

Builds a fully configured IngestionOrchestrator.
"""

from src.core.config import ApplicationConfig

from src.embeddings import EmbeddingManager

from src.ingestion.ingestion_orchestrator import (
    IngestionOrchestrator,
)

from src.ingestion.metadata_enricher import (
    MetadataEnricher,
)

from src.ingestion.metadata_extractor import (
    MetadataExtractor,
)

from src.ingestion.pdf_loader import (
    PDFDocumentLoader,
)

from src.preprocessing.chunking_service import (
    ChunkingService,
)

from src.preprocessing.text_cleaner import (
    TextCleaner,
)

from src.retrieval import (
    BM25Manager,
    FAISSManager,
)

from src.storage.repositories.sqlite_document_repository import (
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