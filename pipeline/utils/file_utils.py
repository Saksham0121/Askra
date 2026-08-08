"""
File Utility Functions.

Provides helper functions for working with files.
"""

import hashlib
from pathlib import Path

from src.core.logging import LoggerManager

logger = LoggerManager.get_logger()


# Calculates the SHA256 hash of a file.
def calculate_sha256(
    file_path: str | Path,
    chunk_size: int = 8192,
) -> str:
    """
    Calculate SHA256 hash of a file.

    Args:
        file_path: Path to the file.
        chunk_size: Bytes to read at a time.

    Returns:
        Hexadecimal SHA256 hash.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    sha256 = hashlib.sha256()

    with open(file_path, "rb") as file:

        while chunk := file.read(chunk_size):
            sha256.update(chunk)

    digest = sha256.hexdigest()

    logger.info(
        f"Calculated SHA256 for {file_path.name}"
    )

    return digest