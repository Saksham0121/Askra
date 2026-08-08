"""
Query Rewriter.

Rewrites naive or vague user queries into cleaner, retrieval-optimised
forms so that downstream vector search and BM25 retrieval can surface
more relevant chunks.

Position in the pipeline
------------------------
  Guardrail → **Query Rewriter** → Direct RAG toggle → ...

The rewriter is called only after the guardrail has already approved the
query.  Blocked queries never reach this module.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.core.logging import LoggerManager
from src.llm import OllamaManager

logger = LoggerManager.get_logger()

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_REWRITE_PROMPT = """\
You are a query-rewriting assistant for a legal document retrieval system.
Your task is to improve the following user question so it is clearer and
more self-contained for semantic search — without changing its meaning or
adding information that isn't implied.

Rules:
1. Expand vague pronouns or incomplete references (e.g. "it", "that clause",
   "the above section") into explicit, descriptive phrases.
2. Make the question fully self-contained so a retrieval engine can match
   it to the right document sections even without prior conversation context.
3. Do NOT add new facts, topics, or scope that the user did not imply.
4. If the question is already clear and specific, return it UNCHANGED.
5. Output ONLY the rewritten question — no explanation, no preamble,
   no bullet points, no quotes.

Original question:
{query}

Rewritten question:"""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass(slots=True)
# Holds the result of a query rewrite operation.
class QueryRewriteResult:
    """
    Output returned by QueryRewriter.rewrite().
    """

    original_query: str
    rewritten_query: str
    was_rewritten: bool


# ---------------------------------------------------------------------------
# Rewriter class
# ---------------------------------------------------------------------------


# Rewrites naive user queries into retrieval-optimised forms.
class QueryRewriter:
    """
    Rewrites naive or vague user queries using an Ollama LLM.

    Falls back to the original query transparently on any error so the
    pipeline is never disrupted.
    """

    # Initializes the rewriter with an Ollama model.
    def __init__(
        self,
        ollama_manager: OllamaManager,
        model: str,
    ) -> None:
        self._ollama = ollama_manager
        self._model = model

    # Rewrites the query and returns a QueryRewriteResult.
    def rewrite(self, query: str) -> QueryRewriteResult:
        """
        Attempt to rewrite *query* into a cleaner retrieval form.

        Parameters
        ----------
        query:
            The normalized query string produced by the Guardrail.

        Returns
        -------
        QueryRewriteResult
            Always returns a valid result.  If the LLM call fails or
            returns an empty string, ``rewritten_query`` equals
            ``original_query`` and ``was_rewritten`` is ``False``.
        """

        try:
            prompt = _REWRITE_PROMPT.format(query=query)
            raw: str = self._ollama.generate(model=self._model, prompt=prompt)
            rewritten = raw.strip()

            # Guard: reject empty or suspiciously long rewrites
            if not rewritten or len(rewritten) > 4 * len(query) + 200:
                logger.debug(
                    "QueryRewriter: rewrite rejected (empty or too long) "
                    "— falling back to original."
                )
                return QueryRewriteResult(
                    original_query=query,
                    rewritten_query=query,
                    was_rewritten=False,
                )

            was_rewritten = rewritten.lower() != query.lower()

            logger.info(
                f"QueryRewriter: was_rewritten={was_rewritten} | "
                f"original={query!r} | rewritten={rewritten!r}"
            )

            return QueryRewriteResult(
                original_query=query,
                rewritten_query=rewritten,
                was_rewritten=was_rewritten,
            )

        except Exception as exc:
            logger.warning(
                f"QueryRewriter: LLM call failed ({exc!r}) "
                "— falling back to original query."
            )
            return QueryRewriteResult(
                original_query=query,
                rewritten_query=query,
                was_rewritten=False,
            )
