"""
Integration tests for end-to-end grading workflow.
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from models.core import GradingRequest
from tests.mocks import MockClaudeAPI, MockPDFParser


@pytest.mark.integration
@pytest.mark.asyncio
class TestGradingWorkflow:
    """Integration tests for complete grading workflow."""

    async def test_full_workflow_with_mocks(self, tmp_path):
        """Test complete workflow from request to result with mocked dependencies."""
        # Create test PDF
        pdf_path = tmp_path / "test_submission.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest content\n%%EOF")

        # Create grading request
        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=85
        )

        # Mock Claude API
        mock_api = MockClaudeAPI(default_score=85.0)

        # Mock PDF parser
        mock_parser = MockPDFParser()

        # Patch dependencies and run orchestrator
        with patch('skills.llm_evaluation_skill.LLMEvaluationSkill') as mock_llm_class:
            with patch('skills.pdf_processing_skill.PDFProcessingSkill') as mock_pdf_class:
                # Configure mocks
                mock_llm_instance = AsyncMock()
                mock_llm_instance.evaluate_with_claude = mock_api.evaluate
                mock_llm_class.return_value = mock_llm_instance

                mock_pdf_instance = MockPDFParser()
                mock_pdf_class.return_value = mock_pdf_instance

                # Import and run orchestrator
                from agents.orchestrator_agent import OrchestratorAgent

                orchestrator = OrchestratorAgent({})
                result = await orchestrator.execute(request)

                # Verify workflow completed
                assert result.success
                assert result.output is not None

                grading_result = result.output

                # Verify grading result structure
                assert grading_result.submission_id
                assert grading_result.self_grade == 85
                assert grading_result.final_score >= 0
                assert grading_result.final_score <= 100
                assert grading_result.criticism_multiplier > 0
                assert len(grading_result.evaluations) > 0
                assert grading_result.processing_time_seconds > 0

    async def test_validation_failure_stops_workflow(self, tmp_path):
        """Test that validation failure prevents further processing."""
        # Create invalid request (missing PDF)
        pdf_path = tmp_path / "nonexistent.pdf"

        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=85
        )

        from agents.orchestrator_agent import OrchestratorAgent

        orchestrator = OrchestratorAgent({})
        result = await orchestrator.execute(request)

        # Should fail at validation
        assert not result.success
        assert "validation" in result.error.lower() or "validation" in str(result.metadata).lower()

    async def test_criticism_multiplier_affects_evaluation(self, tmp_path):
        """Test that criticism multiplier affects final scores."""
        pdf_path = tmp_path / "test.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nTest\n%%EOF")

        # High self-grade (strict evaluation)
        high_grade_request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=95
        )

        # Low self-grade (lenient evaluation)
        low_grade_request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=65
        )

        with patch('skills.llm_evaluation_skill.LLMEvaluationSkill') as mock_llm_class:
            with patch('skills.pdf_processing_skill.PDFProcessingSkill') as mock_pdf_class:
                mock_api = MockClaudeAPI(default_score=80.0)
                mock_llm_instance = AsyncMock()
                mock_llm_instance.evaluate_with_claude = mock_api.evaluate
                mock_llm_class.return_value = mock_llm_instance

                mock_pdf_instance = MockPDFParser()
                mock_pdf_class.return_value = mock_pdf_instance

                from agents.orchestrator_agent import OrchestratorAgent

                orchestrator = OrchestratorAgent({})

                # Test high grade (strict)
                high_result = await orchestrator.execute(high_grade_request)
                assert high_result.success
                assert high_result.output.criticism_multiplier > 1.0

                # Reset orchestrator
                orchestrator = OrchestratorAgent({})

                # Test low grade (lenient)
                low_result = await orchestrator.execute(low_grade_request)
                assert low_result.success
                assert low_result.output.criticism_multiplier < 1.0


@pytest.mark.integration
class TestAgentIntegration:
    """Integration tests for agent interactions."""

    @pytest.mark.asyncio
    async def test_validation_to_parsing_flow(self, tmp_path):
        """Test data flow from validation to parsing."""
        from agents.validation_agent import ValidationAgent
        from agents.parser_agent import ParserAgent

        # Create valid PDF
        pdf_path = tmp_path / "valid.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nContent\n%%EOF")

        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=85
        )

        # Validate
        validator = ValidationAgent({})
        val_result = await validator.execute(request)

        assert val_result.success
        assert val_result.output.is_valid

        # If valid, proceed to parsing
        if val_result.output.is_valid:
            parser = ParserAgent({"cache_enabled": False})

            with patch('skills.pdf_processing_skill.PDFProcessingSkill') as mock_pdf:
                mock_parser = MockPDFParser()
                mock_pdf.return_value = mock_parser

                parse_result = await parser.execute(pdf_path)

                assert parse_result.success
                assert parse_result.output is not None

    @pytest.mark.asyncio
    async def test_scoring_to_reporting_flow(self, tmp_path, sample_criterion_evaluation):
        """Test data flow from scoring to reporting."""
        from agents.scoring_agent import ScoringAgent
        from agents.reporter_agent import ReporterAgent
        from models.io import ScoringInput

        # Create scoring input
        scoring_input = ScoringInput(
            evaluations=[sample_criterion_evaluation],
            criticism_multiplier=1.0,
            self_grade=85
        )

        # Score
        scorer = ScoringAgent({})
        score_result = await scorer.execute(scoring_input)

        assert score_result.success
        grading_result = score_result.output

        # Report
        reporter = ReporterAgent({
            "output_dir": str(tmp_path / "outputs"),
            "formats": ["markdown", "json"]
        })

        report_result = await reporter.execute(grading_result)

        assert report_result.success
        assert "markdown" in report_result.output.paths
        assert "json" in report_result.output.paths

        # Verify files were created
        md_path = Path(report_result.output.paths["markdown"])
        json_path = Path(report_result.output.paths["json"])

        assert md_path.exists()
        assert json_path.exists()
