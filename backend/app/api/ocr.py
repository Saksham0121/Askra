"""
OCR API — POST /api/ocr/scan and GET /api/ocr/health.

Provides a direct REST endpoint for OCR scanning, separate from
the agentic chat flow. The frontend can use this to OCR files
without going through the chat interface.
"""

from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from app.auth.dependencies import get_current_user
from app.auth.models import UserInDB
from app.config import get_settings
from app.pipeline_bridge import get_pipeline_bridge

router = APIRouter(prefix="/api/ocr", tags=["ocr"])

# Supported file types for OCR
_OCR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".pdf"}


class OCRHealthResponse(BaseModel):
    available: bool
    server_url: str


class OCRScanResponse(BaseModel):
    filename: str
    pages: int
    text: str
    scan_time_ms: int


@router.get("/health", response_model=OCRHealthResponse)
async def ocr_health(current_user: UserInDB = Depends(get_current_user)):
    """Check whether the OCR server is reachable."""
    settings = get_settings()
    bridge = get_pipeline_bridge()

    available = False
    if bridge.ocr_service is not None:
        available = bridge.ocr_service.is_available()

    return OCRHealthResponse(
        available=available,
        server_url=settings.ocr_server_url,
    )


@router.post("/scan", response_model=OCRScanResponse, status_code=200)
async def ocr_scan(
    file: UploadFile = File(...),
    current_user: UserInDB = Depends(get_current_user),
):
    """
    Upload an image or PDF and receive the OCR-extracted text.

    The file is temporarily saved to the uploads directory, scanned,
    and the extracted text is returned.
    """
    import time

    filename = file.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in _OCR_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported for OCR. "
                   f"Supported: {', '.join(sorted(_OCR_EXTENSIONS))}",
        )

    settings = get_settings()
    if not settings.ocr_enabled:
        raise HTTPException(
            status_code=503,
            detail="OCR is disabled. Set OCR_ENABLED=true in your .env to enable it.",
        )

    bridge = get_pipeline_bridge()
    if bridge.ocr_service is None:
        raise HTTPException(
            status_code=503,
            detail="OCR service is not initialized.",
        )

    if not bridge.ocr_service.is_available():
        raise HTTPException(
            status_code=503,
            detail="OCR server is not reachable. Please start the SGLang server.",
        )

    # Save uploaded file temporarily
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        start = time.perf_counter()

        if ext == ".pdf":
            results = bridge.ocr_service.ocr_pdf(str(dest))
            text = "\n\n---\n\n".join(
                f"## Page {r['page']}\n\n{r['text']}" for r in results if r["text"]
            )
            page_count = len(results)
        else:
            text = bridge.ocr_service.ocr_image(str(dest))
            page_count = 1

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        return OCRScanResponse(
            filename=filename,
            pages=page_count,
            text=text,
            scan_time_ms=elapsed_ms,
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"OCR scanning failed: {exc}",
        )
