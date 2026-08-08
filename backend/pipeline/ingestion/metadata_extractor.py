"""
Metadata Extractor.

Extracts metadata directly available from the PDF.
"""

from pipeline.models import DocumentContent


# Returns the DocumentContent object unchanged.
class MetadataExtractor:
    """
    Extract metadata from DocumentContent.
    """

    # Returns the input document unchanged.
    def extract(
        self,
        document: DocumentContent,
    ) -> DocumentContent:
        """
        Currently the PDF loader already extracts
        available metadata.

        This class exists so that future extractors
        (DOCX, HTML, OCR) follow the same interface.
        """

        return document