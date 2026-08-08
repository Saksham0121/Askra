"""
Enterprise Guardrail.

Every query enters SAARTHI through this module.
"""

from __future__ import annotations

from .intent_classifier import IntentClassifier
from .models import GuardrailResult
from .models import QueryIntent


# Human-readable rejection messages keyed by intent
_BLOCK_REASONS: dict[QueryIntent, str] = {
    QueryIntent.JAILBREAK: (
        "This request appears to be a prompt-injection or jailbreak attempt "
        "(e.g. trying to override instructions, impersonate roles, or expose "
        "internal system data). SAARTHI cannot process it."
    ),
    QueryIntent.UNSAFE: (
        "This request was flagged as potentially harmful and cannot be processed."
    ),
    QueryIntent.EMPTY: "Please enter a question.",
}


# Validates user queries against predefined intents.
class Guardrail:

    # Initializes the intent classification object.
    def __init__(self):
        self._classifier = IntentClassifier()

    # Validates query intent and returns result.
    def validate(self, query: str) -> GuardrailResult:

        normalized = " ".join(query.split())

        intent = self._classifier.classify(normalized)

        if intent in _BLOCK_REASONS:
            return GuardrailResult(
                allowed=False,
                intent=intent,
                normalized_query=normalized if intent != QueryIntent.EMPTY else "",
                reason=_BLOCK_REASONS[intent],
            )

        return GuardrailResult(
            allowed=True,
            intent=intent,
            normalized_query=normalized,
            reason="Query accepted.",
        )