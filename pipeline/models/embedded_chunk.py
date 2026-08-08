"""
Embedded Chunk Model.

Represents a chunk together with its embedding vector.
"""

from dataclasses import dataclass

from src.models import Chunk


@dataclass(slots=True, frozen=True)
# Represents an embedded data chunk for storage.
class EmbeddedChunk:
    """
    Represents an embedded chunk.
    """

    chunk: Chunk

    embedding: list[float]