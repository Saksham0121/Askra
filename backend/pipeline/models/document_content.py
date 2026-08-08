"""
Document Content Model.

Represents the extracted content of an uploaded document.
"""

from dataclasses import dataclass

from pipeline.models import DocumentMetadata


@dataclass(slots=True, frozen=True)
# Represents content for a single document page.
class PageContent:
    """
    Represents a single page of a document.
    """

    page_number: int

    text: str


@dataclass(slots=True, frozen=True)
# Represents document content and associated metadata.
class DocumentContent:
    """
    Represents the extracted content of a document.
    """

    metadata: DocumentMetadata

    pages: list[PageContent]