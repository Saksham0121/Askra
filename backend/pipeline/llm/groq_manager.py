"""
Groq LLM Manager.

Drop-in replacement for OllamaManager, using the Groq Python SDK.
Exposes the same interface:
  - generate(model, prompt) -> str
  - generate_stream(model, prompt) -> Iterator[str]
  - list_models() -> list[str]
"""

from __future__ import annotations

from typing import Iterator

from groq import Groq

from app.config import get_settings


_SUPPORTED_MODELS = [
    "llama-3.1-8b-instant",
    "llama-3.1-70b-versatile",
    "llama3-8b-8192",
    "llama3-70b-8192",
    "mixtral-8x7b-32768",
    "gemma-7b-it",
]


class GroqManager:
    """
    Groq API wrapper with the same interface as OllamaManager.

    Parameters
    ----------
    api_key : Groq API key. Defaults to env var GROQ_API_KEY.
    """

    def __init__(self, api_key: str | None = None) -> None:
        settings = get_settings()
        self._client = Groq(api_key=api_key or settings.groq_api_key)

    # ------------------------------------------------------------------
    # Public API (mirrors OllamaManager)
    # ------------------------------------------------------------------

    def generate(self, model: str, prompt: str, max_tokens: int = 2048) -> str:
        """
        Generate a completion synchronously.

        Parameters
        ----------
        model      : Groq model name.
        prompt     : User prompt text.
        max_tokens : Maximum response tokens.

        Returns
        -------
        str — The model's text response.
        """
        response = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        return response.choices[0].message.content or ""

    def generate_stream(
        self,
        model: str,
        prompt: str,
        max_tokens: int = 2048,
    ) -> Iterator[str]:
        """
        Generate a streaming completion, yielding text chunks.

        Parameters
        ----------
        model      : Groq model name.
        prompt     : User prompt text.
        max_tokens : Maximum response tokens.

        Yields
        ------
        str — Incremental text chunks.
        """
        stream = self._client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.1,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content

    def list_models(self) -> list[str]:
        """Return the list of supported Groq models."""
        return _SUPPORTED_MODELS
