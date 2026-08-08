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

Answer the following programming question clearly and accurately.
- Provide working code examples where relevant.
- Use markdown code blocks with the correct language tag.
- Explain your reasoning step by step.

Question: {query}

Answer:"""


class CodeTool(BaseTool):
    """Handles code-related queries using Groq LLM."""

    name = "code"

    def __init__(self, groq_manager: GroqManager, model: str) -> None:
        self.groq_manager = groq_manager
        self.model = model

    def execute(self, query: str) -> ToolResult:
        logger.info(f"CodeTool executing for query: {query!r}")
        prompt = _CODE_PROMPT.format(query=query)
        answer = self.groq_manager.generate(model=self.model, prompt=prompt)
        answer = answer.strip()
        logger.info("CodeTool completed.")
        return ToolResult(answer=answer, answer_source=AnswerSource.CODE, sources=[], context="")

    def execute_stream(self, query: str):
        logger.info(f"CodeTool execute_stream for query: {query!r}")
        yield {"type": "status", "message": "Writing code..."}
        prompt = _CODE_PROMPT.format(query=query)
        stream = self.groq_manager.generate_stream(model=self.model, prompt=prompt)
        full_chunks = []
        for chunk in stream:
            full_chunks.append(chunk)
            yield {"type": "chunk", "content": chunk}
        answer = "".join(full_chunks).strip()
        logger.info("CodeTool streaming completed.")
        yield {"type": "result", "data": ToolResult(
            answer=answer, answer_source=AnswerSource.CODE, sources=[], context=""
        )}
