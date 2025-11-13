"""
Parser agent for extracting structured content from PDF submissions.

This agent parses PDF files and extracts text, code blocks, diagrams,
and document structure.
"""

from pathlib import Path
from typing import Any, Dict
import time

from models.agent_result import AgentResult
from models.core import ParsedDocument
from agents.base_agent import BaseAgent
from skills.pdf_processing_skill import PDFProcessingSkill, PDFParsingError
from skills.code_analysis_skill import CodeAnalysisSkill
from skills.caching_skill import CachingSkill


class ParserAgent(BaseAgent[Path, ParsedDocument]):
    """
    Agent that parses PDF submissions and extracts structured content.

    Features:
    - Parse PDFs with PyMuPDF (primary) or pdfplumber (fallback)
    - Extract text, code blocks, diagrams, structure
    - Detect programming languages in code blocks
    - Cache parsed results for performance

    Example:
        >>> agent = ParserAgent({"engine": "pymupdf", "cache_enabled": True})
        >>> result = await agent.execute(Path("submission.pdf"))
        >>> if result.success:
        ...     print(f"Parsed {result.output.total_pages} pages")
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the parser agent.

        Args:
            config: Agent configuration with keys:
                - engine: Primary parser engine ('pymupdf' or 'pdfplumber')
                - fallback_engine: Backup parser engine
                - cache_enabled: Enable result caching (default: True)
                - extract_images: Extract images/diagrams (default: False)
        """
        super().__init__(config)

        # Initialize skills
        self.pdf_skill = PDFProcessingSkill(config)
        self.code_skill = CodeAnalysisSkill()

        # Initialize cache if enabled
        cache_enabled = self.get_config_value('cache_enabled', default=True)
        if cache_enabled:
            self.cache = CachingSkill(cache_dir=Path(".cache/parsed_docs"))
        else:
            self.cache = None

    async def execute(self, pdf_path: Path) -> AgentResult[ParsedDocument]:
        """
        Parse a PDF file and extract structured content.

        Args:
            pdf_path: Path to PDF file

        Returns:
            AgentResult with ParsedDocument
        """
        self.log_execution_start(
            pdf_path,
            pdf_name=pdf_path.name,
            pdf_size_mb=pdf_path.stat().st_size / 1024 / 1024 if pdf_path.exists() else 0
        )

        start_time = time.time()

        try:
            # Check cache first
            if self.cache:
                cached = self.cache.get(pdf_path)
                if cached:
                    self.logger.info(f"Using cached parsing for {pdf_path.name}")
                    return AgentResult.success_result(
                        output=ParsedDocument(**cached),
                        metadata={"from_cache": True},
                        execution_time=time.time() - start_time
                    )

            # Parse PDF
            engine = self.get_config_value('engine', default='pymupdf')

            try:
                parsed_doc = self.pdf_skill.parse_pdf(pdf_path, engine=engine)
                self.logger.info(
                    f"Successfully parsed {pdf_path.name}",
                    extra={
                        "pages": parsed_doc.total_pages,
                        "code_blocks": len(parsed_doc.code_blocks),
                        "engine": parsed_doc.metadata.get('parser')
                    }
                )

            except PDFParsingError as e:
                # Try fallback engine
                fallback_engine = self.get_config_value('fallback_engine', default='pdfplumber')
                self.logger.warning(
                    f"Primary parser failed, trying fallback: {fallback_engine}"
                )

                try:
                    parsed_doc = self.pdf_skill.parse_pdf(pdf_path, engine=fallback_engine)
                    self.logger.info(f"Fallback parser succeeded for {pdf_path.name}")

                except Exception as fallback_error:
                    self.logger.error(f"All parsers failed for {pdf_path.name}")
                    return AgentResult.failure_result(
                        error=f"Failed to parse PDF: {fallback_error}",
                        metadata={
                            "primary_error": str(e),
                            "fallback_error": str(fallback_error)
                        },
                        execution_time=time.time() - start_time
                    )

            # Enhance code blocks with language detection
            for code_block in parsed_doc.code_blocks:
                if code_block.language is None:
                    detected_lang = self.code_skill.detect_language(code_block.content)
                    code_block.language = detected_lang

            self.logger.debug(
                f"Detected languages in {len(parsed_doc.code_blocks)} code blocks"
            )

            # Cache result
            if self.cache:
                self.cache.set(pdf_path, parsed_doc.model_dump())

            execution_time = time.time() - start_time
            self.log_execution_end(True, execution_time, pages=parsed_doc.total_pages)

            return AgentResult.success_result(
                output=parsed_doc,
                metadata={
                    "from_cache": False,
                    "pages": parsed_doc.total_pages,
                    "code_blocks": len(parsed_doc.code_blocks),
                    "sections": len(parsed_doc.structure.sections),
                    "parser": parsed_doc.metadata.get('parser')
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.log_execution_end(False, execution_time)
            return self.handle_error(e)
