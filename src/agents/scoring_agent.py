"""
Scoring agent for calculating final grades from criterion evaluations.

This agent aggregates all criterion evaluations, applies weighted averaging,
severity factors, and criticism multipliers to produce the final grade.
"""

from typing import Any, Dict, List
import time

from models.agent_result import AgentResult
from models.core import GradingResult, CriterionEvaluation, CategoryBreakdown
from models.io import ScoringInput
from agents.base_agent import BaseAgent


class ScoringAgent(BaseAgent[ScoringInput, GradingResult]):
    """
    Agent that calculates final grades from criterion evaluations.

    Features:
    - Weighted averaging across all criteria
    - Severity factor adjustments
    - Criticism multiplier application
    - Category-level breakdown
    - Self-grade comparison

    Example:
        >>> agent = ScoringAgent({"severity_factors": {...}})
        >>> scoring_input = ScoringInput(evaluations=[...], criticism_multiplier=1.0, self_grade=85)
        >>> result = await agent.execute(scoring_input)
        >>> print(result.output.final_score)
        82.5
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the scoring agent.

        Args:
            config: Agent configuration with keys:
                - severity_factors: Dict mapping severity to adjustment factor
        """
        super().__init__(config)

        # Default severity factors
        self.severity_factors = self.get_config_value(
            'severity_factors',
            default={
                'critical': 0.5,    # 50% of score (major penalty)
                'important': 0.8,   # 80% of score
                'minor': 0.95,      # 95% of score
                'strength': 1.0     # 100% of score (no penalty)
            }
        )

    async def execute(self, input_data: ScoringInput) -> AgentResult[GradingResult]:
        """
        Calculate final grade from evaluations.

        Args:
            input_data: Scoring input with evaluations and metadata

        Returns:
            AgentResult with GradingResult
        """
        self.log_execution_start(
            input_data,
            num_evaluations=len(input_data.evaluations),
            criticism_multiplier=input_data.criticism_multiplier
        )

        start_time = time.time()

        try:
            # Calculate weighted scores
            weighted_sum = 0.0
            total_weight = 0.0

            for evaluation in input_data.evaluations:
                # Apply severity factor
                severity_factor = self.severity_factors.get(evaluation.severity, 1.0)
                adjusted_score = evaluation.score * severity_factor

                # Apply criticism multiplier
                adjusted_score = self._apply_criticism_multiplier(
                    adjusted_score,
                    input_data.criticism_multiplier
                )

                # Add to weighted sum
                weighted_sum += adjusted_score * evaluation.weight
                total_weight += evaluation.weight

            # Calculate final score
            if total_weight > 0:
                final_score = weighted_sum / total_weight
            else:
                self.logger.warning("Total weight is zero, defaulting to 0 score")
                final_score = 0.0

            # Ensure score is in valid range
            final_score = max(0.0, min(100.0, final_score))

            # Generate category breakdown
            breakdown = self._create_category_breakdown(input_data.evaluations)

            # Generate comparison message
            comparison_message = self._generate_comparison_message(
                final_score,
                input_data.self_grade,
                input_data.criticism_multiplier
            )

            # Create grading result
            grading_result = GradingResult(
                submission_id="",  # Will be set by orchestrator
                self_grade=input_data.self_grade,
                final_score=round(final_score, 2),
                criticism_multiplier=input_data.criticism_multiplier,
                evaluations=input_data.evaluations,
                breakdown=breakdown,
                comparison_message=comparison_message,
                processing_time_seconds=0.0  # Will be set by orchestrator
            )

            execution_time = time.time() - start_time
            self.log_execution_end(
                True,
                execution_time,
                final_score=final_score,
                difference=final_score - input_data.self_grade
            )

            return AgentResult.success_result(
                output=grading_result,
                metadata={
                    "final_score": final_score,
                    "difference": final_score - input_data.self_grade,
                    "total_weight": total_weight,
                    "num_categories": len(breakdown)
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.log_execution_end(False, execution_time)
            return self.handle_error(e)

    def _apply_criticism_multiplier(
        self,
        score: float,
        multiplier: float
    ) -> float:
        """
        Apply criticism multiplier to adjust score.

        Multiplier > 1.0: Stricter (reduce score on imperfections)
        Multiplier < 1.0: Lenient (recover some lost points)
        Multiplier = 1.0: No adjustment

        Args:
            score: Base score
            multiplier: Criticism multiplier

        Returns:
            Adjusted score
        """
        if score >= 100.0:
            return score  # Perfect score doesn't change

        if multiplier > 1.0:
            # Stricter: penalize imperfections more
            penalty = (100 - score) * (multiplier - 1.0) * 0.2
            return max(0.0, score - penalty)

        elif multiplier < 1.0:
            # Lenient: recover some points
            bonus = (100 - score) * (1.0 - multiplier) * 0.3
            return min(100.0, score + bonus)

        else:
            # No adjustment
            return score

    def _create_category_breakdown(
        self,
        evaluations: List[CriterionEvaluation]
    ) -> Dict[str, CategoryBreakdown]:
        """
        Create category-level breakdown of scores.

        Groups evaluations by category and calculates weighted averages.

        Args:
            evaluations: List of criterion evaluations

        Returns:
            Dictionary mapping category names to CategoryBreakdown
        """
        # Map criteria to categories (simplified - could be from config)
        category_map = {
            'prd_quality': 'Documentation',
            'architecture_doc': 'Documentation',
            'readme': 'Documentation',
            'project_structure': 'Code Quality',
            'code_documentation': 'Code Quality',
            'code_principles': 'Code Quality',
            'config_management': 'Configuration & Security',
            'security_practices': 'Configuration & Security',
            'unit_tests': 'Testing',
            'error_handling': 'Testing',
            'test_results': 'Testing',
            'parameter_exploration': 'Research & Analysis',
            'analysis_notebook': 'Research & Analysis',
            'visualization': 'Research & Analysis',
            'usability': 'UI/UX',
            'interface_documentation': 'UI/UX',
            'git_practices': 'Version Control',
            'prompt_log': 'Version Control',
        }

        # Group evaluations by category
        categories: Dict[str, List[CriterionEvaluation]] = {}
        for evaluation in evaluations:
            category = category_map.get(evaluation.criterion_id, 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(evaluation)

        # Calculate category breakdowns
        breakdown = {}
        for category_name, category_evals in categories.items():
            total_weight = sum(e.weight for e in category_evals)
            weighted_sum = sum(e.score * e.weight for e in category_evals)

            if total_weight > 0:
                weighted_score = weighted_sum / total_weight
            else:
                weighted_score = 0.0

            breakdown[category_name] = CategoryBreakdown(
                category_name=category_name,
                total_weight=total_weight,
                weighted_score=round(weighted_score, 2),
                criteria=category_evals
            )

        return breakdown

    def _generate_comparison_message(
        self,
        final_score: float,
        self_grade: int,
        criticism_multiplier: float
    ) -> str:
        """
        Generate message comparing final score to self-grade.

        Args:
            final_score: Calculated final score
            self_grade: Student's self-assessed grade
            criticism_multiplier: Applied criticism multiplier

        Returns:
            Comparison message
        """
        difference = final_score - self_grade

        if abs(difference) < 2:
            accuracy = "very accurate"
        elif abs(difference) < 5:
            accuracy = "quite accurate"
        elif abs(difference) < 10:
            accuracy = "reasonably accurate"
        else:
            accuracy = "somewhat inaccurate"

        if difference > 5:
            direction = f"higher than your self-assessment by {difference:.1f} points"
            interpretation = "You were more modest than necessary."
        elif difference < -5:
            direction = f"lower than your self-assessment by {abs(difference):.1f} points"
            interpretation = "You may have overestimated some aspects."
        else:
            direction = "very close to your self-assessment"
            interpretation = "Your self-evaluation was well-calibrated."

        # Add criticism multiplier context
        if criticism_multiplier >= 1.5:
            multiplier_note = " (evaluated with very strict standards due to high self-grade)"
        elif criticism_multiplier >= 1.2:
            multiplier_note = " (evaluated with strict standards)"
        elif criticism_multiplier <= 0.6:
            multiplier_note = " (evaluated with supportive standards)"
        elif criticism_multiplier <= 0.8:
            multiplier_note = " (evaluated with encouraging standards)"
        else:
            multiplier_note = ""

        return (
            f"Your self-assessment was {accuracy}. "
            f"The final grade is {direction}. "
            f"{interpretation}{multiplier_note}"
        )
