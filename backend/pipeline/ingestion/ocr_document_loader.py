"""
OCR Document Loader.

Uses the OCRService to extract text from images and PDFs via the
Unlimited-OCR model. Returns the same DocumentContent model as
PDFDocumentLoader — fully compatible with the downstream pipeline.
"""

from __future__ import annotations

from pathlib import Path

from pipeline.core.logging import LoggerManager
from pipeline.models import DocumentContent, DocumentMetadata, PageContent
from pipeline.services.ocr_service import OCRService

logger = LoggerManager.get_logger()

# Image extensions the OCR loader can handle directly
_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class OCRDocumentLoader:
    """
    Loads documents using the Unlimited-OCR model for text extraction.

    Supports:
    - Single images → one-page DocumentContent
    - PDFs → multi-page DocumentContent (each page OCR'd independently)
    """

    def __init__(self, ocr_service: OCRService) -> None:
        self.ocr_service = ocr_service

    def load(self, file_path: str | Path) -> DocumentContent:
        """
        Load a file (image or PDF) using OCR.

        Parameters
        ----------
        file_path : Path to the image or PDF file.

        Returns
        -------
        DocumentContent with OCR-extracted text pages.

        Raises
        ------
        ValueError  : If the file extension is not supported.
        RuntimeError: If the OCR server is unavailable.
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()

        if not self.ocr_service.is_available():
            raise RuntimeError(
                "OCR server is not available. "
                "Please start the SGLang server with the Unlimited-OCR model."
            )

        if ext in _IMAGE_EXTENSIONS:
            return self._load_image(file_path)
        elif ext == ".pdf":
            return self._load_pdf(file_path)
        else:
            raise ValueError(
                f"Unsupported file type '{ext}' for OCR. "
                f"Supported: {_IMAGE_EXTENSIONS | {'.pdf'}}"
            )

    def _load_image(self, image_path: Path) -> DocumentContent:
        """OCR a single image file."""
        logger.info(f"OCR loading image: {image_path.name}")

        text = self.ocr_service.ocr_image(str(image_path))

        return DocumentContent(
            metadata=DocumentMetadata(
                title=image_path.stem,
                author=None,
                subject=None,
                keywords=[],
                publication_date=None,
                effective_date=None,
                version=None,
                language=None,
            ),
            pages=[PageContent(page_number=1, text=text)],
        )

    def _load_pdf(self, pdf_path: Path) -> DocumentContent:
        """OCR all pages of a PDF."""
        logger.info(f"OCR loading PDF: {pdf_path.name}")

        results = self.ocr_service.ocr_pdf(str(pdf_path))

        pages = [
            PageContent(page_number=r["page"], text=r["text"])
            for r in results
        ]

        # Try to extract basic metadata from the PDF
        metadata = self._extract_pdf_metadata(pdf_path)

        logger.info(
            f"OCR loaded PDF {pdf_path.name}: {len(pages)} pages"
        )

        return DocumentContent(metadata=metadata, pages=pages)

    @staticmethod
    def _extract_pdf_metadata(pdf_path: Path) -> DocumentMetadata:
        """Extract basic metadata from the PDF header (non-OCR)."""
        try:
            import fitz

            doc = fitz.open(str(pdf_path))
            meta = doc.metadata or {}
            doc.close()

            return DocumentMetadata(
                title=meta.get("title") or pdf_path.stem,
                author=meta.get("author"),
                subject=meta.get("subject"),
                keywords=[],
                publication_date=None,
                effective_date=None,
                version=None,
                language=None,
            )
        except Exception:
            return DocumentMetadata(
                title=pdf_path.stem,
                author=None,
                subject=None,
                keywords=[],
                publication_date=None,
                effective_date=None,
                version=None,
                language=None,
            )
