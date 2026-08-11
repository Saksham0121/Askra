"""
Pipeline Bridge.

Creates and wires the full AgenticPipeline using GroqManager
instead of OllamaManager. This is the single entry point
for FastAPI endpoints to interact with the pipeline.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pipeline.agent.base_tool import BaseTool
from pipeline.agent.router import AgentRouter
from pipeline.context.context_builder import ContextBuilder
from pipeline.embeddings.embedding_manager import EmbeddingManager
from pipeline.generation.prompt_builder import PromptBuilder
from pipeline.pipeline.agentic_pipeline import AgenticPipeline
from pipeline.pipeline.online_pipeline import OnlinePipeline
from pipeline.pipeline.pipeline_result import PipelineResult
from pipeline.reflection.reflector import Reflector
from pipeline.reranking import CrossEncoderReranker
from pipeline.retrieval.faiss_manager import FAISSManager
from pipeline.retrieval.bm25_manager import BM25Manager
from pipeline.retrieval.dense_retriever import DenseRetriever
from pipeline.retrieval.sparse_retriever import SparseRetriever
from pipeline.retrieval.hybrid_retriever import HybridRetriever
from pipeline.tools.chat_tool import ChatTool
from pipeline.tools.code_tool import CodeTool
from pipeline.tools.rag_tool import RAGTool
from pipeline.tools.ocr_tool import OCRTool
from pipeline.services.ocr_service import OCRService
from pipeline.validation.guardrail import Guardrail
from pipeline.validation.query_rewriter import QueryRewriter
from pipeline.validation.validation_layer import ValidationLayer

from pipeline.llm.groq_manager import GroqManager
from app.config import get_settings

import logging

logger = logging.getLogger("askrab")


class PipelineBridge:
    """
    Bridge connecting FastAPI endpoints to the underlying Askra RAG pipeline.
    Instantiates managers, retrievers, tools, and Agentic / Online pipelines.
    """

    def __init__(self, settings=None):
        if settings is None:
            settings = get_settings()

        self._settings = settings
        self._groq = GroqManager(api_key=settings.groq_api_key)

        # ── Embedding model (local, free) ───────────────────────────────
        self._embedding_manager = EmbeddingManager(
            model_name="all-MiniLM-L6-v2"   # 384-dim, fast, free
        )

        # ── FAISS vector store ───────────────────────────────────────────
        faiss_dir = os.path.abspath(settings.faiss_index_dir)
        os.makedirs(faiss_dir, exist_ok=True)
        self._faiss = FAISSManager(
            dimension=self._embedding_manager.dimension,
            index_path=os.path.join(faiss_dir, "index.faiss"),
            metadata_path=os.path.join(faiss_dir, "metadata.json"),
        )
        try:
            self._faiss.load()
        except Exception as exc:
            logger.warning(f"Failed to load FAISS index on startup: {exc}")

        # ── BM25 sparse retriever ────────────────────────────────────────
        self._bm25 = BM25Manager(
            index_path=os.path.join(faiss_dir, "bm25.pkl")
        )
        try:
            self._bm25.load()
        except Exception as exc:
            logger.warning(f"Failed to load BM25 index on startup: {exc}")

        # ── Hybrid retriever ─────────────────────────────────────────────
        dense_retriever = DenseRetriever(
            embedding_manager=self._embedding_manager,
            faiss_manager=self._faiss,
        )
        sparse_retriever = SparseRetriever(
            bm25_manager=self._bm25,
        )
        self._retriever = HybridRetriever(
            dense_retriever=dense_retriever,
            sparse_retriever=sparse_retriever,
        )

        # ── Reranker ─────────────────────────────────────────────────────
        self._reranker = CrossEncoderReranker(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

        # ── Context + prompt builders ────────────────────────────────────
        self._context_builder = ContextBuilder()
        self._prompt_builder = PromptBuilder()

        # ── Online pipeline (RAG core) ───────────────────────────────────
        self._online_pipeline = OnlinePipeline(
            retriever=self._retriever,
            reranker=self._reranker,
            context_builder=self._context_builder,
            prompt_builder=self._prompt_builder,
            groq_manager=self._groq,
            chat_model=settings.groq_chat_model,
        )

        # ── Tools ────────────────────────────────────────────────────────
        self._chat_tool = ChatTool(
            groq_manager=self._groq,
            model=settings.groq_chat_model,
        )

        self._code_tool = CodeTool(
            groq_manager=self._groq,
            model=settings.groq_code_model,
        )

        self._rag_tool = RAGTool(
            online_pipeline=self._online_pipeline,
            groq_manager=self._groq,
            fallback_model=settings.groq_chat_model,
        )

        # ── Validation layer ─────────────────────────────────────────────
        self._validator = ValidationLayer(
            groq_manager=self._groq,
            model=settings.groq_chat_model,
            threshold=settings.confidence_threshold,
            weights={
                "correctness": 0.5,
                "completeness": 0.3,
                "citations": 0.2,
            },
        )

        # ── Reflector ────────────────────────────────────────────────────
        self._reflector = Reflector(validator=self._validator)

        # ── Query rewriter ───────────────────────────────────────────────
        self._query_rewriter = QueryRewriter(
            groq_manager=self._groq,
            model=settings.groq_rewriter_model,
        )

        # ── Guardrail ────────────────────────────────────────────────────
        self._guardrail = Guardrail()

        # ── Router ───────────────────────────────────────────────────────
        self._router = AgentRouter(
            groq_manager=self._groq,
            model=settings.groq_router_model,
        )

        # ── OCR service + tool ──────────────────────────────────────────────
        self._ocr_service: OCRService | None = None
        self._ocr_tool: OCRTool | None = None

        if settings.ocr_enabled:
            self._ocr_service = OCRService(
                server_url=settings.ocr_server_url,
            )
            self._ocr_tool = OCRTool(
                ocr_service=self._ocr_service,
                upload_dir=settings.upload_dir,
            )
            logger.info(
                f"OCR service initialized (server: {settings.ocr_server_url}, "
                f"available: {self._ocr_service.is_available()})"
            )
        else:
            logger.info("OCR is disabled (OCR_ENABLED=false).")

        # ── Agentic pipeline ───────────────────────────────────────────────
        self._pipeline = AgenticPipeline(
            guardrail=self._guardrail,
            router=self._router,
            chat_tool=self._chat_tool,
            code_tool=self._code_tool,
            rag_tool=self._rag_tool,
            validator=self._validator,
            reflector=self._reflector,
            query_rewriter=self._query_rewriter,
            ocr_tool=self._ocr_tool,
        )

        logger.info("PipelineBridge initialized successfully.")

    @property
    def pipeline(self) -> AgenticPipeline:
        return self._pipeline

    @property
    def embedding_manager(self) -> EmbeddingManager:
        return self._embedding_manager

    @property
    def faiss_manager(self) -> FAISSManager:
        return self._faiss

    @property
    def bm25_manager(self) -> BM25Manager:
        return self._bm25

    @property
    def ocr_service(self) -> OCRService | None:
        return self._ocr_service

    def run(self, query: str, direct_rag: bool = False) -> PipelineResult:
        return self._pipeline.run(query, direct_rag=direct_rag)

    def run_stream(self, query: str, direct_rag: bool = False, history: list[dict] | None = None):
        return self._pipeline.run_stream(query, direct_rag=direct_rag, history=history or [])


_bridge_instance: PipelineBridge | None = None


def get_pipeline_bridge() -> PipelineBridge:
    """Return the singleton PipelineBridge, initializing it on first call."""
    global _bridge_instance
    if _bridge_instance is None:
        _bridge_instance = PipelineBridge()
    return _bridge_instance


def reset_pipeline_bridge() -> None:
    """Reset the singleton (useful for testing)."""
    global _bridge_instance
    _bridge_instance = None
