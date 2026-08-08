"""
RAGPipeline — Unified Singleton Facade.

This is the single object that backend.py interacts with.  It owns both:
  - the offline ingestion path (IngestionOrchestrator via IngestionFactory)
  - the online query path   (OnlinePipeline   via PipelineFactory)

After every successful ingestion the FAISS and BM25 indices held by the
online pipeline's retriever are reloaded from disk so newly added documents
are immediately searchable without a server restart.

Usage
-----
    pipeline = RAGPipeline.get()
    result   = pipeline.ingest(file_bytes, "report.pdf")
    answer   = pipeline.query("What is the scope of Section 4?")
"""

from __future__ import annotations

import tempfile
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pipeline.core.config import ApplicationConfig
from pipeline.core.logging import LoggerManager
from pipeline.ingestion.ingestion_factory import IngestionFactory
from pipeline.models import Document
from pipeline.pipeline.pipeline_factory import PipelineFactory
from pipeline.pipeline.pipeline_result import PipelineResult

logger = LoggerManager.get_logger()

_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass
# Represents the outcome of a RAG pipeline ingest.
class IngestResult:
    """Returned by RAGPipeline.ingest()."""

    document_id: str
    filename: str
    status: str          # "ready" | "failed"
    total_pages: int = 0
    total_chunks: int = 0


@dataclass
# Represents a query result with answer and sources.
class QueryResult:
    """Returned by RAGPipeline.query()."""

    answer: str
    sources: list[str] = field(default_factory=list)
    latency_ms: int = 0


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

