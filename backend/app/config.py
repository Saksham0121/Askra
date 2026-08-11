"""
Askrab Application Settings.

Loads all configuration from environment variables / .env file.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central settings object — loaded once and cached."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM (Groq) ─────────────────────────────────────────────────────
    groq_api_key: str = ""
    groq_chat_model: str = "llama-3.1-8b-instant"
    groq_code_model: str = "llama-3.1-8b-instant"
    groq_router_model: str = "llama-3.1-8b-instant"
    groq_rewriter_model: str = "llama-3.1-8b-instant"

    # ── MongoDB ─────────────────────────────────────────────────────────
    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db_name: str = "askrab"

    # ── JWT Auth ────────────────────────────────────────────────────────
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # ── App ─────────────────────────────────────────────────────────────
    app_env: str = "development"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # ── File Storage ────────────────────────────────────────────────────
    upload_dir: str = "./uploads"
    faiss_index_dir: str = "./faiss_store"

    # ── Pipeline Thresholds ─────────────────────────────────────────────
    hallucination_threshold: float = 0.3
    confidence_threshold: float = 5.5

    # ── OCR (Unlimited-OCR via SGLang) ─────────────────────────────────
    ocr_server_url: str = "http://127.0.0.1:10000"
    ocr_enabled: bool = True

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached Settings singleton."""
    return Settings()
