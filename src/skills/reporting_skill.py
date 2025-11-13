"""
Reporting skill for generating grading reports in multiple formats.

This skill provides functionality to render reports using Jinja2 templates
and convert between formats (Markdown, PDF, JSON).
"""

from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import logging

try:
    from jinja2 import Environment, FileSystemLoader, Template
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

from models.core import GradingResult


class ReportingSkill:
    """
    Skill for generating grading reports.

    Uses Jinja2 templates for Markdown generation and can convert to PDF.

    Example:
        >>> skill = ReportingSkill(template_dir="templates")
        >>> markdown = skill.render_markdown_report(grading_result)
        >>> print(markdown)
    """

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize the reporting skill.

        Args:
            template_dir: Directory containing Jinja2 templates

        Raises:
            RuntimeError: If jinja2 is not installed
        """
        if not JINJA2_AVAILABLE:
            raise RuntimeError("jinja2 library not installed. Run: pip install jinja2")

        self.template_dir = Path(template_dir or "templates")
        self.logger = logging.getLogger(self.__class__.__name__)

        # Initialize Jinja2 environment
        if self.template_dir.exists():
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                trim_blocks=True,
                lstrip_blocks=True
            )
        else:
            self.env = None
            self.logger.warning(f"Template directory not found: {self.template_dir}")

    def render_markdown_report(
        self,
        result: GradingResult,
        template_name: str = "grading_report.md.jinja"
    ) -> str:
        """
        Render Markdown report from grading result.

        Args:
            result: Grading result to render
            template_name: Name of Jinja2 template

        Returns:
            Rendered Markdown report

        Raises:
            FileNotFoundError: If template not found
        """
        # If template exists, use it
        if self.env:
            try:
                template = self.env.get_template(template_name)
                return template.render(
                    result=result,
                    generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                )
            except Exception as e:
                self.logger.warning(f"Template rendering failed: {e}, using fallback")

        # Fallback: Generate basic report
        return self._generate_basic_markdown_report(result)

    def _generate_basic_markdown_report(self, result: GradingResult) -> str:
        """
        Generate a basic Markdown report without templates.

        Args:
            result: Grading result

        Returns:
            Markdown report string
        """
        lines = []

        # Title
        lines.append(f"# Grading Report: {result.submission_id}")
        lines.append("")

        # Summary
        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Self-Assessed Grade:** {result.self_grade}/100")
        lines.append(f"- **Final Grade:** {result.final_score:.2f}/100")
        lines.append(f"- **Difference:** {result.get_grade_difference():+.2f} points")
        lines.append(f"- **Criticism Multiplier:** {result.criticism_multiplier}x")
        lines.append(f"- **Graded At:** {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"- **Processing Time:** {result.processing_time_seconds:.2f} seconds")
        lines.append("")

        # Comparison message
        if result.comparison_message:
            lines.append("## Grade Comparison")
            lines.append("")
            lines.append(result.comparison_message)
            lines.append("")

        # Score Breakdown
        lines.append("## Score Breakdown")
        lines.append("")

        if result.breakdown:
            lines.append("| Category | Weight | Score | Contribution |")
            lines.append("|----------|--------|-------|--------------|")

            for category_name, category in result.breakdown.items():
                contribution = category.weighted_score * category.total_weight
                lines.append(
                    f"| {category_name} | {category.total_weight*100:.1f}% | "
                    f"{category.weighted_score:.1f} | {contribution:.1f} |"
                )

            lines.append("")

        # Detailed Evaluations
        lines.append("## Detailed Evaluation")
        lines.append("")

        for i, evaluation in enumerate(result.evaluations, 1):
            lines.append(f"### {i}. {evaluation.criterion_name}")
            lines.append("")
            lines.append(f"**Score:** {evaluation.score:.1f}/100 | **Weight:** {evaluation.weight*100:.1f}% | **Severity:** {evaluation.severity}")
            lines.append("")

            if evaluation.evidence:
                lines.append("#### Evidence")
                for evidence in evaluation.evidence:
                    lines.append(f"- {evidence}")
                lines.append("")

            if evaluation.strengths:
                lines.append("#### Strengths")
                for strength in evaluation.strengths:
                    lines.append(f"- ✅ {strength}")
                lines.append("")

            if evaluation.weaknesses:
                lines.append("#### Weaknesses")
                for weakness in evaluation.weaknesses:
                    lines.append(f"- ⚠️ {weakness}")
                lines.append("")

            if evaluation.suggestions:
                lines.append("#### Suggestions for Improvement")
                for suggestion in evaluation.suggestions:
                    lines.append(f"- 💡 {suggestion}")
                lines.append("")

        # Footer
        lines.append("---")
        lines.append("")
        lines.append(f"*Report generated by AutoGrader on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")

        return "\n".join(lines)

    def export_to_json(self, result: GradingResult) -> str:
        """
        Export grading result to JSON.

        Args:
            result: Grading result

        Returns:
            JSON string
        """
        return result.model_dump_json(indent=2)

    def export_to_csv_row(self, result: GradingResult) -> str:
        """
        Export grading result as CSV row for batch processing.

        Args:
            result: Grading result

        Returns:
            CSV row string (comma-separated)
        """
        fields = [
            result.submission_id,
            str(result.self_grade),
            f"{result.final_score:.2f}",
            f"{result.get_grade_difference():+.2f}",
            f"{result.criticism_multiplier}",
            str(len(result.evaluations)),
            result.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            f"{result.processing_time_seconds:.2f}"
        ]

        # Escape commas in fields
        fields = [f'"{field}"' if ',' in str(field) else str(field) for field in fields]

        return ",".join(fields)

    def get_csv_header(self) -> str:
        """
        Get CSV header row.

        Returns:
            CSV header string
        """
        return "submission_id,self_grade,final_score,difference,criticism_multiplier,num_evaluations,timestamp,processing_time_seconds"

    def convert_markdown_to_pdf(self, markdown: str) -> bytes:
        """
        Convert Markdown to PDF (placeholder).

        This is a placeholder method. For actual PDF generation, consider using:
        - markdown-pdf library
        - weasyprint
        - pandoc (via subprocess)

        Args:
            markdown: Markdown content

        Returns:
            PDF bytes

        Raises:
            NotImplementedError: Always (not yet implemented)
        """
        raise NotImplementedError(
            "PDF conversion not yet implemented. "
            "Consider using markdown-pdf or weasyprint library."
        )

    def create_template(self, template_name: str, content: str) -> None:
        """
        Create a new Jinja2 template file.

        Args:
            template_name: Name of the template file
            content: Template content

        Raises:
            IOError: If template can't be written
        """
        self.template_dir.mkdir(parents=True, exist_ok=True)
        template_path = self.template_dir / template_name

        try:
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(content)
            self.logger.info(f"Created template: {template_path}")
        except Exception as e:
            self.logger.error(f"Failed to create template: {e}")
            raise IOError(f"Failed to create template: {e}") from e
