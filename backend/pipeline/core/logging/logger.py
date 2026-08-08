"""
Centralized logging module.

Responsibilities:
- Configure application logging.
- Create the log directory if it does not exist.
- Provide a singleton logger instance.
- Read logging configuration from YAML.
"""

from pathlib import Path
import sys
from typing import Final

import yaml
from loguru import logger


DEFAULT_LOG_CONFIG: Final[str] = "configs/logging.yaml"
DEFAULT_LOG_FILE: Final[str] = "logs/agentic_rag.log"


# Manages and configures the application logging system.
class LoggerManager:
    """
    Singleton Logger Manager.

    This class is responsible for configuring the application's
    logging system only once during startup.
    """

    _configured: bool = False

    @classmethod
    # Configures the application logger from YAML.
    def configure(cls, config_path: str = DEFAULT_LOG_CONFIG) -> None:
        """
        Configure the application logger.

        Parameters
        ----------
        config_path : str
            Path to the logging configuration YAML file.
        """

        if cls._configured:
            return

        log_directory = Path("logs")
        log_directory.mkdir(parents=True, exist_ok=True)

        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        logger.remove()

        if config["console"]["enabled"]:
            logger.add(
                sys.stdout,
                level=config["logging"]["level"],
                colorize=True,
            )

        if config["file"]["enabled"]:
            logger.add(
                DEFAULT_LOG_FILE,
                level=config["logging"]["level"],
                rotation=config["logging"]["rotation"],
                retention=config["logging"]["retention"],
                compression=config["logging"]["compression"],
                enqueue=True,
                backtrace=True,
                diagnose=True,
            )

        cls._configured = True

        logger.info("Logger initialized successfully.")

    @staticmethod
    # Returns the configured Loguru application logger.
    def get_logger():
        """
        Return the configured Loguru logger.

        Returns
        -------
        loguru.Logger
            Shared application logger.
        """
        return logger