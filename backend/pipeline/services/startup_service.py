"""
Application Startup Service.

Responsible for initializing all core services
required before launching the application.
"""

from pathlib import Path

from pipeline.core.config import ApplicationConfig
from pipeline.core.logging import LoggerManager

logger = LoggerManager.get_logger()


# Initializes application components and configurations.
class StartupService:
    """
    Handles application startup.
    """

    REQUIRED_DIRECTORIES = [
        "logs",
        "configs",
        "data",
        "models",
        "docs",
        "tests",
    ]

    # Initializes application configuration settings.
    def __init__(self) -> None:
        self.config: ApplicationConfig | None = None

    # Sets up application components and Ollama models.
    def initialize(self) -> None:
        """
        Initialize the application.
        """

        LoggerManager.configure()

        logger.info("Initializing application...")

        self._verify_directories()

        self.config = ApplicationConfig()

        from pipeline.llm.groq_manager import GroqManager

        ollama = OllamaManager()

        if ollama.health_check():

            logger.info("Installed Ollama Models:")

            for model in ollama.list_models():

                logger.info(f"  • {model}")

        else:

            logger.warning("Ollama server is unavailable.")

        logger.info("Startup completed successfully.")

    # Verifies existence of necessary project directories.
    def _verify_directories(self) -> None:
        """
        Ensure all required directories exist.
        """

        for directory in self.REQUIRED_DIRECTORIES:
            Path(directory).mkdir(parents=True, exist_ok=True)

        logger.info("Required directories verified.")