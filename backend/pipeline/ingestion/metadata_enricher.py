"""
Metadata Enricher.

Infers metadata from document content.
"""

import re
from datetime import datetime

from langdetect import detect

from pipeline.models import DocumentContent
from pipeline.models import DocumentMetadata


# Enriches document metadata with date and version.
class MetadataEnricher:
    """
    Enrich document metadata.
    """

    DATE_PATTERN = r"(19|20)\d{2}"

    VERSION_PATTERN = r"v(?:ersion)?\s*([0-9]+(?:\.[0-9]+)?)"

    # Enriches document metadata with available information.
    def enrich(
        self,
        document: DocumentContent,
    ) -> DocumentContent:

        metadata = document.metadata

        first_page = ""

        if document.pages:

            first_page = document.pages[0].text

        publication_date = metadata.publication_date

        if publication_date is None:

            match = re.search(
                self.DATE_PATTERN,
                first_page,
            )

            if match:

                publication_date = datetime(
                    int(match.group()),
                    1,
                    1,
                )

        version = metadata.version

        if version is None:

            match = re.search(
                self.VERSION_PATTERN,
                first_page,
                re.IGNORECASE,
            )

            if match:

                version = match.group(1)

        language = metadata.language

        if language is None:

            try:

                language = detect(first_page)

            except Exception:

                language = None

        enriched = DocumentMetadata(

            title=metadata.title,

            author=metadata.author,

            subject=metadata.subject,

            keywords=metadata.keywords,

            publication_date=publication_date,

            effective_date=metadata.effective_date,

            version=version,

            language=language,
        )

        return DocumentContent(

            metadata=enriched,

            pages=document.pages,
        )