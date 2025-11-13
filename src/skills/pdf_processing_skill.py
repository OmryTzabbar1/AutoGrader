"""
PDF processing skill for extracting structured content from PDFs.

This skill provides functionality to parse PDFs and extract text, code blocks,
diagrams, and document structure using PyMuPDF (primary) and pdfplumber (fallback).
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
import re

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

from models.core import (
    ParsedDocument,
    CodeBlock,
    Diagram,
    Section,
    DocumentStructure,
)


class PDFParsingError(Exception):
    """Raised when PDF parsing fails."""
    pass


class PDFProcessingSkill:
    """
    Skill for parsing and extracting content from PDFs.

    This skill uses PyMuPDF as the primary parser (fast and accurate) with
    pdfplumber as a fallback for complex layouts.

    Features:
    - Text extraction with page tracking
    - Code block detection using heuristics
    - Document structure extraction (headings, sections)
    - Fallback parser support

    Example:
        >>> skill = PDFProcessingSkill()
        >>> document = skill.parse_pdf(Path("submission.pdf"))
        >>> print(document.total_pages)
        25
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the PDF processing skill.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # Check available parsers
        if not PYMUPDF_AVAILABLE and not PDFPLUMBER_AVAILABLE:
            raise RuntimeError(
                "No PDF parser available. Install PyMuPDF or pdfplumber."
            )

    def parse_pdf(
        self,
        pdf_path: Path,
        engine: str = "pymupdf"
    ) -> ParsedDocument:
        """
        Parse a PDF file and extract structured content.

        Args:
            pdf_path: Path to PDF file
            engine: Parser engine ('pymupdf' or 'pdfplumber')

        Returns:
            ParsedDocument with extracted content

        Raises:
            PDFParsingError: If parsing fails with all available engines
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If engine is invalid
        """
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        if pdf_path.suffix.lower() != '.pdf':
            raise ValueError(f"File must be a PDF, got {pdf_path.suffix}")

        # Validate file is not corrupted
        if pdf_path.stat().st_size == 0:
            raise PDFParsingError(f"PDF file is empty: {pdf_path}")

        if pdf_path.stat().st_size > 100 * 1024 * 1024:  # 100MB
            self.logger.warning(f"Large PDF file: {pdf_path.stat().st_size / 1024 / 1024:.1f}MB")

        # Try requested engine
        if engine == "pymupdf" and PYMUPDF_AVAILABLE:
            try:
                return self._parse_with_pymupdf(pdf_path)
            except Exception as e:
                self.logger.warning(f"PyMuPDF failed: {e}")
                if PDFPLUMBER_AVAILABLE:
                    self.logger.info("Trying fallback parser (pdfplumber)")
                    return self._parse_with_pdfplumber(pdf_path)
                raise PDFParsingError(f"Failed to parse PDF: {e}") from e

        elif engine == "pdfplumber" and PDFPLUMBER_AVAILABLE:
            try:
                return self._parse_with_pdfplumber(pdf_path)
            except Exception as e:
                self.logger.warning(f"pdfplumber failed: {e}")
                if PYMUPDF_AVAILABLE:
                    self.logger.info("Trying fallback parser (PyMuPDF)")
                    return self._parse_with_pymupdf(pdf_path)
                raise PDFParsingError(f"Failed to parse PDF: {e}") from e

        else:
            raise ValueError(f"Unknown or unavailable engine: {engine}")

    def _parse_with_pymupdf(self, pdf_path: Path) -> ParsedDocument:
        """
        Parse PDF using PyMuPDF (fast and accurate).

        Args:
            pdf_path: Path to PDF file

        Returns:
            ParsedDocument with extracted content
        """
        doc = fitz.open(pdf_path)

        try:
            # Extract text content by page
            text_content = {}
            for page_num in range(len(doc)):
                page = doc[page_num]
                text_content[page_num + 1] = page.get_text()

            # Detect code blocks
            code_blocks = self._detect_code_blocks(text_content)

            # Extract document structure
            structure = self._extract_structure_pymupdf(doc)

            # Extract diagrams (if enabled)
            diagrams = []
            if self.config.get("extract_images", False):
                diagrams = self._extract_diagrams_pymupdf(doc)

            return ParsedDocument(
                file_path=pdf_path,
                total_pages=len(doc),
                text_content=text_content,
                code_blocks=code_blocks,
                diagrams=diagrams,
                structure=structure,
                metadata={
                    "parser": "pymupdf",
                    "file_size_mb": pdf_path.stat().st_size / 1024 / 1024
                }
            )

        finally:
            doc.close()

    def _parse_with_pdfplumber(self, pdf_path: Path) -> ParsedDocument:
        """
        Parse PDF using pdfplumber (good for complex layouts).

        Args:
            pdf_path: Path to PDF file

        Returns:
            ParsedDocument with extracted content
        """
        with pdfplumber.open(pdf_path) as pdf:
            # Extract text content by page
            text_content = {}
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                text_content[page_num] = text

            # Detect code blocks
            code_blocks = self._detect_code_blocks(text_content)

            # Extract document structure
            structure = self._extract_structure_pdfplumber(pdf)

            return ParsedDocument(
                file_path=pdf_path,
                total_pages=len(pdf.pages),
                text_content=text_content,
                code_blocks=code_blocks,
                diagrams=[],
                structure=structure,
                metadata={
                    "parser": "pdfplumber",
                    "file_size_mb": pdf_path.stat().st_size / 1024 / 1024
                }
            )

    def _detect_code_blocks(
        self,
        text_content: Dict[int, str]
    ) -> List[CodeBlock]:
        """
        Detect code blocks in extracted text using heuristics.

        Code blocks are identified by:
        - Indentation patterns
        - Common programming keywords
        - Special characters (braces, semicolons, operators)
        - Monospace font indicators (from PDF)

        Args:
            text_content: Dictionary mapping page numbers to text

        Returns:
            List of detected code blocks
        """
        code_blocks = []
        code_indicators = [
            # Python
            'def ', 'class ', 'import ', 'from ', 'return ', '__init__',
            # Java/C++/JavaScript
            'public ', 'private ', 'void ', 'int ', 'String ',
            'const ', 'let ', 'var ', 'function ',
            # Common
            'if (', 'for (', 'while (', 'switch (', '=>',
        ]

        for page_num, text in text_content.items():
            lines = text.split('\n')
            current_block = []
            in_code_block = False
            block_start_line = 0

            for i, line in enumerate(lines):
                # Check if line looks like code
                is_code_line = (
                    self._looks_like_code(line, code_indicators) or
                    (in_code_block and line.strip() and
                     (line.startswith('    ') or line.startswith('\t')))
                )

                if is_code_line and not in_code_block:
                    # Start of new code block
                    in_code_block = True
                    block_start_line = i
                    current_block = [line]

                elif is_code_line and in_code_block:
                    # Continue code block
                    current_block.append(line)

                elif not is_code_line and in_code_block:
                    # Check if it's just an empty line (continue block)
                    if not line.strip() and len(current_block) > 0:
                        current_block.append(line)
                    else:
                        # End of code block
                        if len(current_block) >= 3:  # Minimum 3 lines
                            code_blocks.append(CodeBlock(
                                content='\n'.join(current_block),
                                page_number=page_num,
                                line_count=len(current_block),
                                language=None,  # Will be detected later
                                start_line=block_start_line
                            ))
                        current_block = []
                        in_code_block = False

            # Handle code block at end of page
            if in_code_block and len(current_block) >= 3:
                code_blocks.append(CodeBlock(
                    content='\n'.join(current_block),
                    page_number=page_num,
                    line_count=len(current_block),
                    language=None,
                    start_line=block_start_line
                ))

        return code_blocks

    def _looks_like_code(self, line: str, indicators: List[str]) -> bool:
        """
        Heuristic to determine if a line looks like code.

        Args:
            line: Line of text to check
            indicators: List of code indicator keywords

        Returns:
            True if line looks like code, False otherwise
        """
        if not line.strip():
            return False

        # Check for code indicators
        if any(indicator in line for indicator in indicators):
            return True

        # Check for typical code patterns
        code_patterns = [
            r'^\s{4,}',  # Significant indentation
            r'[{}();]',  # Braces, parentheses, semicolons
            r'[=!<>]=',  # Comparison operators
            r'\w+\(',    # Function calls
            r'->\s*\w+',  # Arrow operators
            r'//|/\*|\*/',  # Comments
            r'#\s*\w+',   # Python comments or directives
        ]

        return any(re.search(pattern, line) for pattern in code_patterns)

    def _extract_structure_pymupdf(self, doc) -> DocumentStructure:
        """
        Extract document structure (sections, headings) using PyMuPDF.

        Args:
            doc: PyMuPDF document object

        Returns:
            DocumentStructure with sections
        """
        sections = []

        # Try to extract table of contents
        toc = doc.get_toc()
        has_toc = len(toc) > 0

        if has_toc:
            # Use TOC for structure
            for level, title, page in toc:
                sections.append(Section(
                    title=title,
                    level=level,
                    page_number=page,
                    content_preview=None
                ))
        else:
            # Extract headings using font size heuristics
            for page_num in range(len(doc)):
                page = doc[page_num]
                blocks = page.get_text("dict")["blocks"]

                for block in blocks:
                    if "lines" in block:
                        for line in block["lines"]:
                            for span in line["spans"]:
                                text = span["text"].strip()
                                font_size = span["size"]

                                # Consider large text as headings
                                if font_size > 14 and len(text) > 0:
                                    # Estimate heading level based on font size
                                    if font_size >= 20:
                                        level = 1
                                    elif font_size >= 16:
                                        level = 2
                                    else:
                                        level = 3

                                    sections.append(Section(
                                        title=text,
                                        level=level,
                                        page_number=page_num + 1,
                                        content_preview=None
                                    ))

        return DocumentStructure(
            sections=sections,
            has_toc=has_toc,
            total_sections=len(sections)
        )

    def _extract_structure_pdfplumber(self, pdf) -> DocumentStructure:
        """
        Extract document structure using pdfplumber.

        Args:
            pdf: pdfplumber PDF object

        Returns:
            DocumentStructure with sections
        """
        sections = []

        # Simple heuristic: lines that are short and capitalized
        for page_num, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            lines = text.split('\n')

            for line in lines:
                line = line.strip()
                # Heuristic for headings
                if (len(line) < 100 and len(line) > 5 and
                    (line.isupper() or line[0].isupper())):
                    sections.append(Section(
                        title=line,
                        level=1 if line.isupper() else 2,
                        page_number=page_num,
                        content_preview=None
                    ))

        return DocumentStructure(
            sections=sections,
            has_toc=False,
            total_sections=len(sections)
        )

    def _extract_diagrams_pymupdf(self, doc) -> List[Diagram]:
        """
        Extract diagrams and images from PDF.

        Args:
            doc: PyMuPDF document object

        Returns:
            List of extracted diagrams
        """
        diagrams = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images()

            for img_index, img in enumerate(image_list):
                xref = img[0]
                diagrams.append(Diagram(
                    image_data=f"xref:{xref}",  # Reference to image
                    page_number=page_num + 1,
                    caption=None,
                    image_type=None
                ))

        return diagrams
