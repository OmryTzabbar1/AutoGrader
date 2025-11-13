"""
Input/Output models for agent communication.

This module defines the data structures used for communication between agents,
including inputs and outputs for specific agent types.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from models.core import ParsedDocument, CriterionEvaluation, GradingResult


class EvaluatorInput(BaseModel):
    """
    Input data for an EvaluatorAgent.

    Attributes:
        document: The parsed PDF document to evaluate
        criticism_multiplier: The criticism multiplier to apply
        criterion_config: Optional criterion-specific configuration
    """

    document: ParsedDocument = Field(..., description="Parsed document")
    criticism_multiplier: float = Field(..., gt=0.0, description="Criticism multiplier")
    criterion_config: Dict = Field(default_factory=dict, description="Criterion config")


class ScoringInput(BaseModel):
    """
    Input data for the ScoringAgent.

    Attributes:
        evaluations: List of criterion evaluations to aggregate
        criticism_multiplier: The criticism multiplier that was applied
        self_grade: The student's self-assessed grade
    """

    evaluations: List[CriterionEvaluation] = Field(..., description="Evaluations")
    criticism_multiplier: float = Field(..., gt=0.0, description="Criticism multiplier")
    self_grade: int = Field(..., ge=0, le=100, description="Self-assessed grade")


class ReportInput(BaseModel):
    """
    Input data for the ReporterAgent.

    Attributes:
        grading_result: The complete grading result
        output_formats: List of desired output formats
        output_directory: Directory for output files
    """

    grading_result: GradingResult = Field(..., description="Grading result")
    output_formats: List[str] = Field(
        default_factory=lambda: ["markdown"],
        description="Output formats"
    )
    output_directory: Optional[str] = Field(None, description="Output directory")


class ReportOutput(BaseModel):
    """
    Output data from the ReporterAgent.

    Attributes:
        paths: Dictionary mapping format names to file paths
        generation_time: Time taken to generate all reports
    """

    paths: Dict[str, str] = Field(default_factory=dict, description="Report file paths")
    generation_time: float = Field(0.0, description="Generation time in seconds")

    def get_path(self, format_name: str) -> Optional[str]:
        """Get path for a specific format."""
        return self.paths.get(format_name)


class ValidationInput(BaseModel):
    """
    Input data for the ValidationAgent.

    Attributes:
        data: The data to validate (can be any type)
        validation_rules: Optional custom validation rules
    """

    data: Dict = Field(..., description="Data to validate")
    validation_rules: Optional[Dict] = Field(None, description="Validation rules")


class ValidationResult(BaseModel):
    """
    Result of validation.

    Attributes:
        is_valid: Whether the data passed validation
        errors: List of validation errors
        warnings: List of validation warnings
    """

    is_valid: bool = Field(..., description="Is data valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")

    def add_error(self, error: str) -> 'ValidationResult':
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False
        return self

    def add_warning(self, warning: str) -> 'ValidationResult':
        """Add a validation warning."""
        self.warnings.append(warning)
        return self


class CostReport(BaseModel):
    """
    Cost tracking report from CostTrackerAgent.

    Attributes:
        total_tokens: Total tokens used (input + output)
        total_cost: Total cost in USD
        cost_per_criterion: Cost breakdown by criterion
        api_calls: Number of API calls made
    """

    total_tokens: int = Field(0, description="Total tokens")
    total_cost: float = Field(0.0, description="Total cost USD")
    cost_per_criterion: Dict[str, float] = Field(default_factory=dict, description="Per-criterion costs")
    api_calls: int = Field(0, description="Number of API calls")

    def add_api_call(
        self,
        criterion: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> None:
        """Record an API call."""
        self.total_tokens += input_tokens + output_tokens
        self.total_cost += cost
        self.api_calls += 1

        if criterion not in self.cost_per_criterion:
            self.cost_per_criterion[criterion] = 0.0
        self.cost_per_criterion[criterion] += cost

    def get_average_cost_per_call(self) -> float:
        """Calculate average cost per API call."""
        if self.api_calls == 0:
            return 0.0
        return self.total_cost / self.api_calls
