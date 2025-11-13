"""
Reporter agent for generating grading reports in multiple formats.

This agent generates comprehensive grading reports in various formats
including Markdown, JSON, and optionally PDF and CSV.
"""

from pathlib import Path
from typing import Any, Dict
import time

from models.agent_result import AgentResult
from models.core import GradingResult
from models.io import ReportOutput
from agents.base_agent import BaseAgent
from skills.reporting_skill import ReportingSkill
from skills.file_operations_skill import FileOperationsSkill


class ReporterAgent(BaseAgent[GradingResult, ReportOutput]):
    """
    Agent that generates comprehensive grading reports.

    Features:
    - Markdown report generation
    - JSON export
    - CSV row export
    - Optional PDF generation
    - Multiple output formats

    Example:
        >>> agent = ReporterAgent({
        ...     "output_dir": "workspace/outputs",
        ...     "formats": ["markdown", "json"]
        ... })
        >>> result = await agent.execute(grading_result)
        >>> print(result.output.paths["markdown"])
        workspace/outputs/submission_report.md
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the reporter agent.

        Args:
            config: Agent configuration with keys:
                - output_dir: Directory for output files (default: workspace/outputs)
                - formats: List of formats to generate (default: ["markdown"])
                - template_dir: Directory containing Jinja2 templates
        """
        super().__init__(config)

        # Initialize skills
        template_dir = self.get_config_value('template_dir', default='templates')
        self.reporting_skill = ReportingSkill(Path(template_dir))
        self.file_ops = FileOperationsSkill()

        # Output configuration
        self.output_dir = Path(self.get_config_value('output_dir', default='workspace/outputs'))
        self.formats = self.get_config_value('formats', default=['markdown'])

    async def execute(self, grading_result: GradingResult) -> AgentResult[ReportOutput]:
        """
        Generate grading reports in requested formats.

        Args:
            grading_result: Complete grading result to report

        Returns:
            AgentResult with ReportOutput containing file paths
        """
        self.log_execution_start(
            grading_result,
            submission_id=grading_result.submission_id,
            final_score=grading_result.final_score,
            formats=self.formats
        )

        start_time = time.time()

        try:
            # Ensure output directory exists
            self.file_ops.ensure_dir(self.output_dir)

            report_paths = {}

            # Generate Markdown report
            if 'markdown' in self.formats:
                md_path = await self._generate_markdown(grading_result)
                report_paths['markdown'] = str(md_path)
                self.logger.info(f"Generated Markdown report: {md_path}")

            # Generate JSON export
            if 'json' in self.formats:
                json_path = await self._generate_json(grading_result)
                report_paths['json'] = str(json_path)
                self.logger.info(f"Generated JSON export: {json_path}")

            # Generate CSV row
            if 'csv' in self.formats:
                csv_path = await self._generate_csv_row(grading_result)
                report_paths['csv'] = str(csv_path)
                self.logger.info(f"Generated CSV row: {csv_path}")

            # Generate PDF (if supported)
            if 'pdf' in self.formats:
                try:
                    pdf_path = await self._generate_pdf(grading_result, report_paths.get('markdown'))
                    report_paths['pdf'] = str(pdf_path)
                    self.logger.info(f"Generated PDF report: {pdf_path}")
                except NotImplementedError:
                    self.logger.warning("PDF generation not yet implemented, skipping")

            execution_time = time.time() - start_time

            output = ReportOutput(
                paths=report_paths,
                generation_time=execution_time
            )

            self.log_execution_end(
                True,
                execution_time,
                formats_generated=len(report_paths)
            )

            return AgentResult.success_result(
                output=output,
                metadata={
                    "formats_generated": list(report_paths.keys()),
                    "total_files": len(report_paths)
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.log_execution_end(False, execution_time)
            return self.handle_error(e)

    async def _generate_markdown(self, result: GradingResult) -> Path:
        """
        Generate Markdown report.

        Args:
            result: Grading result

        Returns:
            Path to generated Markdown file
        """
        # Generate report content
        markdown_content = self.reporting_skill.render_markdown_report(result)

        # Write to file
        filename = f"{result.submission_id}_report.md"
        file_path = self.output_dir / filename
        self.file_ops.write_text(file_path, markdown_content)

        return file_path

    async def _generate_json(self, result: GradingResult) -> Path:
        """
        Generate JSON export.

        Args:
            result: Grading result

        Returns:
            Path to generated JSON file
        """
        # Export to JSON
        json_content = self.reporting_skill.export_to_json(result)

        # Write to file
        filename = f"{result.submission_id}_result.json"
        file_path = self.output_dir / filename
        self.file_ops.write_text(file_path, json_content)

        return file_path

    async def _generate_csv_row(self, result: GradingResult) -> Path:
        """
        Generate CSV row (append to batch results file).

        Args:
            result: Grading result

        Returns:
            Path to CSV file
        """
        # CSV file for batch results
        csv_file = self.output_dir / "batch_results.csv"

        # Write header if file doesn't exist
        if not self.file_ops.file_exists(csv_file):
            header = self.reporting_skill.get_csv_header()
            self.file_ops.write_text(csv_file, header + "\n")

        # Append CSV row
        csv_row = self.reporting_skill.export_to_csv_row(result)
        self.file_ops.append_text(csv_file, csv_row + "\n")

        return csv_file

    async def _generate_pdf(
        self,
        result: GradingResult,
        markdown_path: str = None
    ) -> Path:
        """
        Generate PDF report.

        Args:
            result: Grading result
            markdown_path: Path to Markdown file (if available)

        Returns:
            Path to generated PDF file

        Raises:
            NotImplementedError: PDF generation not yet implemented
        """
        # This would require markdown-pdf or weasyprint
        raise NotImplementedError("PDF generation not yet implemented")
