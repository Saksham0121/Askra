"""
Application Configuration Manager.

Loads all YAML configuration files during startup
and exposes them throughout the application.
"""

from pathlib import Path
from typing import Any

import yaml

from src.core.logging import LoggerManager

logger = LoggerManager.get_logger()


# Loads configuration files for the application.
class ApplicationConfig:
    """
    Centralized application configuration.
    """

    # Loads application configuration from YAML files.
    def __init__(self) -> None:

        self.application = self._load_yaml("application")

        self.logging = self._load_yaml("logging")

        self.models = self._load_yaml("models")

        self.storage = self._load_yaml("storage")

        logger.info(
            "Application configuration loaded successfully."
        )

    @staticmethod
    # Loads configuration data from a YAML file.
    def _load_yaml(
        name: str,
    ) -> dict[str, Any]:

        path = Path("configs") / f"{name}.yaml"

        if not path.exists():

            raise FileNotFoundError(
                f"Configuration file not found: {path}"
            )

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:

            return yaml.safe_load(file)