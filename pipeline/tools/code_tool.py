"""
Code Tool.

Handles programming, debugging, algorithm, and software-related queries
using a code-specialised LLM (qwen2.5-coder:7b via Ollama).
"""

from __future__ import annotations

from src.agent.base_tool import BaseTool, ToolResult
from src.core.logging import LoggerManager
from src.llm import OllamaManager
from src.pipeline.pipeline_result import AnswerSource

logger = LoggerManager.get_logger()

_CODE_PROMPT = """You are an expert software engineer and coding assistant.

Answer the following programming question clearly and accurately.
- Provide working code examples where relevant.
- Use markdown code blocks with the correct language tag.
- Explain your reasoning step by step.

Question: {query}

Answer:"""


# Generates code responses using the LLM.
class CodeTool(BaseTool):
    """
    Handles code-related queries using a code-specialised LLM.
    """

    name = "code"

    # Sets up Ollama manager and target model.
    def __init__(
        self,
        ollama_manager: OllamaManager,
        model: str,
    ) -> None:
        self.ollama_manager = ollama_manager
        self.model = model

    # Executes code generation using the language model.
    def execute(self, query: str) -> ToolResult:
        """
        Generate a code-focused answer using the code model.
        """

        logger.info(f"CodeTool executing for query: {query!r} using model '{self.model}'")

        prompt = _CODE_PROMPT.format(query=query)

        try:
            answer = self.ollama_manager.generate(
                model=self.model,
                prompt=prompt,
                options={"num_predict": 1024},
            )
        except Exception as exc:
            # If the code model is unavailable, warn and fall back to chat model
            logger.warning(
                f"CodeTool model '{self.model}' unavailable: {exc}. "
                "Ensure you have run: ollama pull cieloforge/qwen2.5-coder-7b-instruct-spec:latest"
            )
            raise

        answer = answer.strip()

        logger.info("CodeTool completed.")

        return ToolResult(
            answer=answer,
            answer_source=AnswerSource.CODE,
            sources=[],
            context="",
        )

    # Generates a code response from the model.
    def execute_stream(self, query: str):
        """
        Generate a code-focused answer using the code model as a stream of events.
        """
        logger.info(f"CodeTool executing_stream for query: {query!r} using model '{self.model}'")

        yield {"type": "status", "message": "Writing code..."}

        prompt = _CODE_PROMPT.format(query=query)

        try:
            stream = self.ollama_manager.generate_stream(
                model=self.model,
                prompt=prompt,
                options={"num_predict": 1024},
            )

            full_answer_chunks = []
            for chunk in stream:
                full_answer_chunks.append(chunk)
                yield {"type": "chunk", "content": chunk}

            answer = "".join(full_answer_chunks)

        except Exception as exc:
            logger.warning(f"CodeTool model '{self.model}' unavailable: {exc}")
            raise

        answer = answer.strip()

        logger.info("CodeTool streaming completed.")

        result = ToolResult(
            answer=answer,
            answer_source=AnswerSource.CODE,
            sources=[],
            context="",
        )
        yield {"type": "result", "data": result}

