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

Rules:
1. Expand vague pronouns or incomplete references into explicit descriptive phrases.
2. Make the question fully self-contained.
3. Do NOT add new facts or scope the user did not imply.
4. If already clear and specific, return it UNCHANGED.
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

    def rewrite(self, query: str) -> QueryRewriteResult:
        try:
            prompt = _REWRITE_PROMPT.format(query=query)
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
