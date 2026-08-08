"""
Embedding Manager.

Handles loading the embedding model
and generating embeddings.
"""

from sentence_transformers import SentenceTransformer

from pipeline.core.logging import LoggerManager

logger = LoggerManager.get_logger()


# Generates embeddings for input text strings.
class EmbeddingManager:
    """
    Enterprise Embedding Manager.
    """

    # Initializes the model name and internal model.
    def __init__(
        self,
        model_name: str ,
    ) -> None:

        self.model_name = model_name

        self._model = None

    @property
    # Loads and returns the sentence transformer model.
    def model(self) -> SentenceTransformer:
        """
        Lazy-load the embedding model.
        """

        if self._model is None:

            logger.info(
                f"Loading embedding model: {self.model_name}"
            )

            self._model = SentenceTransformer(
                self.model_name
            )

            logger.info(
                "Embedding model loaded successfully."
            )

        return self._model

    # Generates an embedding for input text.
    def embed_text(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate embedding for one text.
        """

        embedding = self.model.encode(
            text,
            normalize_embeddings=True,
        )

        return embedding.tolist()

    # Generates embeddings for a list of texts.
    def embed_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        """

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )

        return embeddings.tolist()