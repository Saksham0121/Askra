"""
Prompt Builder.

Builds prompts for the LLM.
"""


# Constructs a prompt for LLM answer generation.
class PromptBuilder:
    """
    Builds grounded prompts for answer generation.
    """

    # Constructs the complete LLM prompt for answering.
    def build(
        self,
        query: str,
        context: str,
    ) -> str:
        """
        Build the final LLM prompt.
        """

        return f"""
You are an enterprise legal AI assistant.

Answer ONLY using the provided context.

If the answer cannot be found in the context, reply with:

"I could not find the answer in the provided documents."

Always provide a concise and accurate answer.

-------------------------
Context
-------------------------

{context}

-------------------------
Question
-------------------------

{query}

-------------------------
Answer
-------------------------
""".strip()