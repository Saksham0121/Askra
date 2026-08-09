"""
Production PDF Loader.

Extraction Priority

PyMuPDF
    ↓
pdfplumber
    ↓
PyPDF2
"""

from pathlib import Path

import fitz
import pdfplumber
from pypdf import PdfReader

from pipeline.core.logging import LoggerManager
from pipeline.models import DocumentContent
from pipeline.models import DocumentMetadata
from pipeline.models import PageContent

logger = LoggerManager.get_logger()


# Loads PDF content using multiple libraries.
class PDFDocumentLoader:
    """
    Enterprise PDF Loader.
    """

    # Loads PDF content using multiple libraries.
    def load(self, pdf_path: str | Path) -> DocumentContent:

        try:

            return self._load_pymupdf(pdf_path)

        except Exception as error:

            logger.warning(
                f"PyMuPDF failed: {error}"
            )

        try:

            return self._load_pdfplumber(pdf_path)

        except Exception as error:

            logger.warning(
                f"pdfplumber failed: {error}"
            )

        return self._load_pypdf2(pdf_path)

    # Loads PDF content and extracts metadata information.
    def _load_pymupdf(
        self,
        pdf_path: str | Path,
    ) -> DocumentContent:

        document = fitz.open(pdf_path)

        pages = []

        for page in document:

            pages.append(

                PageContent(
                    page_number=page.number + 1,
                    text=page.get_text(),
                )

            )

        metadata = DocumentMetadata(

            title=document.metadata.get("title"),

            author=document.metadata.get("author"),

            subject=document.metadata.get("subject"),

            keywords=[],

            publication_date=None,

            effective_date=None,

            version=None,

            language=None,
        )

        logger.info(
            "Loaded PDF using PyMuPDF."
        )

        return DocumentContent(
            metadata=metadata,
            pages=pages,
        )

    # Loads PDF content and extracts page data.
    def _load_pdfplumber(
        self,
        pdf_path: str | Path,
    ) -> DocumentContent:

        with pdfplumber.open(pdf_path) as pdf:

            pages = []

            for index, page in enumerate(pdf.pages):

                pages.append(

                    PageContent(
                        page_number=index + 1,
                        text=page.extract_text() or "",
                    )

                )

        metadata = DocumentMetadata(
            title=None,
            author=None,
            subject=None,
            keywords=[],
            publication_date=None,
            effective_date=None,
            version=None,
            language=None,
        )

        logger.info(
            "Loaded PDF using pdfplumber."
        )

        return DocumentContent(
            metadata=metadata,
            pages=pages,
        )

    # Loads PDF content and extracts page data.
    def _load_pypdf2(
        self,
        pdf_path: str | Path,
    ) -> DocumentContent:

        reader = PdfReader(pdf_path)

        pages = []

        for index, page in enumerate(reader.pages):

            pages.append(

                PageContent(
                    page_number=index + 1,
                    text=page.extract_text() or "",
                )

            )

        metadata = DocumentMetadata(
            title=None,
            author=None,
            subject=None,
            keywords=[],
            publication_date=None,
            effective_date=None,
            version=None,
            language=None,
        )

        logger.info(
            "Loaded PDF using PyPDF2."
        )

        return DocumentContent(
            metadata=metadata,
            pages=pages,
        )


# Backward compatibility alias
PDFLoader = PDFDocumentLoader