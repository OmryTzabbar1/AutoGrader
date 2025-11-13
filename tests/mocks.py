"""
Mock objects and utilities for testing.

Provides mock implementations of external dependencies like Claude API
for testing without actual API calls.
"""

from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, Mock
import asyncio


class MockClaudeAPI:
    """
    Mock implementation of Claude API for testing.

    Simulates Claude API responses without making actual API calls.
    """

    def __init__(
        self,
        default_score: float = 85.0,
        raise_error: bool = False,
        delay: float = 0.0
    ):
        """
        Initialize mock Claude API.

        Args:
            default_score: Default score to return in evaluations
            raise_error: Whether to raise an error on API calls
            delay: Simulated API delay in seconds
        """
        self.default_score = default_score
        self.raise_error = raise_error
        self.delay = delay
        self.call_count = 0
        self.last_prompt = None
        self.last_context = None

    async def evaluate(
        self,
        prompt: str,
        context: str,
        criticism_multiplier: float = 1.0
    ) -> Dict[str, Any]:
        """
        Mock evaluation call.

        Args:
            prompt: Evaluation prompt
            context: Document context
            criticism_multiplier: Criticism adjustment factor

        Returns:
            Mock evaluation response

        Raises:
            Exception: If raise_error is True
        """
        self.call_count += 1
        self.last_prompt = prompt
        self.last_context = context

        if self.delay > 0:
            await asyncio.sleep(self.delay)

        if self.raise_error:
            raise Exception("Mock API error")

        # Adjust score based on criticism multiplier
        adjusted_score = self.default_score
        if criticism_multiplier > 1.0:
            adjusted_score *= 0.95  # Slightly lower for strict evaluation
        elif criticism_multiplier < 1.0:
            adjusted_score *= 1.05  # Slightly higher for lenient evaluation

        return {
            "evaluation": {
                "score": min(100.0, max(0.0, adjusted_score)),
                "evidence": [
                    f"Evidence from context (length: {len(context)})",
                    "Additional supporting evidence"
                ],
                "strengths": [
                    "Good implementation quality",
                    "Well-documented code"
                ],
                "weaknesses": [
                    "Minor improvements needed"
                ],
                "suggestions": [
                    "Consider adding more test coverage"
                ],
                "severity": "minor" if adjusted_score >= 70 else "important"
            },
            "input_tokens": len(prompt) // 4 + len(context) // 4,
            "output_tokens": 200,
            "cost": 0.0105
        }


class MockPDFParser:
    """
    Mock PDF parser for testing.
    """

    def __init__(self, should_fail: bool = False):
        """
        Initialize mock PDF parser.

        Args:
            should_fail: Whether parsing should fail
        """
        self.should_fail = should_fail
        self.parsed_count = 0

    def parse(self, pdf_path) -> Dict[str, Any]:
        """
        Mock PDF parsing.

        Args:
            pdf_path: Path to PDF file

        Returns:
            Mock parsed document data

        Raises:
            Exception: If should_fail is True
        """
        self.parsed_count += 1

        if self.should_fail:
            raise Exception(f"Failed to parse PDF: {pdf_path}")

        from models.core import ParsedDocument, DocumentStructure, Section, CodeBlock

        return ParsedDocument(
            file_path=pdf_path,
            total_pages=10,
            full_text=f"Mock content from {pdf_path.name}. This is a test document.",
            code_blocks=[
                CodeBlock(
                    content="def test():\n    pass",
                    language="python",
                    line_start=5,
                    line_end=6
                )
            ],
            diagrams=[],
            structure=DocumentStructure(
                title="Mock Document",
                sections=[
                    Section(
                        title="Introduction",
                        content="Mock introduction content",
                        level=1,
                        page_number=1
                    ),
                    Section(
                        title="Implementation",
                        content="Mock implementation details",
                        level=1,
                        page_number=3
                    )
                ],
                toc=["Introduction", "Implementation", "Conclusion"]
            ),
            metadata={"parser": "mock", "mock": True}
        )


class MockCostTracker:
    """
    Mock cost tracker for testing.
    """

    def __init__(self):
        """Initialize mock cost tracker."""
        self.total_cost = 0.0
        self.api_calls = 0
        self.cost_per_criterion = {}

    def track_api_call(
        self,
        criterion: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> None:
        """
        Track mock API call.

        Args:
            criterion: Criterion being evaluated
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Cost in USD
        """
        self.total_cost += cost
        self.api_calls += 1

        if criterion not in self.cost_per_criterion:
            self.cost_per_criterion[criterion] = 0.0
        self.cost_per_criterion[criterion] += cost

    def get_total_cost(self) -> float:
        """Get total cost."""
        return self.total_cost

    def reset(self) -> None:
        """Reset cost tracking."""
        self.total_cost = 0.0
        self.api_calls = 0
        self.cost_per_criterion = {}


def create_mock_agent_result(success: bool = True, output: Any = None, error: Optional[str] = None):
    """
    Create mock AgentResult.

    Args:
        success: Whether result was successful
        output: Output data
        error: Error message if failed

    Returns:
        Mock AgentResult
    """
    from models.agent_result import AgentResult

    if success:
        return AgentResult.success_result(
            output=output or {"mock": "data"},
            metadata={"test": True},
            execution_time=0.5
        )
    else:
        return AgentResult.failure_result(
            error=error or "Mock error",
            metadata={"test": True},
            execution_time=0.1
        )
