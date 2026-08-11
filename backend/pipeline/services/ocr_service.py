"""
OCR Service.

Wraps the Unlimited-OCR SGLang client to provide image and PDF OCR
capabilities. Connects to an external SGLang server running the
baidu/Unlimited-OCR model.

The service is a pure client — it does NOT start or manage the SGLang
server process. The server must be running externally.
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from pipeline.core.logging import LoggerManager

logger = LoggerManager.get_logger()

# ---------------------------------------------------------------------------
# Defaults (mirrors OCR_tool/infer.py)
# ---------------------------------------------------------------------------

_MODEL_NAME = "Unlimited-OCR"
_PROMPT = "document parsing."
_TEMPERATURE = 0
_REQUEST_TIMEOUT = 1200
_MAX_RETRIES = 3
_PDF_DPI = 300


class OCRService:
    """
    Client for the Unlimited-OCR SGLang inference server.

    Parameters
    ----------
    server_url : Base URL of the SGLang server (e.g. http://127.0.0.1:10000).
    """

    def __init__(self, server_url: str = "http://127.0.0.1:10000") -> None:
        self.server_url = server_url.rstrip("/")

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the SGLang OCR server is reachable and healthy."""
        try:
            resp = requests.get(f"{self.server_url}/health", timeout=5)
            return resp.status_code == 200
        except requests.RequestException:
            return False

    # ------------------------------------------------------------------
    # Single-image OCR
    # ------------------------------------------------------------------

    def ocr_image(self, image_path: str, image_mode: str = "gundam") -> str:
        """
        OCR a single image and return the extracted markdown text.

        Parameters
        ----------
        image_path  : Absolute path to the image file.
        image_mode  : "gundam" (crop, faster) or "base" (full, for multi-page).

        Returns
        -------
        str — Extracted text in markdown format.
        """
        content = self._build_content(image_path)
        payload = self._build_payload(content, image_mode)

        for attempt in range(_MAX_RETRIES):
            try:
                resp = requests.post(
                    f"{self.server_url}/v1/chat/completions",
                    headers={"Content-Type": "application/json"},
                    data=json.dumps(payload),
                    timeout=_REQUEST_TIMEOUT,
                    stream=True,
                )
                if resp.status_code == 502 and attempt < _MAX_RETRIES - 1:
                    time.sleep(3 * (attempt + 1))
                    continue
                resp.raise_for_status()
                result = self._collect_stream(resp)
                logger.info(
                    f"OCR completed for {os.path.basename(image_path)}: "
                    f"{result['tokens']} tokens, {result['decode_time']:.1f}s"
                )
                return result["text"]
            except Exception as e:
                if attempt < _MAX_RETRIES - 1:
                    logger.warning(
                        f"OCR retry {attempt + 1}/{_MAX_RETRIES} for "
                        f"{os.path.basename(image_path)}: {e}"
                    )
                    time.sleep(3 * (attempt + 1))
                    continue
                logger.error(f"OCR failed for {os.path.basename(image_path)}: {e}")
                raise

    # ------------------------------------------------------------------
    # PDF OCR (multi-page)
    # ------------------------------------------------------------------

    def ocr_pdf(
        self,
        pdf_path: str,
        dpi: int = _PDF_DPI,
        concurrency: int = 4,
    ) -> list[dict]:
        """
        Convert each PDF page to an image and OCR it.

        Parameters
        ----------
        pdf_path    : Path to the PDF file.
        dpi         : Resolution for PDF→image conversion.
        concurrency : Number of pages to OCR in parallel.

        Returns
        -------
        list[dict] — Sorted list of ``{"page": int, "text": str}`` dicts.
        """
        image_paths, tmp_dir = self._pdf_to_images(pdf_path, dpi)
        try:
            results: list[dict] = []

            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(self.ocr_image, img, "base"): i
                    for i, img in enumerate(image_paths)
                }
                for future in as_completed(futures):
                    page_idx = futures[future]
                    try:
                        text = future.result()
                    except Exception as e:
                        logger.error(f"OCR failed for page {page_idx + 1}: {e}")
                        text = ""
                    results.append({"page": page_idx + 1, "text": text})

            results.sort(key=lambda r: r["page"])
            logger.info(
                f"OCR completed for PDF {os.path.basename(pdf_path)}: "
                f"{len(results)} pages"
            )
            return results
        finally:
            if tmp_dir and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _pdf_to_images(pdf_path: str, dpi: int = 300) -> tuple[list[str], str]:
        """Convert PDF pages to PNG images in a temp directory."""
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        tmp_dir = tempfile.mkdtemp(prefix="ocr_pdf_")
        image_paths: list[str] = []
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        for i, page in enumerate(doc):
            out_path = os.path.join(tmp_dir, f"page_{i + 1:04d}.png")
            page.get_pixmap(matrix=mat).save(out_path)
            image_paths.append(out_path)
        doc.close()
        return image_paths, tmp_dir

    @staticmethod
    def _encode_image(image_path: str) -> dict:
        """Base64-encode an image for the OpenAI-compatible API."""
        ext = os.path.splitext(image_path)[1].lower()
        mime = "image/jpeg" if ext in (".jpg", ".jpeg") else f"image/{ext.lstrip('.')}"
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{data}"}}

    @classmethod
    def _build_content(cls, image_path: str) -> list[dict]:
        """Build the ``messages[].content`` array for a single image."""
        return [{"type": "text", "text": _PROMPT}, cls._encode_image(image_path)]

    @staticmethod
    def _build_payload(content: list[dict], image_mode: str) -> dict:
        """Build the full request payload."""
        return {
            "model": _MODEL_NAME,
            "messages": [{"role": "user", "content": content}],
            "temperature": _TEMPERATURE,
            "skip_special_tokens": False,
            "stream": True,
            "images_config": {"image_mode": image_mode},
        }

    @staticmethod
    def _collect_stream(resp) -> dict:
        """Read an SSE stream and return ``{tokens, decode_time, text}``."""
        chunks: list[str] = []
        token_count = 0
        first_token_time = None

        for raw_line in resp.iter_lines():
            if not raw_line:
                continue
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            if not line.startswith("data:"):
                continue
            data = line[len("data:"):].strip()
            if data == "[DONE]":
                break
            try:
                chunk = json.loads(data)
                delta = chunk["choices"][0]["delta"].get("content", "")
            except (json.JSONDecodeError, KeyError):
                continue
            if not delta:
                continue
            if first_token_time is None:
                first_token_time = time.time()
            token_count += 1
            chunks.append(delta)

        end_time = time.time()
        decode_time = (
            (end_time - first_token_time) if first_token_time and token_count > 1 else 0
        )
        return {"tokens": token_count, "decode_time": decode_time, "text": "".join(chunks)}
