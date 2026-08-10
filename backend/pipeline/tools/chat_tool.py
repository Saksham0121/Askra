"""
Chat Tool — uses GroqManager.
"""
from __future__ import annotations
from pipeline.agent.base_tool import BaseTool, ToolResult
from pipeline.core.logging import LoggerManager
from pipeline.llm.groq_manager import GroqManager
from pipeline.pipeline.pipeline_result import AnswerSource

logger = LoggerManager.get_logger()

_CHAT_PROMPT = """You are Askrab, a helpful enterprise AI assistant.

Answer the following question using your own knowledge.
Be concise, accurate, and professional.

Question: {query}

Answer:"""


class ChatTool(BaseTool):
    """Handles general conversational and factual queries using Groq LLM directly."""

    name = "chat"

    def __init__(self, groq_manager: GroqManager, model: str) -> None:
        self.groq_manager = groq_manager
        self.model = model

    def execute(self, query: str) -> ToolResult:
        logger.info(f"ChatTool executing for query: {query!r}")
        prompt = _CHAT_PROMPT.format(query=query)
        answer = self.groq_manager.generate(model=self.model, prompt=prompt)
        answer = answer.strip()
        logger.info("ChatTool completed.")
        return ToolResult(answer=answer, answer_source=AnswerSource.LLM, sources=[], context="")

    def execute_stream(self, query: str):
        logger.info(f"ChatTool execute_stream for query: {query!r}")
        yield {"type": "status", "message": "Answering from general knowledge..."}
        prompt = _CHAT_PROMPT.format(query=query)
        stream = self.groq_manager.generate_stream(model=self.model, prompt=prompt)
        answer = "".join(stream).strip()
        logger.info("ChatTool streaming completed.")
        yield {"type": "result", "data": ToolResult(
            answer=answer, answer_source=AnswerSource.LLM, sources=[], context=""
        )}
