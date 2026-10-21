"""
Cross Encoder Reranker.

Re-ranks retrieved chunks using a cross-encoder model.
"""

import os
from typing import Any

from pipeline.core.logging import LoggerManager
from pipeline.models import EmbeddedChunk

logger = LoggerManager.get_logger()

# Check available reranker backends (flashrank ONNX preferred for <512MB RAM environments)
try:
    from flashrank import Ranker, RerankRequest
    HAS_FLASHRANK = True
except ImportError:
    HAS_FLASHRANK = False

try:
    from sentence_transformers import CrossEncoder
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False


class CrossEncoderReranker:
    """
    Reranker supporting ultra-lightweight ONNX via FlashRank (~4MB model, ~20MB RAM)
    with toggle support and graceful fallbacks.
    """

    def __init__(
        self,
        model_name: str = "ms-marco-TinyBERT-L-2-v2",
        enabled: bool = True,
        cache_dir: str | None = None,
    ) -> None:
        self.model_name = model_name
        self.enabled = enabled
        self.cache_dir = cache_dir or os.environ.get("MODEL_CACHE_DIR", None)
        self._model: Any = None
        self._backend: str | None = None

        if not self.enabled:
            logger.info("Reranker is disabled by configuration. Retrieval will use dense/sparse hybrid ordering.")
        elif HAS_FLASHRANK:
            self._backend = "flashrank"
        elif HAS_SENTENCE_TRANSFORMERS:
            self._backend = "sentence_transformers"
        else:
            self._backend = None
            logger.warning("No reranking library (flashrank or sentence-transformers) found. Pass-through mode active.")

    @property
    def model(self) -> Any:
        """
        Lazy-load the reranker model using the leanest available engine.
        """
        if not self.enabled:
            return None

        if self._model is None and self._backend:
            if self._backend == "flashrank":
                logger.info(
                    f"Loading ultra-lightweight ONNX reranker via FlashRank: {self.model_name} (cache_dir={self.cache_dir})"
                )
                self._model = Ranker(
                    model_name=self.model_name,
                    cache_dir=self.cache_dir or "/tmp",
                )
                logger.info("FlashRank ONNX reranker loaded successfully.")
            elif self._backend == "sentence_transformers":
                logger.info(
                    f"Loading PyTorch reranker via SentenceTransformer: {self.model_name}"
                )
                self._model = CrossEncoder(self.model_name)
                logger.info("SentenceTransformer reranker loaded successfully.")

        return self._model

    def warmup(self) -> None:
        """Pre-load model weights into memory on startup if reranking is enabled."""
        if not self.enabled:
            return
        try:
            if self._backend == "flashrank":
                # Warm up flashrank with a single dummy query
                _ = self.model
                req = RerankRequest(query="warmup", passages=[{"id": 0, "text": "warmup passage"}])
                self.model.rerank(req)
            elif self._backend == "sentence_transformers":
                _ = self.model
        except Exception as exc:
            logger.warning(f"Reranker warmup warning: {exc}")

    def rerank(
        self,
        query: str,
        chunks: list[EmbeddedChunk],
        top_k: int = 5,
    ) -> list[EmbeddedChunk]:
        """
        Re-rank retrieved chunks.
        """
        if not chunks:
            return []

        if not self.enabled or self.model is None:
            return chunks[:top_k]

        try:
            if self._backend == "flashrank":
                passages = [
                    {"id": idx, "text": chunk.chunk.text}
                    for idx, chunk in enumerate(chunks)
                ]
                req = RerankRequest(query=query, passages=passages)
                results = self.model.rerank(req)
                return [chunks[r["id"]] for r in results[:top_k]]

            elif self._backend == "sentence_transformers":
                pairs = [(query, chunk.chunk.text) for chunk in chunks]
                scores = self.model.predict(pairs)
                ranked = sorted(
                    zip(chunks, scores),
                    key=lambda item: item[1],
                    reverse=True,
                )
                return [chunk for chunk, _ in ranked[:top_k]]

        except Exception as exc:
            logger.error(f"Reranking encountered an error ({exc}), falling back to candidate order.")

        return chunks[:top_k]