"""
Core data models for the AutoGrader system.

This module defines the primary data structures used throughout the system,
including parsed documents, evaluation results, and grading outputs.
"""

from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel, Field, field_validator


class CodeBlock(BaseModel):
    """
    Represents a code block extracted from a PDF.

    Attributes:
        content: The source code content
        page_number: Page number where the code block appears
        line_count: Number of lines in the code block
        language: Detected programming language (e.g., "python", "java")
        start_line: Starting line number in the PDF (if available)
    """

    content: str = Field(..., description="Source code content")
    page_number: int = Field(..., ge=1, description="Page number")
    line_count: int = Field(..., ge=1, description="Number of lines")
    language: Optional[str] = Field(None, description="Programming language")
    start_line: Optional[int] = Field(None, description="Starting line number")

    class Config:
        frozen = False  # Allow modifications for language detection


class Diagram(BaseModel):
    """
    Represents a diagram or image extracted from a PDF.

    Attributes:
        image_data: Base64-encoded image data or file path
        page_number: Page number where the diagram appears
        caption: Diagram caption (if available)
        image_type: Type of image (e.g., "architecture", "flowchart", "screenshot")
    """

    image_data: str = Field(..., description="Image data or path")
    page_number: int = Field(..., ge=1, description="Page number")
    caption: Optional[str] = Field(None, description="Diagram caption")
    image_type: Optional[str] = Field(None, description="Type of diagram")


class Section(BaseModel):
    """
    Represents a document section with heading hierarchy.

    Attributes:
        title: Section title/heading
        level: Heading level (1=h1, 2=h2, etc.)
        page_number: Page number where section starts
        content_preview: First few lines of section content
    """

    title: str = Field(..., description="Section title")
    level: int = Field(..., ge=1, le=6, description="Heading level")
    page_number: int = Field(..., ge=1, description="Page number")
    content_preview: Optional[str] = Field(None, description="Content preview")


class DocumentStructure(BaseModel):
    """
    Represents the hierarchical structure of a document.

    Attributes:
        sections: List of document sections
        has_toc: Whether document has a table of contents
        total_sections: Total number of sections
    """

    sections: List[Section] = Field(default_factory=list, description="Document sections")
    has_toc: bool = Field(False, description="Has table of contents")
    total_sections: int = Field(0, description="Total sections")

    def get_section_by_title(self, title: str) -> Optional[Section]:
        """Find a section by title (case-insensitive)."""
        title_lower = title.lower()
        for section in self.sections:
            if title_lower in section.title.lower():
                return section
        return None


class ParsedDocument(BaseModel):
    """
    Represents a fully parsed PDF document.

    This is the output of the ParserAgent and input to EvaluatorAgents.

    Attributes:
        file_path: Path to the original PDF file
        total_pages: Total number of pages
        text_content: Dictionary mapping page numbers to extracted text
        code_blocks: List of detected code blocks
        diagrams: List of extracted diagrams
        structure: Document structure (sections, headings)
        metadata: Additional metadata (file size, parsing time, etc.)
    """

    file_path: Path = Field(..., description="Path to PDF file")
    total_pages: int = Field(..., ge=1, description="Total pages")
    text_content: Dict[int, str] = Field(default_factory=dict, description="Page text")
    code_blocks: List[CodeBlock] = Field(default_factory=list, description="Code blocks")
    diagrams: List[Diagram] = Field(default_factory=list, description="Diagrams")
    structure: DocumentStructure = Field(default_factory=DocumentStructure, description="Document structure")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    def get_page_text(self, page_number: int) -> Optional[str]:
        """Get text content for a specific page."""
        return self.text_content.get(page_number)

    def get_all_text(self) -> str:
        """Get all text content concatenated."""
        return "\n\n".join(
            f"=== Page {page} ===\n{text}"
            for page, text in sorted(self.text_content.items())
        )

    def search_text(self, keyword: str, case_sensitive: bool = False) -> List[int]:
        """
        Search for a keyword across all pages.

        Returns:
            List of page numbers where keyword appears
        """
        pages = []
        keyword_search = keyword if case_sensitive else keyword.lower()

        for page_num, text in self.text_content.items():
            text_search = text if case_sensitive else text.lower()
            if keyword_search in text_search:
                pages.append(page_num)

        return pages


