"""
Lightweight rule-based intent classifier.

Designed to be replaceable by an LLM classifier
without changing the Guardrail API.

Jailbreak / prompt-injection detection is multi-layered:
  1. High-confidence exact/partial phrase blocklist
  2. Regex patterns for known attack structures
  3. Heuristic scoring — multiple weak signals accumulate
     into a block when their combined score exceeds the threshold
"""

from __future__ import annotations

import re

from .models import QueryIntent


# ---------------------------------------------------------------------------
# Heuristic signal weights
# Each signal contributes a score; HEURISTIC_THRESHOLD triggers a block.
# ---------------------------------------------------------------------------

HEURISTIC_THRESHOLD = 2.5

_HEURISTIC_SIGNALS: list[tuple[str, float]] = [
    # Instruction-override language
    (r"ignore\s+(all\s+)?(previous|prior|earlier|your|the)?\s*(instructions?|rules?|prompts?|context|guidelines?|constraints?)", 2.0),
    (r"disregard\s+(all\s+)?(previous|prior|earlier|your|the)?\s*(instructions?|rules?|prompts?|context)", 2.0),
    (r"forget\s+(everything|all|previous|your)\s*(instructions?|rules?|prompts?|context|you\s+were\s+told)?", 2.0),
    (r"override\s+(your\s+)?(instructions?|rules?|settings?|guidelines?|restrictions?)", 2.0),

    # Role / persona hijacking
    (r"\bact\s+as\s+(if\s+you\s+are|a|an|the)\b", 1.5),
    (r"\bpretend\s+(you\s+are|to\s+be|you're)\b", 1.5),
    (r"\byou\s+are\s+now\s+(a|an|the)\b", 1.5),
    (r"\bbecome\s+(a|an|the)\s+\w+\s*(bot|ai|assistant|model|system)\b", 1.5),
    (r"\bswitch\s+(to\s+)?(developer|admin|god|unrestricted|jailbreak)\s*mode\b", 2.0),
    (r"\benter\s+(developer|admin|god|unrestricted|jailbreak|safe)?\s*mode\b", 1.5),

    # System/internal access probing
    (r"\bsystem\s*(prompt|message|instruction|context)\b", 1.5),
    (r"\bdeveloper\s*(message|mode|prompt|instruction)\b", 1.5),
    (r"\binternal\s*(prompt|instruction|context|chain.of.thought)\b", 2.0),
    (r"\bhidden\s*(prompt|instruction|context|chain.of.thought)\b", 2.0),
    (r"\bchain.of.thought\b", 1.5),
    (r"\breveal\s+(your|the|all|my|our)?\s*(instructions?|prompt|context|rules?|configuration|settings?)\b", 2.0),
    (r"\bprint\s+(your|the)?\s*(instructions?|prompt|context|system\s*prompt)\b", 2.0),
    (r"\bshow\s+(me\s+)?(your|the)?\s*(instructions?|prompt|system|context|rules?)\b", 1.5),
    (r"\btell\s+me\s+(your|the)?\s*(instructions?|prompt|system\s+prompt|hidden)\b", 1.5),
    (r"\bwhat\s+(are\s+your|is\s+your)\s*(instructions?|prompt|guidelines?|rules?|system\s+prompt)\b", 1.5),

    # Data exfiltration / memory dumping
    (r"\b(dump|export|extract|leak|exfiltrate)\s+(all\s+)?(chunk|embed|vector|faiss|memory|data|index|database)\b", 2.0),
    (r"\braw\s+(faiss|index|vector|embed|chunk|database)\b", 2.0),
    (r"\bvector\s*(database|store|index|content|data)\b", 1.5),
    (r"\b(show|print|return|give|list|display)\s+(me\s+)?(all\s+)?(chunk|embed|vector|faiss|index|memory|stored|raw)\b", 1.5),
    (r"\bfaiss\s*(index|store|dump|content)\b", 2.0),
    (r"\bembedding(s)?\s*(used|stored|in|from|of)\b", 1.5),
    (r"\bstored\s+in\s+memory\b", 1.5),

    # Safety/restriction bypass
    (r"\b(disable|remove|turn\s+off|bypass|circumvent|ignore)\s+(all\s+)?(safety|guardrail|filter|restriction|check|rule|limit)\b", 2.0),
    (r"\bwithout\s+(any\s+)?(safety|restriction|filter|limit|guardrail)\b", 1.5),
    (r"\banswer\s+freely\b", 1.5),
    (r"\bno\s+restrictions?\b", 1.5),
    (r"\bunrestricted\b", 1.0),
    (r"\bjailbreak\b", 2.0),
    (r"\bdan\b", 1.0),  # "Do Anything Now" jailbreak persona

    # Access escalation
    (r"\b(give|grant|provide)\s+(me\s+)?(administrator|admin|root|full|super)\s*(access|privileges?|rights?|permission)\b", 2.0),
    (r"\badmin(istrator)?\s+(access|mode|rights?|privileges?)\b", 1.5),

    # "Ignore documents" override
    (r"\bignore\s+(the\s+)?(uploaded|indexed|your|the)?\s*(document|pdf|file|context|chunk)\b", 2.0),
    (r"\bdon.t\s+use\s+(the\s+)?(document|pdf|file|context|chunk)\b", 1.5),
    (r"\banswer\s+from\s+(your\s+)?(own\s+)?(knowledge|training|memory|mind)\b", 1.5),
    (r"\buse\s+your\s+(own\s+)?(knowledge|training|memory)\b", 1.0),
    (r"\bwithout\s+(using\s+)?(the\s+)?(document|pdf|file|context|chunk)\b", 1.0),

    # Prompt delimiters / injection framing
    (r"[<\[{]\s*(system|instruction|prompt|context|human|assistant)\s*[>\]}]", 2.0),
    (r"###\s*(instruction|system|prompt)", 1.5),
    (r"```\s*(system|prompt|instruction)", 1.5),

    # Credential / key exfiltration
    (r"\b(api\s*key|secret\s*key|password|credential|token)\s*(reveal|show|print|dump|leak|expose)\b", 2.0),
    (r"\b(reveal|show|print|leak|expose)\s+(the\s+)?(api\s*key|secret|password|token|credential)\b", 2.0),
]


