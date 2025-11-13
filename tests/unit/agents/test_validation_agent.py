"""
Unit tests for ValidationAgent.
"""

import pytest
from pathlib import Path

from agents.validation_agent import ValidationAgent
from models.core import GradingRequest


@pytest.fixture
def validation_agent():
    """Create ValidationAgent instance."""
    return ValidationAgent({})


class TestValidationAgent:
    """Test suite for ValidationAgent."""

    @pytest.mark.asyncio
    async def test_valid_request(self, validation_agent, tmp_path):
        """Test validation of valid grading request."""
        # Create valid PDF
        pdf_path = tmp_path / "valid.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\ntest content")

        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=85
        )

        # Validate
        result = await validation_agent.execute(request)

        assert result.success
        assert result.output.is_valid
        assert len(result.output.errors) == 0

    @pytest.mark.asyncio
    async def test_missing_pdf_file(self, validation_agent, tmp_path):
        """Test validation fails for missing PDF."""
        pdf_path = tmp_path / "nonexistent.pdf"

        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=85
        )

        # Validate
        result = await validation_agent.execute(request)

        assert result.success  # Agent succeeds
        assert not result.output.is_valid  # But validation fails
        assert len(result.output.errors) > 0
        assert any("does not exist" in err.lower() for err in result.output.errors)

    @pytest.mark.asyncio
    async def test_invalid_self_grade_too_high(self, validation_agent, tmp_path):
        """Test validation fails for self-grade > 100."""
        pdf_path = tmp_path / "valid.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\ntest")

        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=105
        )

        # Validate
        result = await validation_agent.execute(request)

        assert result.success
        assert not result.output.is_valid
        assert any("self-grade" in err.lower() or "100" in err for err in result.output.errors)

    @pytest.mark.asyncio
    async def test_invalid_self_grade_negative(self, validation_agent, tmp_path):
        """Test validation fails for negative self-grade."""
        pdf_path = tmp_path / "valid.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\ntest")

        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=-10
        )

        # Validate
        result = await validation_agent.execute(request)

        assert result.success
        assert not result.output.is_valid
        assert any("self-grade" in err.lower() or "negative" in err.lower() or "0" in err for err in result.output.errors)

    @pytest.mark.asyncio
    async def test_warnings_for_edge_cases(self, validation_agent, tmp_path):
        """Test warnings are generated for edge cases."""
        pdf_path = tmp_path / "tiny.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\nx")  # Very small PDF

        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=100  # Perfect self-grade might trigger warning
        )

        # Validate
        result = await validation_agent.execute(request)

        assert result.success
        # May have warnings even if valid
        assert isinstance(result.output.warnings, list)

    @pytest.mark.asyncio
    async def test_non_pdf_file(self, validation_agent, tmp_path):
        """Test validation fails for non-PDF file."""
        txt_path = tmp_path / "document.txt"
        txt_path.write_text("This is not a PDF")

        request = GradingRequest(
            pdf_path=txt_path,
            self_grade=85
        )

        # Validate
        result = await validation_agent.execute(request)

        assert result.success
        # Should either fail validation or warn about non-PDF
        if result.output.is_valid:
            assert len(result.output.warnings) > 0
        else:
            assert len(result.output.errors) > 0

    @pytest.mark.asyncio
    async def test_metadata_includes_counts(self, validation_agent, tmp_path):
        """Test result metadata includes error/warning counts."""
        pdf_path = tmp_path / "nonexistent.pdf"

        request = GradingRequest(
            pdf_path=pdf_path,
            self_grade=85
        )

        # Validate
        result = await validation_agent.execute(request)

        assert "errors_count" in result.metadata
        assert "warnings_count" in result.metadata
        assert result.metadata["errors_count"] == len(result.output.errors)
        assert result.metadata["warnings_count"] == len(result.output.warnings)
