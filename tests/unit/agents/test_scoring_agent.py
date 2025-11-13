"""
Unit tests for ScoringAgent.
"""

import pytest

from agents.scoring_agent import ScoringAgent
from models.core import CriterionEvaluation
from models.io import ScoringInput


@pytest.fixture
def scoring_agent():
    """Create ScoringAgent instance."""
    return ScoringAgent({})


@pytest.fixture
def sample_evaluations():
    """Create sample criterion evaluations."""
    return [
        CriterionEvaluation(
            criterion_id="prd_quality",
            criterion_name="PRD Quality",
            weight=0.2,
            score=90.0,
            evidence=["Good PRD"],
            strengths=["Clear"],
            weaknesses=[],
            suggestions=[],
            severity="strength"
        ),
        CriterionEvaluation(
            criterion_id="code_quality",
            criterion_name="Code Quality",
            weight=0.3,
            score=80.0,
            evidence=["Good code"],
            strengths=["Well-structured"],
            weaknesses=["Minor issues"],
            suggestions=["Add tests"],
            severity="minor"
        ),
        CriterionEvaluation(
            criterion_id="testing",
            criterion_name="Testing",
            weight=0.5,
            score=70.0,
            evidence=["Some tests"],
            strengths=[],
            weaknesses=["Low coverage"],
            suggestions=["Add more tests"],
            severity="important"
        )
    ]


class TestScoringAgent:
    """Test suite for ScoringAgent."""

    @pytest.mark.asyncio
    async def test_calculate_weighted_score(self, scoring_agent, sample_evaluations):
        """Test weighted score calculation."""
        scoring_input = ScoringInput(
            evaluations=sample_evaluations,
            criticism_multiplier=1.0,
            self_grade=75
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        grading_result = result.output

        # Calculate expected: (90*0.2 + 80*0.3 + 70*0.5) / 1.0
        # = (18 + 24 + 35) = 77
        expected_score = 77.0
        assert abs(grading_result.final_score - expected_score) < 0.1

    @pytest.mark.asyncio
    async def test_criticism_multiplier_strict(self, scoring_agent):
        """Test stricter grading with high criticism multiplier."""
        evaluations = [
            CriterionEvaluation(
                criterion_id="test",
                criterion_name="Test",
                weight=1.0,
                score=90.0,
                evidence=[],
                strengths=[],
                weaknesses=[],
                suggestions=[],
                severity="minor"
            )
        ]

        scoring_input = ScoringInput(
            evaluations=evaluations,
            criticism_multiplier=1.5,  # Strict
            self_grade=95
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        # Score should be lower than base score due to strict multiplier
        assert result.output.final_score < 90.0

    @pytest.mark.asyncio
    async def test_criticism_multiplier_lenient(self, scoring_agent):
        """Test more lenient grading with low criticism multiplier."""
        evaluations = [
            CriterionEvaluation(
                criterion_id="test",
                criterion_name="Test",
                weight=1.0,
                score=70.0,
                evidence=[],
                strengths=[],
                weaknesses=[],
                suggestions=[],
                severity="minor"
            )
        ]

        scoring_input = ScoringInput(
            evaluations=evaluations,
            criticism_multiplier=0.6,  # Lenient
            self_grade=60
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        # Score should be higher than base score due to lenient multiplier
        assert result.output.final_score > 70.0

    @pytest.mark.asyncio
    async def test_severity_factors_applied(self, scoring_agent):
        """Test severity factors affect scores."""
        evaluations = [
            CriterionEvaluation(
                criterion_id="critical_issue",
                criterion_name="Critical Issue",
                weight=1.0,
                score=80.0,
                evidence=[],
                strengths=[],
                weaknesses=[],
                suggestions=[],
                severity="critical"  # Should apply 0.5 factor
            )
        ]

        scoring_input = ScoringInput(
            evaluations=evaluations,
            criticism_multiplier=1.0,
            self_grade=75
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        # Critical severity should reduce score significantly
        assert result.output.final_score < 80.0

    @pytest.mark.asyncio
    async def test_category_breakdown_generated(self, scoring_agent, sample_evaluations):
        """Test category breakdown is generated."""
        scoring_input = ScoringInput(
            evaluations=sample_evaluations,
            criticism_multiplier=1.0,
            self_grade=75
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        assert len(result.output.breakdown) > 0

        # Check that categories have expected structure
        for category_name, breakdown in result.output.breakdown.items():
            assert breakdown.category_name == category_name
            assert breakdown.total_weight > 0
            assert breakdown.weighted_score >= 0
            assert len(breakdown.criteria) > 0

    @pytest.mark.asyncio
    async def test_comparison_message_generated(self, scoring_agent, sample_evaluations):
        """Test comparison message is generated."""
        scoring_input = ScoringInput(
            evaluations=sample_evaluations,
            criticism_multiplier=1.0,
            self_grade=75
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        assert result.output.comparison_message
        assert len(result.output.comparison_message) > 0

    @pytest.mark.asyncio
    async def test_final_score_clamped(self, scoring_agent):
        """Test final score is clamped to 0-100 range."""
        # Extreme case that might produce score > 100
        evaluations = [
            CriterionEvaluation(
                criterion_id="perfect",
                criterion_name="Perfect",
                weight=1.0,
                score=100.0,
                evidence=[],
                strengths=[],
                weaknesses=[],
                suggestions=[],
                severity="strength"
            )
        ]

        scoring_input = ScoringInput(
            evaluations=evaluations,
            criticism_multiplier=0.5,  # Very lenient
            self_grade=50
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        assert 0 <= result.output.final_score <= 100

    @pytest.mark.asyncio
    async def test_metadata_includes_metrics(self, scoring_agent, sample_evaluations):
        """Test result metadata includes scoring metrics."""
        scoring_input = ScoringInput(
            evaluations=sample_evaluations,
            criticism_multiplier=1.0,
            self_grade=75
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        assert "final_score" in result.metadata
        assert "difference" in result.metadata
        assert "total_weight" in result.metadata
        assert "num_categories" in result.metadata

    @pytest.mark.asyncio
    async def test_empty_evaluations_handled(self, scoring_agent):
        """Test handling of empty evaluations list."""
        scoring_input = ScoringInput(
            evaluations=[],
            criticism_multiplier=1.0,
            self_grade=75
        )

        result = await scoring_agent.execute(scoring_input)

        # Should handle gracefully, likely with 0 score
        assert result.success
        assert result.output.final_score == 0.0

    @pytest.mark.asyncio
    async def test_self_grade_comparison_accurate(self, scoring_agent, sample_evaluations):
        """Test accurate self-grade comparison messaging."""
        scoring_input = ScoringInput(
            evaluations=sample_evaluations,
            criticism_multiplier=1.0,
            self_grade=77  # Very close to actual score
        )

        result = await scoring_agent.execute(scoring_input)

        assert result.success
        # Should indicate accurate self-assessment
        assert "accurate" in result.output.comparison_message.lower()