# Defines keyword sets for intent recognition.
class IntentClassifier:

    # -----------------------------------------------------------------------
    # Legitimate-query keyword sets
    # -----------------------------------------------------------------------

    GREETINGS = {
        "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    }

    DOCUMENT_KEYWORDS = {
        "document", "pdf", "uploaded", "clause", "section",
        "policy", "act", "agreement", "contract",
    }

    CODE_KEYWORDS = {
        "python", "java", "javascript", "typescript", "c++", "c#", "golang", "rust",
        "sql", "html", "css", "react", "nodejs", "django", "flask",
        "code", "function", "bug", "error", "exception", "class", "algorithm",
        "leetcode", "debug", "compile", "runtime", "syntax", "library",
        "framework", "script", "api", "endpoint", "recursion", "loop",
        "variable", "object", "array", "string", "integer", "null", "pointer",
    }

    OCR_KEYWORDS = {
        "scan", "ocr", "extract text from image", "read this image",
        "parse this image", "scan this document", "scan this pdf",
        "scan the document", "scan the pdf", "scan the image",
        "image to text", "scanned", "handwritten",
    }

    # -----------------------------------------------------------------------
    # Hard-block phrase list (instant JAILBREAK, no scoring)
    # -----------------------------------------------------------------------

    _HARD_BLOCK_PHRASES: tuple[str, ...] = (
        # Instruction overrides — with or without "all"
        "ignore all previous",
        "ignore all instructions",
        "ignore previous instructions",
        "ignore your instructions",
        "ignore these instructions",
        "ignore prior instructions",
        "ignore the instructions",
        "forget your instructions",
        "disregard your instructions",
        # Role hijacking
        "you are now an",
        "you are now a",
        "pretend you are not an ai",
        "pretend to be",
        "you have no restrictions",
        # System prompt probing
        "your internal prompt",
        "internal prompt",
        "reveal your system prompt",
        "reveal your hidden",
        "print your prompt",
        "show me your prompt",
        "show me your system",
        "tell me your prompt",
        "tell me your system prompt",
        "your hidden system",
        "your system prompt",
        # Data exfiltration
        "dump every chunk",
        "show me the vector",
        "vector database contents",
        "return the raw faiss",
        "raw faiss index",
        "the raw faiss",
        # Embedding / index probing
        "reveal the embeddings",
        "embeddings used to index",
        "show me the embeddings",
        # Safety bypass
        "disable all safety",
        "bypass all safety",
        "answer freely",
        "no restrictions",
        "jailbreak",
        "do anything now",
        "developer mode",
        "god mode",
        # Admin access
        "grant me admin",
        "give me administrator",
        "administrator access",
        # Document override
        "ignore the uploaded documents",
        "ignore the uploaded",
        "ignore your documents",
        "answer from your own knowledge",
        "from your own knowledge",
    )

    # -----------------------------------------------------------------------
    # Unsafe-content patterns (instant UNSAFE)
    # -----------------------------------------------------------------------

    UNSAFE_PATTERNS: tuple[str, ...] = (
        r"build\s+a\s+bomb",
        r"make\s+(an?\s+)?explosive",
        r"synthesise\s+drugs?",
        r"breach\s+.*data",
        r"steal\s+password",
        r"\bmalware\b",
        r"\bransomware\b",
        r"\bphishing\b",
        r"create\s+a\s+virus",
    )

    # -----------------------------------------------------------------------
    # Classifier entry point
    # -----------------------------------------------------------------------

    # Classifies user queries for potential risks.
    def classify(self, query: str) -> QueryIntent:
        q = query.lower()

        if not q.strip():
            return QueryIntent.EMPTY

        # 1 — Hard-block phrase check (fastest, no regex)
        for phrase in self._HARD_BLOCK_PHRASES:
            if phrase in q:
                return QueryIntent.JAILBREAK

        # 2 — Heuristic scoring: accumulate signal weights
        score = 0.0
        for pattern, weight in _HEURISTIC_SIGNALS:
            if re.search(pattern, q):
                score += weight
                if score >= HEURISTIC_THRESHOLD:
                    return QueryIntent.JAILBREAK

        # 3 — Unsafe content
        for pattern in self.UNSAFE_PATTERNS:
            if re.search(pattern, q):
                return QueryIntent.UNSAFE

        # 4 — Legitimate intent classification (word-boundary matching prevents
        #     false positives like "act" inside "react" or "class" inside "classify")
        def _has_word(keywords: set) -> bool:
            return any(
                re.search(r"\b" + re.escape(w) + r"s?\b", q)
                for w in keywords
            )

        if _has_word(self.GREETINGS):
            return QueryIntent.GREETING

        # OCR detection — check before CODE/DOCUMENT to avoid false matches
        if _has_word(self.OCR_KEYWORDS):
            return QueryIntent.OCR_SCAN

        # CODE before DOCUMENT: avoids "act" in "react" triggering DOCUMENT
        if _has_word(self.CODE_KEYWORDS):
            return QueryIntent.CODE

        if _has_word(self.DOCUMENT_KEYWORDS):
            return QueryIntent.DOCUMENT

        return QueryIntent.GENERAL_CHAT