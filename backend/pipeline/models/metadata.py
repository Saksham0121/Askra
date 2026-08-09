"""
Metadata Model.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True, frozen=True)
class DocumentMetadata:
    """
    Metadata extracted from a document.
    """

    title: str | None = None
    author: str | None = None
    subject: str | None = None
    keywords: list[str] | None = None
    publication_date: datetime | None = None
    effective_date: datetime | None = None
    version: str | None = None
    language: str | None = None