"""
Agent Router.

Two-stage hybrid routing:
  1. Fast rule-based stage — uses the IntentClassifier (same one the Guardrail
     uses) to map obvious intents to tools with zero LLM overhead.
  2. LLM fallback — called only for UNKNOWN intent (genuinely ambiguous queries).

Tool map:
  GREETING      → chat
  GENERAL_CHAT  → chat
  CODE          → code
  DOCUMENT      → rag
  UNKNOWN       → LLM decides (rag / chat / code)

This eliminates the Ollama round-trip for the vast majority of queries and
fixes misrouting (e.g. "tell me about indian cricket team" → chat, not rag).
"""

from __future__ import annotations

import re

from src.core.logging import LoggerManager
from src.llm import OllamaManager
from src.validation.intent_classifier import IntentClassifier
from src.validation.models import QueryIntent

logger = LoggerManager.get_logger()

# ---------------------------------------------------------------------------
# LLM prompt — only used for ambiguous / UNKNOWN queries
# ---------------------------------------------------------------------------

_ROUTING_PROMPT = """\
You are a query router for an enterprise document assistant.
Choose ONE tool to handle the user's query.

Tools:
- "rag"  : Questions about uploaded documents, internal policies, contracts,
           legal acts, reports, or any domain-specific private data.
- "chat" : General knowledge (history, sports, science, geography, news),
           greetings, or anything answerable without private documents.
- "code" : Programming, scripting, debugging, algorithms, or software questions.

Rules:
1. Reply with ONLY one word: rag, chat, or code — no punctuation, no explanation.
2. If the query mentions topics clearly unrelated to the user's documents
   (sports, general facts, public figures, current events), choose chat.

User query: {query}

Tool:"""

# ---------------------------------------------------------------------------
# Intent → tool mapping (rule-based, no LLM needed)
# ---------------------------------------------------------------------------

_INTENT_TO_TOOL: dict[QueryIntent, str] = {
    QueryIntent.GREETING:     "chat",
    QueryIntent.GENERAL_CHAT: "chat",
    QueryIntent.CODE:         "code",
    QueryIntent.DOCUMENT:     "rag",
    # EMPTY / UNSAFE / JAILBREAK are blocked by the Guardrail before reaching here.
    # UNKNOWN falls through to the LLM.
}


# Routes user queries to appropriate tools.
class AgentRouter:
    """
    Hybrid router: rule-based first, LLM fallback for ambiguous queries.
    """

    VALID_TOOLS = {"rag", "chat", "code"}

    # Sets up Ollama manager and intent classifier.
    def __init__(
        self,
        ollama_manager: OllamaManager,
        model: str,
    ) -> None:
        self.ollama_manager  = ollama_manager
        self.model           = model
        self._classifier     = IntentClassifier()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    # Determines the appropriate tool for a query.
    def route(self, query: str) -> str:
        """
        Return the tool name that should handle *query*.

        Tries rule-based routing first; falls back to an LLM call only
        when the intent is ambiguous (UNKNOWN).
        """

        # Stage 1 — fast, zero-LLM rule-based routing
        intent = self._classifier.classify(query)
        tool   = _INTENT_TO_TOOL.get(intent)

        if tool is not None:
            logger.info(
                f"AgentRouter (rule-based): '{tool}' for intent='{intent.value}' | {query!r}"
            )
            return tool

        # Stage 2 — LLM fallback for UNKNOWN intent
        logger.info(
            f"AgentRouter: intent='{intent.value}' is ambiguous, calling LLM for {query!r}"
        )
        return self._llm_route(query)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    # Resolves ambiguous routing using an LLM.
    def _llm_route(self, query: str) -> str:
        """Call the LLM to resolve ambiguous routing."""
        prompt = _ROUTING_PROMPT.format(query=query)

        try:
            response = self.ollama_manager.generate(
                model=self.model,
                prompt=prompt,
            )
            tool = self._parse_tool(response)
            logger.info(f"AgentRouter (LLM): '{tool}' for query: {query!r}")
            return tool

        except Exception as exc:
            logger.warning(
                f"AgentRouter LLM call failed ({exc}), defaulting to 'rag'."
            )
            return "rag"

    # Extracts a tool name from LLM response.
    def _parse_tool(self, raw: str) -> str:
        """
        Extract a valid tool name from the LLM response.
        Handles extra whitespace, punctuation, and casing.
        Prefers the first valid token found.
        """
        cleaned = raw.strip().lower()

        # Check in priority order to avoid accidental substring matches
        for tool in ("chat", "code", "rag"):
            if re.search(rf"\b{tool}\b", cleaned):
                return tool

        logger.warning(
            f"AgentRouter could not parse tool from: {raw!r}, defaulting to 'rag'."
        )
        return "rag"
