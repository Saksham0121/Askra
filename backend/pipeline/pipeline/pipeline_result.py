"""
Pipeline Result.

Unified result dataclass returned by both the direct RAG path
and the full agentic pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Answer source constants
# ---------------------------------------------------------------------------

# Defines different answer source types and strategies.
class AnswerSource:
    RAG        = "rag"           # grounded in indexed documents
    LLM        = "llm"           # chat tool / LLM own knowledge
    CODE       = "code"          # code tool / LLM own knowledge
    RAG_FALLBACK = "rag_fallback"  # RAG tried but fell back to LLM
    OCR          = "ocr"            # OCR scan of image/PDF


# ---------------------------------------------------------------------------
# Confidence helpers
# ---------------------------------------------------------------------------

# Maps score to human-readable confidence labels.
def confidence_label(score: float) -> str:
    """Map a 0-10 score to a human-readable label."""
    if score >= 7.5:
        return "High"
    if score >= 5.0:
        return "Medium"
    return "Low"


# Generates confidence badge with emoji and score.
def confidence_badge(score: float) -> str:
    """Return an emoji badge + label + numeric for display."""
    label = confidence_label(score)
    icon  = {"High": "🟢", "Medium": "🟡", "Low": "🔴"}[label]
    return f"{icon} {label} ({score:.1f}/10)"


# Generates user-friendly labels for answer sources.
def answer_source_label(source: str) -> str:
    """Return a human-readable UI label for the answer source."""
    return {
        AnswerSource.RAG:          "📄 Grounded in your documents",
        AnswerSource.LLM:          "🤖 LLM answer (own knowledge)",
        AnswerSource.CODE:         "💻 Code answer (own knowledge)",
        AnswerSource.RAG_FALLBACK: "⚠️ RAG fallback — LLM answered from general knowledge",
        AnswerSource.OCR:          "🔍 OCR scan (Unlimited-OCR)",
    }.get(source, "❓ Unknown source")


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
# Represents a pipelines result with associated data.
class PipelineResult:
    """
    Unified result returned to the backend / UI.
    """

    answer: str

    sources: list[str] = field(default_factory=list)

    confidence_score: float = 0.0

    answer_source: str = AnswerSource.RAG

    validation_reasoning: str = ""

    iterations: int = 1          # how many reflection loops ran

    latency_ms: int = 0

    @property
    # Generates a confidence badge string value.
    def confidence_badge(self) -> str:
        return confidence_badge(self.confidence_score)

    @property
    # Returns the source label string.
    def answer_source_label(self) -> str:
        return answer_source_label(self.answer_source)
