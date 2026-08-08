"""
Agent Router adapted for GroqManager.
"""
from __future__ import annotations
import re
from pipeline.core.logging import LoggerManager
from pipeline.llm.groq_manager import GroqManager
from pipeline.validation.intent_classifier import IntentClassifier
from pipeline.validation.models import QueryIntent

logger = LoggerManager.get_logger()

_ROUTING_PROMPT = """\
You are a query router for an enterprise document assistant.
Choose ONE tool to handle the user's query.

Tools:
- "rag"  : Questions about uploaded documents, internal policies, contracts, legal acts, reports, or domain-specific private data.
- "chat" : General knowledge (history, sports, science, geography, news), greetings, or anything answerable without private documents.
- "code" : Programming, scripting, debugging, algorithms, or software questions.

Rules:
1. Reply with ONLY one word: rag, chat, or code — no punctuation, no explanation.
2. If the query mentions topics clearly unrelated to documents (sports, general facts, public figures), choose chat.

User query: {query}

Tool:"""

_INTENT_TO_TOOL: dict[QueryIntent, str] = {
    QueryIntent.GREETING: "chat",
    QueryIntent.GENERAL_CHAT: "chat",
    QueryIntent.CODE: "code",
    QueryIntent.DOCUMENT: "rag",
}


class AgentRouter:
    """Hybrid router: rule-based first, Groq LLM fallback for ambiguous queries."""

    VALID_TOOLS = {"rag", "chat", "code"}

    def __init__(self, groq_manager: GroqManager, model: str) -> None:
        self.groq_manager = groq_manager
        self.model = model
        self._classifier = IntentClassifier()

    def route(self, query: str) -> str:
        intent = self._classifier.classify(query)
        tool = _INTENT_TO_TOOL.get(intent)
        if tool is not None:
            logger.info(f"AgentRouter (rule-based): '{tool}' for intent='{intent.value}'")
            return tool
        logger.info(f"AgentRouter: intent='{intent.value}' is ambiguous, calling Groq LLM")
        return self._llm_route(query)

    def _llm_route(self, query: str) -> str:
        prompt = _ROUTING_PROMPT.format(query=query)
        try:
            response = self.groq_manager.generate(model=self.model, prompt=prompt)
            tool = self._parse_tool(response)
            logger.info(f"AgentRouter (LLM): '{tool}' for query: {query!r}")
            return tool
        except Exception as exc:
            logger.warning(f"AgentRouter LLM call failed ({exc}), defaulting to 'rag'.")
            return "rag"

    def _parse_tool(self, raw: str) -> str:
        cleaned = raw.strip().lower()
        for tool in ("chat", "code", "rag"):
            if re.search(rf"\b{tool}\b", cleaned):
                return tool
        logger.warning(f"AgentRouter could not parse tool from: {raw!r}, defaulting to 'rag'.")
        return "rag"
