"""
Reflection Layer.

If the Validation Layer scores an answer below the confidence threshold,
the Reflector re-runs the same tool with a refined prompt that instructs
the LLM to improve on the identified weakness.

Max retries: 2 (configurable via MAX_RETRIES).
After all retries, the attempt with the highest confidence score is returned.
"""

from __future__ import annotations

from src.agent.base_tool import BaseTool, ToolResult
from src.core.logging import LoggerManager
from src.validation.validation_layer import ValidationLayer, ValidationResult

logger = LoggerManager.get_logger()

MAX_RETRIES = 2

_RETRY_PROMPT_TEMPLATE = """Your previous answer scored {score:.1f}/10.

Evaluator feedback: {reasoning}

Please improve your answer by addressing the identified weakness.
Be more thorough, accurate, and include relevant source references if applicable.

Original question: {query}

Improved answer:"""


# Manages reflection retries for improved answer quality.
class Reflector:
    """
    Manages the reflection retry loop.

    Runs up to MAX_RETRIES additional attempts when the answer confidence
    is below the validation threshold. Keeps track of all attempts and
    returns the best one.
    """

    # Initializes validator and retry count settings
    def __init__(
        self,
        validator: ValidationLayer,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        self.validator = validator
        self.max_retries = max_retries

    # Executes the reflection retry loop logic.
    def reflect(
        self,
        tool: BaseTool,
        query: str,
        initial_result: ToolResult,
        initial_validation: ValidationResult,
    ) -> tuple[ToolResult, ValidationResult, int]:
        """
        Run the reflection retry loop.

        Parameters
        ----------
        tool                : The tool that produced the initial result.
        query               : The original user query.
        initial_result      : The tool's first attempt.
        initial_validation  : The validation score for the first attempt.

        Returns
        -------
        tuple of (best_result, best_validation, total_iterations)
            best_result      : ToolResult with the highest confidence score.
            best_validation  : Corresponding ValidationResult.
            total_iterations : Total number of tool executions (1 + retries).
        """

        best_result     = initial_result
        best_validation = initial_validation
        iterations      = 1

        for attempt in range(1, self.max_retries + 1):

            if best_validation.confidence_score >= self.validator.threshold:
                logger.info(
                    f"Reflector: confidence {best_validation.confidence_score:.1f} "
                    f"meets threshold {self.validator.threshold} — stopping early."
                )
                break

            logger.info(
                f"Reflector: attempt {attempt}/{self.max_retries} "
                f"(score={best_validation.confidence_score:.1f}, "
                f"threshold={self.validator.threshold})"
            )

            # Build a refined query that incorporates evaluator feedback
            refined_query = _RETRY_PROMPT_TEMPLATE.format(
                score=best_validation.confidence_score,
                reasoning=best_validation.reasoning,
                query=query,
            )

            try:
                retry_result = tool.execute(refined_query)
            except Exception as exc:
                logger.warning(f"Reflector: tool execution failed on attempt {attempt}: {exc}")
                break

            retry_validation = self.validator.validate(
                query=query,
                answer=retry_result.answer,
                context=retry_result.context,
            )

            iterations += 1

            if retry_validation.confidence_score > best_validation.confidence_score:
                logger.info(
                    f"Reflector: improved score "
                    f"{best_validation.confidence_score:.1f} → "
                    f"{retry_validation.confidence_score:.1f}"
                )
                best_result     = retry_result
                best_validation = retry_validation

            else:
                logger.info(
                    f"Reflector: attempt {attempt} did not improve "
                    f"({retry_validation.confidence_score:.1f} ≤ "
                    f"{best_validation.confidence_score:.1f}) — keeping previous best."
                )

        logger.info(
            f"Reflector finished: best_score={best_validation.confidence_score:.1f}, "
            f"iterations={iterations}"
        )

        return best_result, best_validation, iterations

    # Executes reflection retry loop for improved results.
    def reflect_stream(
        self,
        tool: BaseTool,
        query: str,
        initial_result: ToolResult,
        initial_validation: ValidationResult,
    ):
        """
        Run the reflection retry loop, yielding pipeline events.
        """
        best_result = initial_result
        best_validation = initial_validation
        iterations = 1

        for attempt in range(1, self.max_retries + 1):
            if best_validation.confidence_score >= self.validator.threshold:
                break
            
            yield {"type": "status", "message": f"Answer scored {best_validation.confidence_score:.1f}/10. Refining (Attempt {attempt}/{self.max_retries})..."}
            yield {"type": "clear_chunks"}

            refined_query = _RETRY_PROMPT_TEMPLATE.format(
                score=best_validation.confidence_score,
                reasoning=best_validation.reasoning,
                query=query,
            )

            try:
                stream = tool.execute_stream(refined_query)
                retry_result = None
                
                # Consume the tool stream and yield chunks upward
                for event in stream:
                    if event["type"] == "result":
                        retry_result = event["data"]
                    else:
                        yield event
                        
            except Exception as exc:
                logger.warning(f"Reflector: tool execution failed on attempt {attempt}: {exc}")
                break

            if retry_result is None:
                break
                
            yield {"type": "status", "message": "Evaluating refined answer..."}

            retry_validation = self.validator.validate(
                query=query,
                answer=retry_result.answer,
                context=retry_result.context,
            )

            iterations += 1

            if retry_validation.confidence_score > best_validation.confidence_score:
                logger.info(
                    f"Reflector: improved score "
                    f"{best_validation.confidence_score:.1f} → "
                    f"{retry_validation.confidence_score:.1f}"
                )
                best_result = retry_result
                best_validation = retry_validation
            else:
                logger.info("Reflector: attempt did not improve. Keeping previous best.")

        # Yield the final best outcome directly to the orchestrator (which yields it to the UI)
        return best_result, best_validation, iterations

