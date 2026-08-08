"""
Ollama Manager

Responsible for:
- Checking Ollama availability
- Listing installed models
- Providing a single interface to Ollama
"""

from ollama import Client

from pipeline.core.logging import LoggerManager

logger = LoggerManager.get_logger()


# Manages communication with the Ollama server.
class OllamaManager:
    """
    Handles communication with the local Ollama server.
    """

    # Initializes the client for vector database access
    def __init__(self, host: str = "http://localhost:11434") -> None:
        self.client = Client(host=host)

    # Verifies Ollamas availability and connectivity status.
    def health_check(self) -> bool:
        """
        Check whether Ollama is running.

        Returns
        -------
        bool
            True if Ollama is reachable.
        """

        try:
            self.client.list()

            logger.info("Successfully connected to Ollama.")

            return True

        except Exception as error:

            logger.error(f"Unable to connect to Ollama: {error}")

            return False

    # Lists available Ollama models from the client.
    def list_models(self) -> list[str]:
        """
        Return installed Ollama model names.
        """

        try:

            response = self.client.list()

            models = []

            for model in response.models:
                models.append(model.model)

            logger.info(f"Discovered {len(models)} Ollama model(s).")

            return models

        except Exception as error:

            logger.error(f"Failed to list models: {error}")

            return []
        
    # Generates a response from an Ollama model.
    def generate(
        self,
        model: str,
        prompt: str,
        options: dict | None = None,
    ) -> str:
        """
        Generate a response from an Ollama model.

        Parameters
        ----------
        model   : Ollama model name.
        prompt  : Full prompt string.
        options : Optional Ollama generation options, e.g.
                  {"num_predict": 512, "num_ctx": 2048, "temperature": 0.7}.
                  Passed directly to the Ollama client; unset keys use Ollama defaults.
        """

        try:

            response = self.client.generate(
                model=model,
                prompt=prompt,
                options=options or {},
            )

            logger.info(
                f"Generated response using model '{model}'."
            )

            return response.response

        except Exception as error:

            logger.error(
                f"Generation failed: {error}"
            )

            raise

    # Generates and yields streamed responses from models.
    def generate_stream(
        self,
        model: str,
        prompt: str,
        options: dict | None = None,
    ):
        """
        Generate a streamed response from an Ollama model.
        Yields strings as they arrive.

        Parameters
        ----------
        model   : Ollama model name.
        prompt  : Full prompt string.
        options : Optional Ollama generation options (same as ``generate``).
        """
        try:
            stream = self.client.generate(
                model=model,
                prompt=prompt,
                stream=True,
                options=options or {},
            )

            for chunk in stream:
                yield chunk["response"]

        except Exception as error:
            logger.error(f"Streaming generation failed: {error}")
            raise
