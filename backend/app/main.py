"""
Askrab — FastAPI Application Entry Point.
"""
from __future__ import annotations
import logging
import re
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import close_connection
from app.pipeline_bridge import get_pipeline_bridge
from app.auth.router import router as auth_router
from app.api.chat import router as chat_router
from app.api.documents import router as documents_router
from app.api.analytics import router as analytics_router
from app.api.admin import router as admin_router
from app.api.ocr import router as ocr_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("askrab")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("Askrab starting up...")
    settings = get_settings()
    logger.info(f"Environment: {settings.app_env}")

    # Warm up the pipeline (loads embedding model, FAISS index, Groq client)
    try:
        get_pipeline_bridge()
        logger.info("Pipeline bridge initialized successfully.")
    except Exception as exc:
        logger.error(f"Pipeline bridge initialization failed: {exc}")

    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("Askrab shutting down...")
    await close_connection()


settings = get_settings()

app = FastAPI(
    title="Askrab API",
    description="Intelligent Agentic RAG System — 7-Layer Pipeline",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def path_sanitization_middleware(request: Request, call_next):
    raw_path = request.scope.get("path", "")
    if "//" in raw_path:
        normalized_path = "/" + "/".join(segment for segment in raw_path.split("/") if segment)
        request.scope["path"] = normalized_path
    return await call_next(request)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(documents_router)
app.include_router(analytics_router)
app.include_router(admin_router)
app.include_router(ocr_router)


@app.get("/", tags=["health"])
@app.head("/", tags=["health"])
async def root():
    return {
        "name": "Askrab API",
        "version": "1.0.0",
        "status": "running",
        "pipeline": "7-layer agentic RAG",
    }


@app.get("/health", tags=["health"])
@app.head("/health", tags=["health"])
async def health():
    return {"status": "ok"}
