"""
SQLite implementation of the Document Repository.
"""

from pipeline.core.logging import LoggerManager
from pipeline.models import Document
from pipeline.storage.database import SQLiteManager
from pipeline.storage.mappers import DocumentMapper
from pipeline.storage.repositories.document_repository import DocumentRepository

logger = LoggerManager.get_logger()


# Manages document storage using SQLite database.
class SQLiteDocumentRepository(DocumentRepository):
    """
    SQLite implementation of the Document Repository.
    """

    # Sets up database connection and table creation.
    def __init__(self) -> None:
        self.connection = SQLiteManager.get_connection()
        self.cursor = self.connection.cursor()

        self._create_table()

    # Creates the documents table if needed.
    def _create_table(self) -> None:
        """
        Create the documents table if it does not already exist.
        """

        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (

                document_id TEXT PRIMARY KEY,

                filename TEXT NOT NULL,

                file_hash TEXT UNIQUE NOT NULL,

                upload_timestamp TEXT,

                indexed_timestamp TEXT,

                publication_date TEXT,

                effective_date TEXT,

                document_version TEXT,

                total_pages INTEGER,

                total_chunks INTEGER,

                language TEXT,

                embedding_model TEXT,

                embedding_version TEXT,

                index_version TEXT,

                status TEXT

            );
            """
        )

        self.connection.commit()

        logger.info(
            "SQLite document table initialized."
        )

    # Adds a new document to the database.
    def add(
        self,
        document: Document,
    ) -> None:
        """
        Add a new document.
        """

        values = DocumentMapper.to_database(document)


        self.cursor.execute(
            """
            INSERT INTO documents
            VALUES (

                :document_id,

                :filename,

                :file_hash,

                :upload_timestamp,

                :indexed_timestamp,

                :publication_date,

                :effective_date,

                :document_version,

                :total_pages,

                :total_chunks,

                :language,

                :embedding_model,

                :embedding_version,

                :index_version,

                :status
            )
            """,
            values,
        )

        self.connection.commit()

        logger.info(
            f"Document '{document.filename}' added to registry."
        )

    # Retrieves a document based on SHA256 hash.
    def get_by_hash(
        self,
        file_hash: str,
    ):
        """
        Retrieve a document by its SHA256 hash.
        """

        self.cursor.execute(
            """
            SELECT *
            FROM documents
            WHERE file_hash = ?
            """,
            (file_hash,),
        )

        row = self.cursor.fetchone()

        if row is None:
            return None

        return DocumentMapper.from_database(row)

    # Checks if document exists by hash value.
    def exists_by_hash(
        self,
        file_hash: str,
    ) -> bool:
        """
        Check whether a document already exists.
        """

        return self.get_by_hash(file_hash) is not None

    # Retrieves a document based on its unique ID.
    def get_by_id(
        self,
        document_id: str,
    ):
        """
        Retrieve a document by its ID.
        """

        self.cursor.execute(
            """
            SELECT *
            FROM documents
            WHERE document_id = ?
            """,
            (document_id,),
        )

        row = self.cursor.fetchone()

        if row is None:
            return None

        return DocumentMapper.from_database(row)

    # Updates an existing document in the database.
    def update(
        self,
        document: Document,
    ) -> None:
        """
        Update an existing document.
        """

        values = DocumentMapper.to_database(document)

        
        self.cursor.execute(
            """
            UPDATE documents
            SET

                filename = :filename,

                upload_timestamp = :upload_timestamp,

                indexed_timestamp = :indexed_timestamp,

                publication_date = :publication_date,

                effective_date = :effective_date,

                document_version = :document_version,

                total_pages = :total_pages,

                total_chunks = :total_chunks,

                language = :language,

                embedding_model = :embedding_model,

                embedding_version = :embedding_version,

                index_version = :index_version,

                status = :status

            WHERE

                document_id = :document_id
            """,
            values,
        )

        self.connection.commit()

        logger.info(
            f"Updated document '{document.filename}'."
        )

    # Deletes a document from the documents table.
    def delete(
        self,
        document_id: str,
    ) -> None:
        """
        Delete a document.
        """

        self.cursor.execute(
            """
            DELETE
            FROM documents
            WHERE document_id = ?
            """,
            (document_id,),
        )

        self.connection.commit()

        logger.info(
            f"Deleted document '{document_id}'."
        )

    # Retrieves all documents from the database index.
    def list_documents(
        self,
    ) -> list[Document]:
        """
        Return all indexed documents.
        """

        self.cursor.execute(
            """
            SELECT *
            FROM documents
            """
        )

        rows = self.cursor.fetchall()

        return [
            DocumentMapper.from_database(row)
            for row in rows
        ]
    
    # Closes the SQLite connection and associated resources.
    def close(self) -> None:
        """
        Close the SQLite connection.
        """

        if self.cursor is not None:
            self.cursor.close()
            self.cursor = None

        if self.connection is not None:
            self.connection.close()
            self.connection = None

        logger.info(
            "SQLite connection closed."
        )

    