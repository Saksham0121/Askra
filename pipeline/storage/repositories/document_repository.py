"""
Document Repository Interface.

Defines the contract for all document repositories.
"""

from abc import ABC
from abc import abstractmethod

from src.models import Document


# Abstract base class for document storage.
class DocumentRepository(ABC):
    """
    Abstract document repository.
    """

    @abstractmethod
    # Stores a document in the system.
    def add(self, document: Document) -> None:
        """Store a document."""
        ...

    @abstractmethod
    # Retrieves document by SHA256 hash value.
    def get_by_hash(self, file_hash: str) -> Document | None:
        """Retrieve a document using its SHA256 hash."""
        ...

    @abstractmethod
    # Retrieves a document by its unique identifier.
    def get_by_id(self, document_id: str) -> Document | None:
        """Retrieve a document using its ID."""
        ...

    @abstractmethod
    # Updates the document with new information.
    def update(self, document: Document) -> None:
        """Update an existing document."""
        ...

    @abstractmethod
    # Deletes a document from the system.
    def delete(self, document_id: str) -> None:
        """Delete a document."""
        ...

    @abstractmethod
    # Returns a list of all indexed documents.
    def list_documents(self) -> list[Document]:
        """Return all indexed documents."""
        ...