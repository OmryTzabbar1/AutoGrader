"""
Data validation skill for validating inputs and outputs.

This skill provides validation functions for PDFs, grades, evaluations,
and other data structures used in the grading system.
"""

from pathlib import Path
from typing import Any, List
import logging

from models.io import ValidationResult
from models.core import CriterionEvaluation, GradingRequest


class DataValidationSkill:
    """
    Skill for validating data at various stages of the grading pipeline.

    Example:
        >>> skill = DataValidationSkill()
        >>> result = skill.validate_pdf_input(Path("submission.pdf"))
        >>> if result.is_valid:
        ...     print("PDF is valid")
    """

    def __init__(self):
        """Initialize the data validation skill."""
        self.logger = logging.getLogger(self.__class__.__name__)

        # PDF validation limits
        self.max_pdf_size_mb = 100
        self.min_pdf_size_bytes = 1024  # 1KB

    def validate_pdf_input(self, pdf_path: Path) -> ValidationResult:
        """
        Validate PDF file input.

        Checks:
        - File exists
        - File is a PDF
        - File is not empty
        - File is not too large
        - File is readable

        Args:
            pdf_path: Path to PDF file

        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult(is_valid=True)

        # Check existence
        if not pdf_path.exists():
            return result.add_error(f"PDF file not found: {pdf_path}")

        # Check is file (not directory)
        if not pdf_path.is_file():
            return result.add_error(f"Path is not a file: {pdf_path}")

        # Check extension
        if pdf_path.suffix.lower() != '.pdf':
            result.add_warning(f"File extension is '{pdf_path.suffix}', expected '.pdf'")

        # Check file size
        file_size = pdf_path.stat().st_size

        if file_size < self.min_pdf_size_bytes:
            return result.add_error(f"PDF file is too small ({file_size} bytes), may be empty")

        max_size_bytes = self.max_pdf_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            result.add_warning(
                f"PDF file is large ({file_size / 1024 / 1024:.1f}MB), processing may be slow"
            )

        # Check readable
        try:
            with open(pdf_path, 'rb') as f:
                # Read first few bytes to check if it's a PDF
                header = f.read(8)
                if not header.startswith(b'%PDF'):
                    return result.add_error("File does not appear to be a valid PDF")
        except Exception as e:
            return result.add_error(f"Cannot read PDF file: {e}")

        return result

    def validate_self_grade(self, grade: int) -> ValidationResult:
        """
        Validate self-assessed grade.

        Checks:
        - Grade is integer
        - Grade is in range 0-100

        Args:
            grade: Self-assessed grade

        Returns:
            ValidationResult with any errors
        """
        result = ValidationResult(is_valid=True)

        # Check type
        if not isinstance(grade, int):
            return result.add_error(f"Grade must be an integer, got {type(grade).__name__}")

        # Check range
        if not 0 <= grade <= 100:
            return result.add_error(f"Grade must be between 0 and 100, got {grade}")

        # Warnings for unusual grades
        if grade == 100:
            result.add_warning("Self-grade is 100 (perfect) - very strict evaluation will be applied")
        elif grade < 50:
            result.add_warning("Self-grade is below 50 - consider providing improvement context")

        return result

    def validate_grading_request(self, request: GradingRequest) -> ValidationResult:
        """
        Validate complete grading request.

        Args:
            request: Grading request to validate

        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult(is_valid=True)

        # Validate PDF
        pdf_result = self.validate_pdf_input(request.pdf_path)
        result.errors.extend(pdf_result.errors)
        result.warnings.extend(pdf_result.warnings)

        if pdf_result.errors:
            result.is_valid = False

        # Validate self-grade
        grade_result = self.validate_self_grade(request.self_grade)
        result.errors.extend(grade_result.errors)
        result.warnings.extend(grade_result.warnings)

        if grade_result.errors:
            result.is_valid = False

        return result

    def validate_evaluation(self, evaluation: CriterionEvaluation) -> ValidationResult:
        """
        Validate a criterion evaluation.

        Checks:
        - Score is in range 0-100
        - Weight is in range 0-1
        - Required fields are present
        - Lists are not empty

        Args:
            evaluation: Criterion evaluation to validate

        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult(is_valid=True)

        # Check score range
        if not 0.0 <= evaluation.score <= 100.0:
            result.add_error(f"Score {evaluation.score} is out of range [0, 100]")

        # Check weight range
        if not 0.0 <= evaluation.weight <= 1.0:
            result.add_error(f"Weight {evaluation.weight} is out of range [0, 1]")

        # Check required fields
        if not evaluation.criterion_id:
            result.add_error("Criterion ID is empty")

        if not evaluation.criterion_name:
            result.add_error("Criterion name is empty")

        # Check severity
        valid_severities = ['critical', 'important', 'minor', 'strength']
        if evaluation.severity not in valid_severities:
            result.add_error(
                f"Invalid severity '{evaluation.severity}', must be one of {valid_severities}"
            )

        # Warnings for empty lists
        if not evaluation.evidence:
            result.add_warning(f"No evidence provided for {evaluation.criterion_id}")

        if not evaluation.strengths and not evaluation.weaknesses:
            result.add_warning(f"No strengths or weaknesses provided for {evaluation.criterion_id}")

        if not evaluation.suggestions:
            result.add_warning(f"No suggestions provided for {evaluation.criterion_id}")

        return result

    def validate_evaluations_complete(
        self,
        evaluations: List[CriterionEvaluation],
        expected_criteria: List[str]
    ) -> ValidationResult:
        """
        Validate that all expected criteria have been evaluated.

        Args:
            evaluations: List of evaluations
            expected_criteria: List of expected criterion IDs

        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult(is_valid=True)

        evaluated_criteria = {eval.criterion_id for eval in evaluations}
        expected_set = set(expected_criteria)

        # Check for missing criteria
        missing = expected_set - evaluated_criteria
        if missing:
            result.add_error(f"Missing evaluations for criteria: {sorted(missing)}")

        # Check for unexpected criteria
        unexpected = evaluated_criteria - expected_set
        if unexpected:
            result.add_warning(f"Unexpected evaluations for criteria: {sorted(unexpected)}")

        # Check for duplicates
        criterion_ids = [eval.criterion_id for eval in evaluations]
        duplicates = {cid for cid in criterion_ids if criterion_ids.count(cid) > 1}
        if duplicates:
            result.add_error(f"Duplicate evaluations for criteria: {sorted(duplicates)}")

        return result

    def validate_weights_sum_to_one(
        self,
        evaluations: List[CriterionEvaluation],
        tolerance: float = 0.05
    ) -> ValidationResult:
        """
        Validate that criterion weights sum to approximately 1.0.

        Args:
            evaluations: List of evaluations
            tolerance: Acceptable deviation from 1.0 (default: 0.05)

        Returns:
            ValidationResult with any errors/warnings
        """
        result = ValidationResult(is_valid=True)

        total_weight = sum(eval.weight for eval in evaluations)

        if abs(total_weight - 1.0) > tolerance:
            result.add_error(
                f"Criterion weights sum to {total_weight:.4f}, expected ~1.0 (±{tolerance})"
            )

        return result

    def sanitize_text(self, text: str) -> str:
        """
        Sanitize text by removing dangerous characters.

        Args:
            text: Text to sanitize

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove null bytes
        text = text.replace('\x00', '')

        # Remove other control characters (except newlines, tabs)
        text = ''.join(char for char in text if char == '\n' or char == '\t' or ord(char) >= 32)

        return text

    def validate_api_key(self, api_key: str) -> ValidationResult:
        """
        Validate API key format.

        Args:
            api_key: API key to validate

        Returns:
            ValidationResult with any errors
        """
        result = ValidationResult(is_valid=True)

        if not api_key:
            return result.add_error("API key is empty")

        if len(api_key) < 20:
            result.add_warning("API key seems too short, may be invalid")

        if ' ' in api_key:
            return result.add_error("API key contains spaces, may be malformed")

        return result
