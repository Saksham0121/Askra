"""
Application Enums.
"""

from enum import Enum


# Represents document indexing status stages.
class DocumentStatus(str, Enum):
    """
    Document indexing lifecycle.
    """

    NEW = "NEW"

    INDEXING = "INDEXING"

    INDEXED = "INDEXED"

    FAILED = "FAILED"

    DELETED = "DELETED"