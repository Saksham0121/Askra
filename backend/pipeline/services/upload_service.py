"""
Upload Service.

Handles saving uploaded documents into the
local document repository.
"""

import shutil
from datetime import datetime
from pathlib import Path

from pipeline.core.logging import LoggerManager

logger = LoggerManager.get_logger()


# Handles document uploads and saves them.
class UploadService:
    """
    Handles document uploads.
    """

    ALLOWED_EXTENSIONS = {
        ".pdf",
    }

    # Creates and initializes the upload directory.
    def __init__(
        self,
        upload_directory: str,
    ) -> None:

        self.upload_directory = Path(upload_directory)

        self.upload_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    # Saves the uploaded document to storage.
    def upload(
        self,
        source_file: str | Path,
    ) -> Path:
        """
        Save an uploaded document.

        Args:
            source_file:
                Path of the uploaded file.

        Returns:
            Saved file path.
        """

        source_file = Path(source_file)

        if not source_file.exists():

            raise FileNotFoundError(
                f"{source_file} not found."
            )

        if (
            source_file.suffix.lower()
            not in self.ALLOWED_EXTENSIONS
        ):

            raise ValueError(
                "Only PDF documents are supported."
            )

        destination = (
            self.upload_directory
            / source_file.name
        )

        # Prevent overwriting an existing file.
        if destination.exists():

            timestamp = datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )

            destination = (
                self.upload_directory
                / f"{source_file.stem}_{timestamp}{source_file.suffix}"
            )

        shutil.copy2(
            source_file,
            destination,
        )

        logger.info(
            f"Uploaded document: {destination.name}"
        )

        return destination