# Orchestrates retrieval and generation within RAG.
class RAGPipeline:
    """
    Unified RAG Pipeline singleton.

    Call RAGPipeline.get() to obtain the shared instance.
    """

    _instance: Optional["RAGPipeline"] = None

    # ------------------------------------------------------------------
    # Singleton accessor
    # ------------------------------------------------------------------

    @classmethod
    # Returns or creates the shared RAGPipeline instance.
    def get(cls) -> "RAGPipeline":
        """
        Return the shared RAGPipeline instance, creating it on first call.
        """
        if cls._instance is None:
            with _lock:
                if cls._instance is None:
                    cls._instance = cls._create()
        return cls._instance

    @classmethod
    # Creates and configures the RAGPipeline instance.
    def _create(cls) -> "RAGPipeline":
        logger.info("Initialising RAGPipeline…")
        instance = cls()
        instance._config = ApplicationConfig()
        instance._ingestion = IngestionFactory.create()
        instance._online = PipelineFactory.create()
        instance._agentic = None   # built lazily on first agentic_query() call
        logger.info("RAGPipeline ready.")
        return instance

    # ------------------------------------------------------------------
    # Ingestion
    # ------------------------------------------------------------------

    # Ingests a PDF document into the system.
    def ingest(self, file_bytes: bytes, filename: str) -> IngestResult:
        """
        Ingest a PDF document supplied as raw bytes.

        Uses a temp directory named with the original filename so the document
        registry stores the correct display name, not a system temp name.
        """

        logger.info(f"Ingesting document: {filename}")

        import tempfile as _tmpmod
        tmp_dir = Path(_tmpmod.mkdtemp())
        tmp_path = tmp_dir / filename   # preserves original filename

        try:
            tmp_path.write_bytes(file_bytes)
            self._ingestion.ingest_document(tmp_path)

        except FileExistsError:
            logger.info(f"{filename} already indexed — returning existing record.")
            from pipeline.utils import calculate_sha256
            file_hash = calculate_sha256(tmp_path)
            doc = self._ingestion.repository.get_by_hash(file_hash)
            tmp_path.unlink(missing_ok=True)
            try:
                tmp_dir.rmdir()
            except Exception:
                pass
            if doc is not None:
                return IngestResult(
                    document_id=doc.document_id,
                    filename=doc.filename,
                    status="ready",
                    total_pages=doc.total_pages,
                    total_chunks=doc.total_chunks,
                )
            return IngestResult(document_id="unknown", filename=filename, status="ready")

        except Exception as exc:
            logger.error(f"Ingestion failed for {filename}: {exc}")
            tmp_path.unlink(missing_ok=True)
            try:
                tmp_dir.rmdir()
            except Exception:
                pass
            return IngestResult(document_id="", filename=filename, status="failed")

        # Ingestion succeeded — retrieve record by hash
        from pipeline.utils import calculate_sha256
        file_hash = calculate_sha256(tmp_path)
        tmp_path.unlink(missing_ok=True)
        try:
            tmp_dir.rmdir()
        except Exception:
            pass

        doc = self._ingestion.repository.get_by_hash(file_hash)

        # Hot-reload so the online pipeline sees the new data immediately
        self._reload_indices()

        if doc is not None:
            return IngestResult(
                document_id=doc.document_id,
                filename=doc.filename,
                status="ready",
                total_pages=doc.total_pages,
                total_chunks=doc.total_chunks,
            )

        return IngestResult(document_id="", filename=filename, status="ready")


    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    # Executes the RAG pipeline for a question.
    def query(self, question: str) -> QueryResult:
        """
        Run the online RAG pipeline for a user question.

        Parameters
        ----------
        question:
            Natural-language query.

        Returns
        -------
        QueryResult
            Generated answer with source references and latency.
        """

        start = time.perf_counter()

        logger.info(f"Running query: {question!r}")

        answer = self._online.ask(question)

        latency_ms = int((time.perf_counter() - start) * 1000)

        # Extract source filenames from the retriever's last result set.
        # The context_builder already formatted the context — we pull sources
        # from the retriever directly for the sources list in the UI.
        sources = self._collect_sources(question)

        return QueryResult(
            answer=answer,
            sources=sources,
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # Document management
    # ------------------------------------------------------------------

    # Returns all documents from the registry.
    def list_documents(self) -> list[Document]:
        """Return all documents in the registry."""
        return self._ingestion.repository.list_documents()

    # Deletes document and associated vectors.
    def delete_document(self, document_id: str) -> None:
        """
        Remove a document from the registry and vectors from FAISS/BM25.
        """
        logger.info(f"Deleting document: {document_id}")
        self._ingestion.repository.delete(document_id)
        
        # Remove vectors from indexes
        try:
            self._online.retriever.dense_retriever.faiss_manager.delete_by_document_id(document_id)
            self._online.retriever.sparse_retriever.bm25_manager.delete_by_document_id(document_id)
            logger.info(f"Successfully deleted vectors for {document_id}")
        except Exception as exc:
            logger.error(f"Failed to delete vectors for {document_id}: {exc}")

    # Executes the complete agentic query pipeline.
    def agentic_query(
        self,
        question: str,
        direct_rag: bool = False,
    ) -> PipelineResult:
        """
        Run the full agentic pipeline (guardrail → router → tool →
        validation → reflection → answer generation).

        Parameters
        ----------
        question   : User's question.
        direct_rag : If True, skip routing and go straight to RAG tool.

        Returns
        -------
        PipelineResult
            Full result including confidence score, source label, and citations.
        """

        # Build the AgenticPipeline lazily (shares self._online to avoid
        # loading embedding + reranker models twice)
        if self._agentic is None:
            from pipeline.pipeline.agentic_pipeline import AgenticPipeline
            self._agentic = AgenticPipeline.create(self._online)

        return self._agentic.run(question, direct_rag=direct_rag)

    # Executes the agentic pipeline for streaming results.
    def agentic_query_stream(
        self,
        question: str,
        direct_rag: bool = False,
    ):
        """
        Run the full agentic pipeline and yield a stream of events.
        """
        if self._agentic is None:
            from pipeline.pipeline.agentic_pipeline import AgenticPipeline
            self._agentic = AgenticPipeline.create(self._online)

        return self._agentic.run_stream(question, direct_rag=direct_rag)



    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    # Reloads FAISS and BM25 indices for retrieval.
    def _reload_indices(self) -> None:
        """
        Hot-reload FAISS and BM25 indices into the online pipeline's
        retriever after a new document has been ingested.
        """

        logger.info("Hot-reloading retrieval indices…")

        try:
            config = self._config

            # Reload FAISS
            self._online.retriever.dense_retriever.faiss_manager.load()

            # Reload BM25
            bm25_path = Path(
                config.storage["bm25"]["index_path"]
            )

            if bm25_path.exists():
                self._online.retriever.sparse_retriever.bm25_manager.load()

            logger.info("Retrieval indices reloaded successfully.")

        except Exception as exc:
            logger.warning(
                f"Index hot-reload failed (query will use stale index): {exc}"
            )

    # Collects unique source filenames from search results.
    def _collect_sources(self, query: str) -> list[str]:
        """
        Return a deduplicated list of source filenames from a lightweight
        retrieval pass (top-5 dense only) for UI display.
        """

        try:
            dense = self._online.retriever.dense_retriever
            embedding = dense.embedding_manager.embed_text(query)
            chunks = dense.faiss_manager.search(embedding, top_k=5)
            seen: set[str] = set()
            sources: list[str] = []
            for chunk in chunks:
                src = chunk.chunk.source
                if src not in seen:
                    seen.add(src)
                    sources.append(src)
            return sources

        except Exception:
            return []
