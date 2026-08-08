"""
Validation Layer — LLM-as-Judge.

Scores a generated answer on three dimensions:
  - Correctness   (0-10): Is the answer factually accurate given the context?
  - Completeness  (0-10): Does it fully address the question?
  - Citations     (bool): Are sources/references mentioned?

The weighted confidence score determines whether the Reflection Layer
should run another attempt.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from src.core.logging import LoggerManager
from src.llm import OllamaManager

logger = LoggerManager.get_logger()

# ---------------------------------------------------------------------------
# Judge prompt
# ---------------------------------------------------------------------------

_JUDGE_PROMPT = """You are a strict quality evaluator for an AI assistant.

Evaluate the answer below based on the query and the provided context (if any).
Respond ONLY with a valid JSON object — no extra text before or after.

Query: {query}

Context (document excerpts used to generate the answer — may be empty):
{context}

Answer to evaluate:
{answer}

Scoring criteria:
- correctness  : 0-10 — Is the answer factually accurate? (Use context if available)
- completeness : 0-10 — Does it fully address all parts of the query?
- has_citations: true/false — Does the answer reference source documents or sections?
- reasoning    : One sentence explaining the main weakness (if any)

Respond with ONLY this JSON (no markdown, no code block):
{{"correctness": <number>, "completeness": <number>, "has_citations": <true|false>, "reasoning": "<string>"}}"""


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
# Represents an LLM judgment evaluation outcome.
class ValidationResult:
    """Outcome of the LLM-as-judge evaluation."""

    confidence_score: float     # weighted 0-10
    correctness: float          # 0-10
    completeness: float         # 0-10
    has_citations: bool
    reasoning: str
    threshold: float = 5.5      # injected by ValidationLayer so passed() is accurate

    @property
    # Checks if confidence score meets or exceeds the configured threshold.
    def passed(self) -> bool:
        """True if the score meets the configured threshold."""
        return self.confidence_score >= self.threshold


# ---------------------------------------------------------------------------
# Validation Layer
# ---------------------------------------------------------------------------

# Scores an answer and returns validation results.
class ValidationLayer:
    """
    LLM-as-judge that scores an answer and returns a ValidationResult.
    """

    DEFAULT_THRESHOLD = 5.5

    # Sets up Ollama manager and scoring parameters.
    def __init__(
        self,
        ollama_manager: OllamaManager,
        model: str,
        threshold: float = DEFAULT_THRESHOLD,
        weights: dict | None = None,
    ) -> None:
        self.ollama_manager = ollama_manager
        self.model = model
        self.threshold = threshold
        self.weights = weights or {
            "correctness":  0.5,
            "completeness": 0.3,
            "citations":    0.2,
        }

    # Scores an answer using the LLM judge.
    def validate(
        self,
        query: str,
        answer: str,
        context: str = "",
    ) -> ValidationResult:
        """
        Score the answer using the LLM-as-judge.

        Parameters
        ----------
        query   : The original user question.
        answer  : The generated answer to evaluate.
        context : Document context used by the RAG tool (empty for LLM tools).

        Returns
        -------
        ValidationResult
        """

        logger.info("ValidationLayer: scoring answer…")

        prompt = _JUDGE_PROMPT.format(
            query=query,
            context=context or "(no document context — LLM answer)",
            answer=answer,
        )

        try:
            raw = self.ollama_manager.generate(
                model=self.model,
                prompt=prompt,
            )

            scores = self._parse_json(raw)

        except Exception as exc:
            logger.warning(
                f"ValidationLayer LLM call failed ({exc}). Using default scores."
            )
            scores = self._default_scores()

        correctness  = float(scores.get("correctness",  6.0))
        completeness = float(scores.get("completeness", 6.0))
        has_citations = bool(scores.get("has_citations", False))
        reasoning    = str(scores.get("reasoning", "Could not evaluate."))

        # Clamp to 0-10
        correctness  = max(0.0, min(10.0, correctness))
        completeness = max(0.0, min(10.0, completeness))

        citations_score = 10.0 if has_citations else 5.0

        confidence = (
            correctness  * self.weights["correctness"]
            + completeness * self.weights["completeness"]
            + citations_score * self.weights["citations"]
        )

        logger.info(
            f"ValidationLayer: score={confidence:.1f}/10 "
            f"(correctness={correctness}, completeness={completeness}, "
            f"citations={has_citations})"
        )

        return ValidationResult(
            confidence_score=round(confidence, 2),
            correctness=correctness,
            completeness=completeness,
            has_citations=has_citations,
            reasoning=reasoning,
            threshold=self.threshold,
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    # Parses JSON from LLM responses robustly.
    def _parse_json(self, raw: str) -> dict:
        """
        Robustly extract JSON from the LLM response.
        Handles markdown code fences, leading/trailing text.
        """

        # Try direct parse first
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            pass

        # Extract JSON object with regex
        match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        logger.warning(f"ValidationLayer: could not parse JSON from: {raw!r}")
        return self._default_scores()

    @staticmethod
    # Provides fallback scores for failed LLM judgments.
    def _default_scores() -> dict:
        """Fallback scores when the LLM judge fails."""
        return {
            "correctness":  6.0,
            "completeness": 6.0,
            "has_citations": False,
            "reasoning": "Evaluation unavailable — using default scores.",
        }
