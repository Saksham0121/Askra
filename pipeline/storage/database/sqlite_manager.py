"""
SQLite Manager.

Creates and manages SQLite connections.
"""

import sqlite3
from pathlib import Path


# Manages and provides connections to SQLite databases.
class SQLiteManager:
    """
    SQLite connection manager.
    """

    DATABASE_PATH = Path(
        "data/registry/document_registry.db"
    )

    @classmethod
    # Overrides the database path for testing purposes.
    def set_database(
        cls,
        database_path: str | Path,
    ) -> None:
        """
        Override the database path.

        Useful for testing.
        """

        cls.DATABASE_PATH = Path(database_path)

    @classmethod
    # Creates and returns a SQLite database connection.
    def get_connection(
        cls,
    ) -> sqlite3.Connection:
        """
        Return a SQLite connection.
        """

        cls.DATABASE_PATH.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        connection = sqlite3.connect(
            cls.DATABASE_PATH,
            check_same_thread=False,
        )

        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON;")

        return connection