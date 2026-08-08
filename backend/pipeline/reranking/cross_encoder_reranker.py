"""
Cross Encoder Reranker.

Re-ranks retrieved chunks using a cross-encoder model.
"""

from sentence_transformers import CrossEncoder

from pipeline.core.logging import LoggerManager
from pipeline.models import EmbeddedChunk

logger = LoggerManager.get_logger()


# Re-ranks search results using a cross-encoder model.
class CrossEncoderReranker:
    """
    Cross-encoder based reranker.
    """

    # Sets the model name and initializes the model.
    def __init__(
        self,
        model_name: str,
    ) -> None:

        self.model_name = model_name

        self._model = None

    @property
    # Loads and returns the CrossEncoder model.
    def model(
        self,
    ) -> CrossEncoder:

        if self._model is None:

            logger.info(
                f"Loading reranker: {self.model_name}"
            )

            self._model = CrossEncoder(
                self.model_name
            )

            logger.info(
                "Reranker loaded successfully."
            )

        return self._model

    # Reorders chunks based on relevance scores.
    def rerank(
        self,
        query: str,
        chunks: list[EmbeddedChunk],
        top_k: int = 5,
    ) -> list[EmbeddedChunk]:
        """
        Re-rank retrieved chunks.
        """

        pairs = [

            (
                query,
                chunk.chunk.text,
            )

            for chunk in chunks
        ]

        scores = self.model.predict(
            pairs
        )

        ranked = sorted(

            zip(
                chunks,
                scores,
            ),

            key=lambda item: item[1],

            reverse=True,

        )

        return [

            chunk

            for chunk, _ in ranked[:top_k]

        ]