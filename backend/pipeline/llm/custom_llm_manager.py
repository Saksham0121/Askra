"""
Custom LLM Manager.

Drop-in replacement for CustomLLMManager, targeting any OpenAI-compatible
/v1/chat/completions endpoint (e.g. a self-hosted vLLM / llama.cpp server).

Exposes the same interface:
  - generate(model, prompt) -> str
  - generate_stream(model, prompt) -> Iterator[str]
  - list_models() -> list[str]
"""

from __future__ import annotations

from typing import Iterator

from openai import OpenAI


class CustomLLMManager:
    """
    Wrapper around any OpenAI-compatible chat completions endpoint.

    Parameters
    ----------
    base_url : Base URL of the API server, e.g. "https://llm.saranshh.me/v1".
               Defaults to the LLM_BASE_URL env var.
    api_key  : Bearer token. Defaults to LLM_API_KEY env var.
               Set to a dummy value if the server doesn't require auth.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        from app.config import get_settings  # lazy import to avoid circular dependency
        settings = get_settings()
        self._client = OpenAI(
            base_url=base_url or settings.llm_base_url,
            api_key=api_key or settings.llm_api_key,
        )

    # ------------------------------------------------------------------
    # Public API (mirrors CustomLLMManager / OllamaManager)
    # ------------------------------------------------------------------

    def generate(self, model: str, prompt: str, max_tokens: int = 2048) -> str:
        """
        Generate a completion synchronously.

        Parameters
        ----------
        model      : Model name as expected by the remote server (e.g. "gemma").
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
        model      : Model name as expected by the remote server.
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
        """Return the list of models available on the remote server."""
        try:
            models = self._client.models.list()
            return [m.id for m in models.data]
        except Exception:
            # Fallback: return the configured default model name
            from app.config import get_settings  # lazy import
            settings = get_settings()
            return [settings.llm_chat_model]
