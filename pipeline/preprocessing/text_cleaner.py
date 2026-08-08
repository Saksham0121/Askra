"""
Text Cleaning Service.

Responsible for normalizing extracted document text
without changing its semantic meaning.
"""

import re
import unicodedata

from src.models import DocumentContent
from src.models import PageContent


# Cleans extracted document text for processing.
class TextCleaner:
    """
    Cleans extracted document text.
    """

    # Cleans and prepares document pages for processing.
    def clean(
        self,
        document: DocumentContent,
    ) -> DocumentContent:

        cleaned_pages = []

        for page in document.pages:

            text = self._clean_text(page.text)

            cleaned_pages.append(

                PageContent(
                    page_number=page.page_number,
                    text=text,
                )

            )

        return DocumentContent(
            metadata=document.metadata,
            pages=cleaned_pages,
        )

    @staticmethod
    # Cleans and normalizes input text string.
    def _clean_text(text: str) -> str:

        text = unicodedata.normalize("NFKC", text)

        text = text.replace("\r\n", "\n")

        text = text.replace("\r", "\n")

        text = re.sub(r"[^\S\n]+", " ", text)

        text = re.sub(r"\n{3,}", "\n\n", text)

        text = re.sub(r"[\x00-\x1F\x7F]", "", text)

        return text.strip()