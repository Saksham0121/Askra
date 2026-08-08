"""
Metadata Model.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
# Represents metadata associated with a document.
class DocumentMetadata:
    """
    Metadata extracted from a document.
    """

    title: str | None

    author: str | None

    subject: str | None

    keywords: list[str]

    publication_date: datetime | None

    effective_date: datetime | None

    version: str | None

    language: str | None