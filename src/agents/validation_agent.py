"""
Validation agent for validating grading requests.

This agent validates all inputs before the grading workflow begins.
"""

from typing import Any, Dict
from models.agent_result import AgentResult
from models.core import GradingRequest
from models.io import ValidationResult
from agents.base_agent import BaseAgent
from skills.data_validation_skill import DataValidationSkill


class ValidationAgent(BaseAgent[GradingRequest, ValidationResult]):
    """
    Agent that validates grading requests.

    Checks:
    - PDF file exists and is valid
    - Self-grade is in valid range (0-100)
    - All required fields are present

    Example:
        >>> agent = ValidationAgent({})
        >>> request = GradingRequest(pdf_path=Path("submission.pdf"), self_grade=85)
        >>> result = await agent.execute(request)
        >>> if result.success:
        ...     print("Request is valid")
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the validation agent.

        Args:
            config: Agent configuration
        """
        super().__init__(config)
        self.validation_skill = DataValidationSkill()

    async def execute(self, input_data: GradingRequest) -> AgentResult[ValidationResult]:
        """
        Validate a grading request.

        Args:
            input_data: Grading request to validate

        Returns:
            AgentResult with ValidationResult
        """
        self.log_execution_start(input_data)

        try:
            # Validate using skill
            validation_result = self.validation_skill.validate_grading_request(input_data)

            # Log validation results
            if validation_result.is_valid:
                self.logger.info(
                    f"Validation passed for {input_data.pdf_path.name}",
                    extra={
                        "warnings": len(validation_result.warnings),
                        "self_grade": input_data.self_grade
                    }
                )
            else:
                self.logger.error(
                    f"Validation failed for {input_data.pdf_path.name}",
                    extra={
                        "errors": validation_result.errors,
                        "warnings": validation_result.warnings
                    }
                )

            return AgentResult.success_result(
                output=validation_result,
                metadata={
                    "errors_count": len(validation_result.errors),
                    "warnings_count": len(validation_result.warnings)
                }
            )

        except Exception as e:
            return self.handle_error(e)
