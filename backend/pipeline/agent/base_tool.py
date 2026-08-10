"""
Base Tool Interface.

All agent tools (Chat, Code, RAG) implement this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
# Represents results from various tools/processes.
class ToolResult:
    """
    Standardised output from any tool.
    """

    answer: str

    # "rag" | "llm" | "code" | "rag_fallback"
    answer_source: str

    # Source document filenames (empty for non-RAG tools)
    sources: list[str] = field(default_factory=list)

    # Raw context string passed to the LLM (empty for non-RAG tools)
    context: str = ""


# Abstract base class for agent tool functionality
class BaseTool(ABC):
    """
    Abstract base class for all agent tools.
    """

    @property
    @abstractmethod
    # Identifies the tool or component name.
    def name(self) -> str:
        """Short tool identifier, e.g. 'chat', 'code', 'rag'."""

    @abstractmethod
    # Executes the tool with the provided query.
    def execute(self, query: str) -> ToolResult:
        """
        Execute the tool for the given query synchronously.
        """

    @abstractmethod
    # Executes the tool and streams output events.
    def execute_stream(self, query: str, history: list[dict] | None = None):
        """
        Execute the tool for the given query and stream the output.
        
        Yields
        ------
        dict
            Event objects:
            - {"type": "status", "message": str}
            - {"type": "chunk", "content": str}
            - {"type": "result", "data": ToolResult}
        """