class CriterionEvaluation(BaseModel):
    """
    Represents the evaluation result for a single criterion.

    This is the output of an EvaluatorAgent.

    Attributes:
        criterion_id: Unique identifier for the criterion (e.g., "prd_quality")
        criterion_name: Human-readable name (e.g., "PRD Quality")
        weight: Weight of this criterion in final score (0.0 to 1.0)
        score: Score for this criterion (0.0 to 100.0)
        evidence: List of evidence from the submission
        strengths: List of identified strengths
        weaknesses: List of identified weaknesses
        suggestions: List of improvement suggestions
        severity: Severity level of issues found
    """

    criterion_id: str = Field(..., description="Criterion identifier")
    criterion_name: str = Field(..., description="Criterion name")
    weight: float = Field(..., ge=0.0, le=1.0, description="Criterion weight")
    score: float = Field(..., ge=0.0, le=100.0, description="Score")
    evidence: List[str] = Field(default_factory=list, description="Evidence")
    strengths: List[str] = Field(default_factory=list, description="Strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Weaknesses")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions")
    severity: Literal["critical", "important", "minor", "strength"] = Field(
        ..., description="Issue severity"
    )

    @field_validator('score')
    @classmethod
    def validate_score(cls, v: float) -> float:
        """Ensure score is within valid range."""
        if not 0.0 <= v <= 100.0:
            raise ValueError(f"Score must be between 0 and 100, got {v}")
        return round(v, 2)

    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v: float) -> float:
        """Ensure weight is within valid range."""
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"Weight must be between 0 and 1, got {v}")
        return round(v, 4)


class CategoryBreakdown(BaseModel):
    """
    Represents the score breakdown for a category of criteria.

    Attributes:
        category_name: Name of the category (e.g., "Documentation")
        total_weight: Total weight of all criteria in this category
        weighted_score: Weighted average score for this category
        criteria: List of criterion evaluations in this category
    """

    category_name: str = Field(..., description="Category name")
    total_weight: float = Field(..., ge=0.0, le=1.0, description="Total weight")
    weighted_score: float = Field(..., ge=0.0, le=100.0, description="Weighted score")
    criteria: List[CriterionEvaluation] = Field(default_factory=list, description="Criteria")


class GradingResult(BaseModel):
    """
    Represents the complete grading result for a submission.

    This is the output of the ScoringAgent and input to the ReporterAgent.

    Attributes:
        submission_id: Unique identifier for the submission
        self_grade: Student's self-assessed grade (0-100)
        final_score: Final calculated grade (0-100)
        criticism_multiplier: Applied criticism multiplier
        evaluations: List of all criterion evaluations
        breakdown: Category-level breakdown
        comparison_message: Message comparing final score to self-grade
        timestamp: When the grading was performed
        processing_time_seconds: Total processing time
    """

    submission_id: str = Field(..., description="Submission identifier")
    self_grade: int = Field(..., ge=0, le=100, description="Self-assessed grade")
    final_score: float = Field(..., ge=0.0, le=100.0, description="Final score")
    criticism_multiplier: float = Field(..., gt=0.0, description="Criticism multiplier")
    evaluations: List[CriterionEvaluation] = Field(default_factory=list, description="Evaluations")
    breakdown: Dict[str, CategoryBreakdown] = Field(default_factory=dict, description="Category breakdown")
    comparison_message: str = Field("", description="Comparison to self-grade")
    timestamp: datetime = Field(default_factory=datetime.now, description="Grading timestamp")
    processing_time_seconds: float = Field(0.0, description="Processing time")

    @field_validator('final_score')
    @classmethod
    def validate_final_score(cls, v: float) -> float:
        """Ensure final score is within valid range."""
        if not 0.0 <= v <= 100.0:
            raise ValueError(f"Final score must be between 0 and 100, got {v}")
        return round(v, 2)

    def get_grade_difference(self) -> float:
        """Calculate difference between final score and self-grade."""
        return round(self.final_score - self.self_grade, 2)

    def get_evaluation_by_id(self, criterion_id: str) -> Optional[CriterionEvaluation]:
        """Find an evaluation by criterion ID."""
        for evaluation in self.evaluations:
            if evaluation.criterion_id == criterion_id:
                return evaluation
        return None


class GradingRequest(BaseModel):
    """
    Represents a request to grade a submission.

    This is the input to the OrchestratorAgent.

    Attributes:
        pdf_path: Path to the PDF submission file
        self_grade: Student's self-assessed grade (0-100)
        submission_id: Optional submission identifier (generated if not provided)
        config_overrides: Optional configuration overrides
    """

    pdf_path: Path = Field(..., description="Path to PDF file")
    self_grade: int = Field(..., ge=0, le=100, description="Self-assessed grade")
    submission_id: Optional[str] = Field(None, description="Submission ID")
    config_overrides: Dict[str, Any] = Field(default_factory=dict, description="Config overrides")

    @field_validator('pdf_path')
    @classmethod
    def validate_pdf_path(cls, v: Path) -> Path:
        """Ensure PDF path exists and has correct extension."""
        if not v.exists():
            raise ValueError(f"PDF file not found: {v}")
        if v.suffix.lower() != '.pdf':
            raise ValueError(f"File must be a PDF, got {v.suffix}")
        return v

    def model_post_init(self, __context) -> None:
        """Generate submission ID if not provided."""
        if self.submission_id is None:
            # Use filename without extension as submission ID
            self.submission_id = self.pdf_path.stem
