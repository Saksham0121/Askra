"""
Code Tool — uses GroqManager.
"""
from __future__ import annotations
from pipeline.agent.base_tool import BaseTool, ToolResult
from pipeline.core.logging import LoggerManager
from pipeline.llm.groq_manager import GroqManager
from pipeline.pipeline.pipeline_result import AnswerSource

logger = LoggerManager.get_logger()

_CODE_PROMPT = """You are an expert software engineer and coding assistant.

{history_block}Answer the following programming question clearly and accurately.
- Provide working code examples where relevant.
- Use markdown code blocks with the correct language tag.
- Explain your reasoning step by step.

Question: {query}

Answer:"""


def _build_history_block(history: list[dict]) -> str:
    if not history:
        return ""
    lines = ["Conversation so far:"]
    for msg in history[-10:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content'][:500]}")
    return "\n".join(lines) + "\n\n"


class CodeTool(BaseTool):
    """Handles code-related queries using Groq LLM."""

    name = "code"

    def __init__(self, groq_manager: GroqManager, model: str) -> None:
        self.groq_manager = groq_manager
        self.model = model

    def execute(self, query: str) -> ToolResult:
        logger.info(f"CodeTool executing for query: {query!r}")
        prompt = _CODE_PROMPT.format(query=query, history_block="")
        answer = self.groq_manager.generate(model=self.model, prompt=prompt)
        answer = answer.strip()
        logger.info("CodeTool completed.")
        return ToolResult(answer=answer, answer_source=AnswerSource.CODE, sources=[], context="")

    def execute_stream(self, query: str, history: list[dict] | None = None):
        logger.info(f"CodeTool execute_stream for query: {query!r}")
        yield {"type": "status", "message": "Writing code..."}
        history_block = _build_history_block(history or [])
        prompt = _CODE_PROMPT.format(query=query, history_block=history_block)
        stream = self.groq_manager.generate_stream(model=self.model, prompt=prompt)
        answer = "".join(stream).strip()
        logger.info("CodeTool streaming completed.")
        yield {"type": "result", "data": ToolResult(
            answer=answer, answer_source=AnswerSource.CODE, sources=[], context=""
        )}
