"""
Pytest configuration and shared fixtures for AutoGrader tests.
"""

import pytest
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
import tempfile
import shutil

from models.core import (
    ParsedDocument, DocumentStructure, Section, CodeBlock,
    CriterionEvaluation, GradingResult, GradingRequest
)
from models.io import EvaluatorInput, ValidationResult


# ============================================================================
# Path Fixtures
# ============================================================================

@pytest.fixture
def test_data_dir() -> Path:
    """Return path to test data directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def temp_workspace(tmp_path) -> Path:
    """Create temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "inputs").mkdir()
    (workspace / "intermediate" / "evaluations").mkdir(parents=True)
    (workspace / "outputs").mkdir()
    return workspace


@pytest.fixture
def temp_config_file(tmp_path) -> Path:
    """Create temporary config file."""
    config_path = tmp_path / "config.yaml"
    config_content = """
orchestrator:
  max_parallel_evaluations: 5
  timeout_seconds: 60

parser:
  engine: "pymupdf"
  cache_enabled: false

llm:
  api_key: "test-api-key"
  model: "claude-sonnet-4-20250514"
  max_tokens: 1000
  temperature: 0.0

evaluators:
  - criterion: "test_criterion"
    weight: 1.0
    prompt_template: "prompts/test.txt"
"""
    config_path.write_text(config_content)
    return config_path


# ============================================================================
# Model Fixtures
# ============================================================================

@pytest.fixture
def sample_code_block() -> CodeBlock:
    """Create sample code block."""
    return CodeBlock(
        content="def hello():\n    print('Hello, world!')",
        language="python",
        line_start=10,
        line_end=11
    )


@pytest.fixture
def sample_section() -> Section:
    """Create sample document section."""
    return Section(
        title="Introduction",
        content="This is the introduction section with important information.",
        level=1,
        page_number=1
    )


@pytest.fixture
def sample_parsed_document(sample_section, sample_code_block) -> ParsedDocument:
    """Create sample parsed document."""
    return ParsedDocument(
        file_path=Path("test.pdf"),
        total_pages=5,
        full_text="Full document text content here.",
        code_blocks=[sample_code_block],
        diagrams=[],
        structure=DocumentStructure(
            title="Test Document",
            sections=[sample_section],
            toc=["Introduction", "Methods", "Results"]
        ),
        metadata={
            "parser": "pymupdf",
            "file_size": 12345
        }
    )


@pytest.fixture
def sample_criterion_evaluation() -> CriterionEvaluation:
    """Create sample criterion evaluation."""
    return CriterionEvaluation(
        criterion_id="prd_quality",
        criterion_name="PRD Quality",
        weight=0.08,
        score=85.0,
        evidence=["Good requirements documentation", "Clear user stories"],
        strengths=["Comprehensive coverage", "Well structured"],
        weaknesses=["Missing some edge cases"],
        suggestions=["Add more detailed acceptance criteria"],
        severity="minor"
    )


@pytest.fixture
def sample_grading_result(sample_criterion_evaluation) -> GradingResult:
    """Create sample grading result."""
    return GradingResult(
        submission_id="test_submission_001",
        self_grade=85,
        final_score=82.5,
        criticism_multiplier=1.0,
        evaluations=[sample_criterion_evaluation],
        breakdown={},
        comparison_message="Your self-assessment was quite accurate.",
        processing_time_seconds=30.5
    )


@pytest.fixture
def sample_grading_request(tmp_path) -> GradingRequest:
    """Create sample grading request."""
    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_text("dummy pdf content")

    return GradingRequest(
        pdf_path=pdf_path,
        self_grade=85
    )


@pytest.fixture
def sample_evaluator_input(sample_parsed_document) -> EvaluatorInput:
    """Create sample evaluator input."""
    return EvaluatorInput(
        document=sample_parsed_document,
        criticism_multiplier=1.0,
        criterion_config={}
    )


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_claude_response() -> Dict[str, Any]:
    """Create mock Claude API response."""
    return {
        "evaluation": {
            "score": 85.0,
            "evidence": ["Good documentation", "Clear structure"],
            "strengths": ["Comprehensive", "Well-organized"],
            "weaknesses": ["Minor gaps in testing"],
            "suggestions": ["Add more unit tests"],
            "severity": "minor"
        },
        "input_tokens": 1000,
        "output_tokens": 500,
        "cost": 0.0105
    }


@pytest.fixture
def mock_llm_skill(mock_claude_response):
    """Create mock LLM evaluation skill."""
    mock = AsyncMock()
    mock.evaluate_with_claude.return_value = mock_claude_response
    return mock


@pytest.fixture
def mock_pdf_skill(sample_parsed_document):
    """Create mock PDF processing skill."""
    mock = Mock()
    mock.parse_pdf.return_value = sample_parsed_document
    return mock


@pytest.fixture
def mock_validation_result() -> ValidationResult:
    """Create mock validation result."""
    return ValidationResult(
        is_valid=True,
        errors=[],
        warnings=[]
    )


# ============================================================================
# File Fixtures
# ============================================================================

@pytest.fixture
def sample_pdf_path(tmp_path) -> Path:
    """Create sample PDF file."""
    pdf_path = tmp_path / "sample.pdf"
    # Create a minimal PDF-like file
    pdf_content = b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"
    pdf_path.write_bytes(pdf_content)
    return pdf_path


@pytest.fixture
def sample_json_file(tmp_path) -> Path:
    """Create sample JSON file."""
    json_path = tmp_path / "data.json"
    json_path.write_text('{"test": "data", "value": 123}')
    return json_path


# ============================================================================
# Agent Configuration Fixtures
# ============================================================================

@pytest.fixture
def base_agent_config() -> Dict[str, Any]:
    """Base configuration for agents."""
    return {
        "log_level": "INFO",
        "timeout": 60
    }


@pytest.fixture
def evaluator_agent_config() -> Dict[str, Any]:
    """Configuration for evaluator agent."""
    return {
        "criterion_id": "test_criterion",
        "criterion_name": "Test Criterion",
        "weight": 0.1,
        "prompt_template": "prompts/test_evaluation.txt",
        "keywords": ["test", "example"]
    }


@pytest.fixture
def parser_agent_config() -> Dict[str, Any]:
    """Configuration for parser agent."""
    return {
        "engine": "pymupdf",
        "fallback_engine": "pdfplumber",
        "cache_enabled": False,
        "extract_images": False
    }


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def capture_logs(caplog):
    """Fixture to capture log messages."""
    import logging
    caplog.set_level(logging.DEBUG)
    return caplog


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Reset environment variables for each test."""
    # Clear any AUTOGRADER_ prefixed env vars
    import os
    for key in list(os.environ.keys()):
        if key.startswith('AUTOGRADER_'):
            monkeypatch.delenv(key, raising=False)
