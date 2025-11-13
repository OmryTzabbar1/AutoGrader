# AutoGrader Examples

This directory contains example files and configurations for testing the AutoGrader system.

## Files

### manifest.json

Example manifest file for batch processing. Contains:
- `pdf`: Path to PDF file (relative to submissions directory)
- `self_grade`: Student's self-assessed grade (0-100)
- `student_id`: Optional student identifier
- `notes`: Optional notes about the submission

### Usage Examples

#### Grade Single Submission

```bash
# From project root
python autograder.py grade examples/sample_submission.pdf --self-grade 85
```

#### Batch Processing

```bash
# Process all submissions in examples directory
python autograder.py batch examples/ --manifest examples/manifest.json
```

## Test Submissions

For testing purposes, you can create sample PDF submissions with the following characteristics:

### Excellent Project (90-100)
- Comprehensive PRD with clear requirements
- Detailed architecture documentation with diagrams
- Well-structured code with good documentation
- High test coverage (>80%)
- Proper error handling and security practices
- Professional README and documentation
- Clean git history with meaningful commits

### Good Project (80-89)
- Complete PRD and architecture docs
- Good code structure and documentation
- Adequate testing (60-80% coverage)
- Basic error handling and security
- Good README with examples
- Regular commits with clear messages

### Adequate Project (70-79)
- Basic PRD and architecture docs
- Reasonable code structure
- Some tests (40-60% coverage)
- Basic error handling
- Minimal README
- Irregular commits

### Needs Improvement (<70)
- Missing or incomplete documentation
- Poor code structure
- Minimal or no tests
- Inadequate error handling
- Missing README or documentation
- Poor git practices

## Creating Test PDFs

You can use any tool to create test PDFs:
1. Export documentation from Google Docs/Word as PDF
2. Use pandoc to convert Markdown to PDF
3. Use LaTeX to generate professional PDFs
4. Print web pages to PDF

Ensure PDFs include:
- Text content (not just images)
- Code blocks (formatted with monospace font)
- Section headings
- Multiple pages
