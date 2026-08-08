"""
Context Builder.

Builds LLM-ready context from retrieved chunks.
"""

from src.models import EmbeddedChunk


# Builds context string from retrieved chunks.
class ContextBuilder:
    """
    Builds context for answer generation.
    """

    # Generates context string from retrieved chunks.
    def build(
        self,
        chunks: list[EmbeddedChunk],
    ) -> str:
        """
        Build context from retrieved chunks.
        """

        context_parts = []

        for chunk in chunks:

            context_parts.append(

                f"""Source: {chunk.chunk.source}
Page: {chunk.chunk.page_number}

{chunk.chunk.text}
"""

            )

        return "\n\n".join(
            context_parts
        )