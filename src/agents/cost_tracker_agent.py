"""
Cost tracker agent for monitoring API usage and costs.

This agent tracks Claude API usage across all evaluations and provides
cost reports and budget warnings.
"""

from typing import Any, Dict
from pathlib import Path

from models.agent_result import AgentResult
from models.io import CostReport
from agents.base_agent import BaseAgent


class CostTrackerAgent(BaseAgent[str, CostReport]):
    """
    Agent that tracks API costs throughout the grading process.

    Features:
    - Track tokens and costs per API call
    - Aggregate costs by criterion
    - Generate cost reports
    - Budget warnings and alerts

    Example:
        >>> agent = CostTrackerAgent({"budget_limit": 10.0})
        >>> agent.track_api_call("prd_quality", 1000, 500, 0.0225)
        >>> result = await agent.execute("submission_123")
        >>> print(result.output.total_cost)
        0.0225
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the cost tracker agent.

        Args:
            config: Agent configuration with keys:
                - budget_limit: Maximum budget in USD (optional)
                - warn_threshold: Threshold for budget warnings (0.0-1.0)
        """
        super().__init__(config)

        # Cost tracking
        self.cost_report = CostReport()

        # Budget configuration
        self.budget_limit = self.get_config_value('budget_limit', default=None)
        self.warn_threshold = self.get_config_value('warn_threshold', default=0.8)

    def track_api_call(
        self,
        criterion: str,
        input_tokens: int,
        output_tokens: int,
        cost: float
    ) -> None:
        """
        Record an API call for cost tracking.

        Args:
            criterion: Criterion being evaluated
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost: Cost in USD
        """
        self.cost_report.add_api_call(criterion, input_tokens, output_tokens, cost)

        self.logger.debug(
            f"Tracked API call for {criterion}",
            extra={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cost": cost
            }
        )

        # Check budget warnings
        if self.budget_limit:
            self._check_budget_warning()

    def _check_budget_warning(self) -> None:
        """Check if budget threshold is exceeded and log warnings."""
        if not self.budget_limit:
            return

        usage_ratio = self.cost_report.total_cost / self.budget_limit

        if usage_ratio >= 1.0:
            self.logger.error(
                f"Budget exceeded! Spent ${self.cost_report.total_cost:.4f} "
                f"of ${self.budget_limit:.2f} budget"
            )
        elif usage_ratio >= self.warn_threshold:
            self.logger.warning(
                f"Budget warning: {usage_ratio*100:.1f}% of budget used "
                f"(${self.cost_report.total_cost:.4f} / ${self.budget_limit:.2f})"
            )

    async def execute(self, submission_id: str) -> AgentResult[CostReport]:
        """
        Generate cost report for a submission.

        Args:
            submission_id: Submission identifier

        Returns:
            AgentResult with CostReport
        """
        self.log_execution_start(
            submission_id,
            total_cost=self.cost_report.total_cost,
            api_calls=self.cost_report.api_calls
        )

        try:
            # Log cost summary
            self.logger.info(
                f"Cost summary for {submission_id}",
                extra={
                    "total_cost": f"${self.cost_report.total_cost:.4f}",
                    "total_tokens": self.cost_report.total_tokens,
                    "api_calls": self.cost_report.api_calls,
                    "avg_cost_per_call": f"${self.cost_report.get_average_cost_per_call():.4f}"
                }
            )

            # Log per-criterion costs
            for criterion, cost in sorted(
                self.cost_report.cost_per_criterion.items(),
                key=lambda x: x[1],
                reverse=True
            ):
                self.logger.debug(f"  {criterion}: ${cost:.4f}")

            return AgentResult.success_result(
                output=self.cost_report,
                metadata={
                    "within_budget": (
                        self.cost_report.total_cost <= self.budget_limit
                        if self.budget_limit else True
                    ),
                    "budget_used_pct": (
                        (self.cost_report.total_cost / self.budget_limit * 100)
                        if self.budget_limit else None
                    )
                }
            )

        except Exception as e:
            return self.handle_error(e)

    def reset(self) -> None:
        """Reset cost tracking for new submission."""
        self.cost_report = CostReport()
        self.logger.debug("Cost tracking reset")

    def get_total_cost(self) -> float:
        """Get current total cost."""
        return self.cost_report.total_cost

    def export_cost_report(self, output_path: Path) -> None:
        """
        Export cost report to JSON file.

        Args:
            output_path: Path to output file
        """
        import json

        report_dict = {
            "total_cost_usd": self.cost_report.total_cost,
            "total_tokens": self.cost_report.total_tokens,
            "api_calls": self.cost_report.api_calls,
            "average_cost_per_call": self.cost_report.get_average_cost_per_call(),
            "cost_per_criterion": self.cost_report.cost_per_criterion,
            "budget_limit": self.budget_limit,
            "within_budget": (
                self.cost_report.total_cost <= self.budget_limit
                if self.budget_limit else None
            )
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2)

        self.logger.info(f"Cost report exported to {output_path}")
