"""
OCR Tool.

Agent tool that scans uploaded images and PDFs using the Unlimited-OCR
model via the SGLang inference server. The router dispatches queries like
"scan this document" or "extract text from the image" here.
"""

from __future__ import annotations

import os
from pathlib import Path

from pipeline.agent.base_tool import BaseTool, ToolResult
from pipeline.core.logging import LoggerManager
from pipeline.pipeline.pipeline_result import AnswerSource
from pipeline.services.ocr_service import OCRService

logger = LoggerManager.get_logger()

# Image extensions the tool can process
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
_SUPPORTED_EXTENSIONS = _IMAGE_EXTENSIONS | {".pdf"}


class OCRTool(BaseTool):
    """
    Scans images and PDFs using the Unlimited-OCR model.

    The tool looks for the most recently uploaded file in the uploads
    directory and OCRs it. Users can also specify a filename in their query.
    """

    name = "ocr"

    def __init__(
        self,
        ocr_service: OCRService,
        upload_dir: str = "./uploads",
    ) -> None:
        self.ocr_service = ocr_service
        self.upload_dir = upload_dir

    def execute(self, query: str) -> ToolResult:
        """Run OCR on the most recent uploadable file."""
        logger.info(f"OCRTool executing for query: {query!r}")

        if not self.ocr_service.is_available():
            return ToolResult(
                answer=(
                    "⚠️ The OCR server is not currently available. "
                    "Please ensure the SGLang server with the Unlimited-OCR model "
                    "is running and try again."
                ),
                answer_source=AnswerSource.OCR,
                sources=[],
                context="",
            )

        file_path = self._find_target_file(query)
        if file_path is None:
            return ToolResult(
                answer=(
                    "I couldn't find a suitable file to scan. "
                    "Please upload an image or PDF first, then ask me to scan it."
                ),
                answer_source=AnswerSource.OCR,
                sources=[],
                context="",
            )

        try:
            ext = file_path.suffix.lower()
            if ext == ".pdf":
                results = self.ocr_service.ocr_pdf(str(file_path))
                text = "\n\n---\n\n".join(
                    f"## Page {r['page']}\n\n{r['text']}" for r in results if r["text"]
                )
            else:
                text = self.ocr_service.ocr_image(str(file_path))

            if not text.strip():
                text = "The OCR process completed but no text was extracted from the file."

            answer = f"📄 **OCR Result for `{file_path.name}`:**\n\n{text}"

            logger.info(f"OCRTool completed for {file_path.name}")
            return ToolResult(
                answer=answer,
                answer_source=AnswerSource.OCR,
                sources=[file_path.name],
                context=text,
            )

        except Exception as exc:
            logger.error(f"OCRTool failed: {exc}")
            return ToolResult(
                answer=f"OCR scanning failed: {exc}",
                answer_source=AnswerSource.OCR,
                sources=[],
                context="",
            )

    def execute_stream(self, query: str, history: list[dict] | None = None):
        """Streaming version with status updates."""
        logger.info(f"OCRTool execute_stream for query: {query!r}")

        yield {"type": "status", "message": "🔍 Checking OCR server availability..."}

        if not self.ocr_service.is_available():
            yield {"type": "result", "data": ToolResult(
                answer=(
                    "⚠️ The OCR server is not currently available. "
                    "Please ensure the SGLang server with the Unlimited-OCR model "
                    "is running and try again."
                ),
                answer_source=AnswerSource.OCR,
                sources=[],
                context="",
            )}
            return

        yield {"type": "status", "message": "📁 Locating the file to scan..."}
        file_path = self._find_target_file(query)

        if file_path is None:
            yield {"type": "result", "data": ToolResult(
                answer=(
                    "I couldn't find a suitable file to scan. "
                    "Please upload an image or PDF first, then ask me to scan it."
                ),
                answer_source=AnswerSource.OCR,
                sources=[],
                context="",
            )}
            return

        try:
            ext = file_path.suffix.lower()

            if ext == ".pdf":
                yield {"type": "status", "message": f"📖 Scanning PDF `{file_path.name}` with OCR..."}
                results = self.ocr_service.ocr_pdf(str(file_path))
                text = "\n\n---\n\n".join(
                    f"## Page {r['page']}\n\n{r['text']}" for r in results if r["text"]
                )
            else:
                yield {"type": "status", "message": f"🖼️ Scanning image `{file_path.name}` with OCR..."}
                text = self.ocr_service.ocr_image(str(file_path))

            if not text.strip():
                text = "The OCR process completed but no text was extracted from the file."

            answer = f"📄 **OCR Result for `{file_path.name}`:**\n\n{text}"

            logger.info(f"OCRTool streaming completed for {file_path.name}")
            yield {"type": "result", "data": ToolResult(
                answer=answer,
                answer_source=AnswerSource.OCR,
                sources=[file_path.name],
                context=text,
            )}

        except Exception as exc:
            logger.error(f"OCRTool streaming failed: {exc}")
            yield {"type": "result", "data": ToolResult(
                answer=f"OCR scanning failed: {exc}",
                answer_source=AnswerSource.OCR,
                sources=[],
                context="",
            )}

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_target_file(self, query: str) -> Path | None:
        """
        Find the file to OCR.

        Strategy:
        1. Check if the query mentions a specific filename.
        2. Fall back to the most recently modified scannable file in uploads/.
        """
        upload_dir = Path(self.upload_dir)
        if not upload_dir.exists():
            return None

        # Strategy 1: look for a filename mentioned in the query
        q_lower = query.lower()
        for f in upload_dir.iterdir():
            if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS:
                if f.name.lower() in q_lower or f.stem.lower() in q_lower:
                    return f

        # Strategy 2: most recently modified scannable file
        candidates = [
            f for f in upload_dir.iterdir()
            if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTENSIONS
        ]
        if not candidates:
            return None

        return max(candidates, key=lambda f: f.stat().st_mtime)
