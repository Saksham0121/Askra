"""
Chat Tool.

Answers general questions directly using the LLM (no document context).
Labels its answer as "llm" to indicate it comes from model knowledge.
"""

from __future__ import annotations

from src.agent.base_tool import BaseTool, ToolResult
from src.core.logging import LoggerManager
from src.llm import OllamaManager
from src.pipeline.pipeline_result import AnswerSource

logger = LoggerManager.get_logger()

_CHAT_PROMPT = """You are SAARTHI, a helpful enterprise assistant.

Answer the following question using your own knowledge.
Be concise, accurate, and professional.

Question: {query}

Answer:"""


# Handles conversational queries using the LLM directly.
class ChatTool(BaseTool):
    """
    Handles general conversational and factual queries using the LLM directly.
    """

    name = "chat"

    # Sets up Ollama manager and target model.
    def __init__(
        self,
        ollama_manager: OllamaManager,
        model: str,
    ) -> None:
        self.ollama_manager = ollama_manager
        self.model = model

    # Generates an answer using the LLM model.
    def execute(self, query: str) -> ToolResult:
        """
        Generate a direct LLM answer.
        """

        logger.info(f"ChatTool executing for query: {query!r}")

        prompt = _CHAT_PROMPT.format(query=query)

        answer = self.ollama_manager.generate(
            model=self.model,
            prompt=prompt,
            options={"num_predict": 768},
        )

        answer = answer.strip()

        logger.info("ChatTool completed.")

        return ToolResult(
            answer=answer,
            answer_source=AnswerSource.LLM,
            sources=[],
            context="",
        )

    # Streams LLM response as a sequence of events.
    def execute_stream(self, query: str):
        """
        Generate a direct LLM answer as a stream of events.
        """
        logger.info(f"ChatTool executing_stream for query: {query!r}")

        yield {"type": "status", "message": "Answering from general knowledge..."}

        prompt = _CHAT_PROMPT.format(query=query)

        stream = self.ollama_manager.generate_stream(
            model=self.model,
            prompt=prompt,
            options={"num_predict": 768},
        )

        full_answer_chunks = []
        for chunk in stream:
            full_answer_chunks.append(chunk)
            yield {"type": "chunk", "content": chunk}

        answer = "".join(full_answer_chunks).strip()

        logger.info("ChatTool streaming completed.")

        result = ToolResult(
            answer=answer,
            answer_source=AnswerSource.LLM,
            sources=[],
            context="",
        )
        yield {"type": "result", "data": result}

