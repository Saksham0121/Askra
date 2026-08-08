"""
Validation models for SAARTHI.

This module contains shared enums and dataclasses used by the
validation layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


# Defines supported query intents for the system.
class QueryIntent(str, Enum):
    """Supported query intents."""

    EMPTY = "empty"

    GREETING = "greeting"

    DOCUMENT = "document"

    GENERAL_CHAT = "general_chat"

    CODE = "code"

    UNSAFE = "unsafe"

    JAILBREAK = "jailbreak"

    UNKNOWN = "unknown"


@dataclass(slots=True)
# Represents Guardrail query result details.
class GuardrailResult:
    """
    Output returned by the Guardrail.
    """

    allowed: bool

    intent: QueryIntent

    normalized_query: str

    reason: str