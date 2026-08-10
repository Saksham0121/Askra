"""
QueryRewriter adapted for GroqManager.
"""
from __future__ import annotations
from dataclasses import dataclass
from pipeline.core.logging import LoggerManager
from pipeline.llm.groq_manager import GroqManager

logger = LoggerManager.get_logger()

_REWRITE_PROMPT = """\
You are a query-rewriting assistant for an enterprise document retrieval system.
Improve the following user question so it is clearer and more self-contained for semantic search.

{history_block}
Rules:
1. Expand vague pronouns or incomplete references into explicit descriptive phrases using the conversation history above.
2. Make the question fully self-contained — it should make sense without the conversation history.
3. Do NOT add new facts or scope the user did not imply.
4. If the question is already clear and specific, return it UNCHANGED.
5. Output ONLY the rewritten question — no explanation, no preamble.

Original question:
{query}

Rewritten question:"""


@dataclass(slots=True)
class QueryRewriteResult:
    original_query: str
    rewritten_query: str
    was_rewritten: bool


class QueryRewriter:
    def __init__(self, groq_manager: GroqManager, model: str) -> None:
        self._groq = groq_manager
        self._model = model

    def rewrite(self, query: str, history: list[dict] | None = None) -> QueryRewriteResult:
        try:
            # Build a compact history block for the prompt (last 4 turns)
            history_block = ""
            if history:
                turns = history[-8:]  # up to 4 user+assistant pairs
                lines = ["Recent conversation:"]
                for msg in turns:
                    role = "User" if msg["role"] == "user" else "Assistant"
                    lines.append(f"  {role}: {msg['content'][:300]}")
                history_block = "\n".join(lines) + "\n\n"

            prompt = _REWRITE_PROMPT.format(query=query, history_block=history_block)
            raw = self._groq.generate(model=self._model, prompt=prompt)
            rewritten = raw.strip()

            if not rewritten or len(rewritten) > 4 * len(query) + 200:
                return QueryRewriteResult(
                    original_query=query, rewritten_query=query, was_rewritten=False
                )

            was_rewritten = rewritten.lower() != query.lower()
            logger.info(f"QueryRewriter: was_rewritten={was_rewritten}")
            return QueryRewriteResult(
                original_query=query, rewritten_query=rewritten, was_rewritten=was_rewritten
            )
        except Exception as exc:
            logger.warning(f"QueryRewriter: LLM call failed ({exc!r}) — falling back.")
            return QueryRewriteResult(
                original_query=query, rewritten_query=query, was_rewritten=False
            )

