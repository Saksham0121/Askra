"""
ValidationLayer and QueryRewriter adapted for GroqManager.
"""
from __future__ import annotations
import json
import re
from dataclasses import dataclass
from pipeline.core.logging import LoggerManager
from pipeline.llm.groq_manager import GroqManager

logger = LoggerManager.get_logger()

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


@dataclass
class ValidationResult:
    confidence_score: float
    correctness: float
    completeness: float
    has_citations: bool
    reasoning: str
    threshold: float = 5.5

    @property
    def passed(self) -> bool:
        return self.confidence_score >= self.threshold


class ValidationLayer:
    DEFAULT_THRESHOLD = 5.5

    def __init__(
        self,
        groq_manager: GroqManager,
        model: str,
        threshold: float = DEFAULT_THRESHOLD,
        weights: dict | None = None,
    ) -> None:
        self.groq_manager = groq_manager
        self.model = model
        self.threshold = threshold
        self.weights = weights or {"correctness": 0.5, "completeness": 0.3, "citations": 0.2}

    def validate(self, query: str, answer: str, context: str = "") -> ValidationResult:
        logger.info("ValidationLayer: scoring answer...")
        prompt = _JUDGE_PROMPT.format(
            query=query,
            context=context or "(no document context — LLM answer)",
            answer=answer,
        )
        try:
            raw = self.groq_manager.generate(model=self.model, prompt=prompt)
            scores = self._parse_json(raw)
        except Exception as exc:
            logger.warning(f"ValidationLayer LLM call failed ({exc}). Using default scores.")
            scores = self._default_scores()

        correctness = max(0.0, min(10.0, float(scores.get("correctness", 6.0))))
        completeness = max(0.0, min(10.0, float(scores.get("completeness", 6.0))))
        has_citations = bool(scores.get("has_citations", False))
        reasoning = str(scores.get("reasoning", "Could not evaluate."))
        citations_score = 10.0 if has_citations else 5.0

        confidence = (
            correctness * self.weights["correctness"]
            + completeness * self.weights["completeness"]
            + citations_score * self.weights["citations"]
        )

        logger.info(f"ValidationLayer: score={confidence:.1f}/10")
        return ValidationResult(
            confidence_score=round(confidence, 2),
            correctness=correctness,
            completeness=completeness,
            has_citations=has_citations,
            reasoning=reasoning,
            threshold=self.threshold,
        )

    def _parse_json(self, raw: str) -> dict:
        try:
            return json.loads(raw.strip())
        except json.JSONDecodeError:
            pass
        match = re.search(r"\{[^{}]+\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        logger.warning(f"ValidationLayer: could not parse JSON from: {raw!r}")
        return self._default_scores()

    @staticmethod
    def _default_scores() -> dict:
        return {
            "correctness": 6.0,
            "completeness": 6.0,
            "has_citations": False,
            "reasoning": "Evaluation unavailable — using default scores.",
        }
