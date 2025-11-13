"""
Data models for the AutoGrader system.

This package contains all Pydantic models used throughout the system.
"""

from models.agent_result import AgentResult
from models.core import (
    CodeBlock,
    Diagram,
    Section,
    DocumentStructure,
    ParsedDocument,
    CriterionEvaluation,
    CategoryBreakdown,
    GradingResult,
    GradingRequest,
)
from models.io import (
    EvaluatorInput,
    ScoringInput,
    ReportInput,
    ReportOutput,
    ValidationInput,
    ValidationResult,
    CostReport,
)

__all__ = [
    # Agent result
    "AgentResult",
    # Core models
    "CodeBlock",
    "Diagram",
    "Section",
    "DocumentStructure",
    "ParsedDocument",
    "CriterionEvaluation",
    "CategoryBreakdown",
    "GradingResult",
    "GradingRequest",
    # I/O models
    "EvaluatorInput",
    "ScoringInput",
    "ReportInput",
    "ReportOutput",
    "ValidationInput",
    "ValidationResult",
    "CostReport",
]
