# AutoGrader CLI Usage Guide

Command-line interface for the AutoGrader system.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API key
export CLAUDE_API_KEY=your-api-key-here
```

## Commands

### Grade Single Submission

Grade a single PDF submission:

```bash
python autograder.py grade submission.pdf --self-grade 85
```

Options:
- `--self-grade, -s`: Student's self-assessed grade (0-100) **[Required]**
- `--output-dir, -o`: Output directory for reports (default: workspace/outputs)
- `--formats, -f`: Output formats - can specify multiple (markdown, json, csv)
- `--verbose, -v`: Show detailed output and criterion evaluations

Examples:
```bash
# Basic grading
python autograder.py grade project.pdf -s 90

# With multiple output formats
python autograder.py grade submission.pdf -s 85 -f markdown -f json -f csv

# Verbose output with all details
python autograder.py grade project.pdf -s 88 -v

# Custom output directory
python autograder.py grade submission.pdf -s 92 -o ./my_reports
```

### Batch Processing

Grade multiple submissions at once:

```bash
python autograder.py batch ./submissions --manifest manifest.json
```

The manifest file should be a JSON array with submission metadata:

```json
[
  {"pdf": "student1_project.pdf", "self_grade": 85},
  {"pdf": "student2_project.pdf", "self_grade": 90},
  {"pdf": "student3_project.pdf", "self_grade": 78}
]
```

Options:
- `--manifest, -m`: Path to manifest JSON file (default: submissions_dir/manifest.json)
- `--output-dir, -o`: Output directory for reports
- `--formats, -f`: Output formats (default: markdown, csv)
- `--verbose, -v`: Verbose output

Examples:
```bash
# Basic batch processing
python autograder.py batch ./submissions -m manifest.json

# With JSON output
python autograder.py batch ./all_projects -m students.json -f json

# Verbose mode
python autograder.py batch ./submissions -v
```

### Validate Submission

Validate a PDF without grading:

```bash
python autograder.py validate submission.pdf --self-grade 85
```

This checks if the PDF is readable and meets basic requirements before running the full grading process.

Options:
- `--self-grade, -s`: Optional self-grade to validate

Examples:
```bash
# Validate PDF only
python autograder.py validate project.pdf

# Validate with self-grade check
python autograder.py validate submission.pdf -s 95
```

### Configuration

View or manage configuration:

```bash
# Show all configuration
python autograder.py config --show

# Show specific configuration value
python autograder.py config --key llm.model

# Show usage and environment variable info
python autograder.py config
```

## Output

### Terminal Output

The CLI provides rich terminal output with:
- ✓ Success messages in green
- ✗ Error messages in red
- ⚠ Warning messages in yellow
- ℹ Info messages in blue
- Progress bars for batch processing
- Formatted tables for results

### Grading Summary

After grading, you'll see:

```
──────────────────────────────────────────────────────────
Grading Summary
──────────────────────────────────────────────────────────

Submission ID:  project_20250113_143022
Self-Grade:     85
Final Score:    82.50
Difference:     -2.50
Processing:     45.23s

Your self-assessment was quite accurate. The final grade is
very close to your self-assessment. Your self-evaluation
was well-calibrated.

──────────────────────────────────────────────────────────
Category Breakdown
──────────────────────────────────────────────────────────

Category                  | Weight | Score
──────────────────────────────────────────
Documentation             | 0.20   | 88.50
Code Quality              | 0.25   | 85.20
Configuration & Security  | 0.10   | 80.00
Testing                   | 0.20   | 78.50
Research & Analysis       | 0.15   | 82.00
UI/UX                     | 0.05   | 75.00
Version Control           | 0.05   | 90.00
```

### Generated Files

Reports are saved to the output directory:

```
workspace/outputs/
├── project_20250113_143022_report.md    # Markdown report
├── project_20250113_143022_result.json  # JSON export
└── batch_results.csv                     # CSV (for batch mode)
```

## Environment Variables

Override configuration with environment variables:

```bash
# LLM configuration
export AUTOGRADER_LLM__API_KEY=your-api-key
export AUTOGRADER_LLM__MODEL=claude-sonnet-4-20250514
export AUTOGRADER_LLM__MAX_TOKENS=4096
export AUTOGRADER_LLM__TEMPERATURE=0.0

# Parser configuration
export AUTOGRADER_PARSER__ENGINE=pymupdf
export AUTOGRADER_PARSER__CACHE_ENABLED=true

# Output configuration
export AUTOGRADER_REPORTING__OUTPUT_DIR=./custom_outputs
```

Note: Use double underscores (`__`) to specify nested keys.

## Error Handling

Common errors and solutions:

### API Key Not Set
```
Error: CLAUDE_API_KEY environment variable not set
```
Solution: `export CLAUDE_API_KEY=your-key`

### PDF Not Found
```
Error: PDF file not found: submission.pdf
```
Solution: Check the file path is correct

### Invalid Self-Grade
```
Error: Invalid value for '--self-grade': 105 is not in the range 0<=x<=100
```
Solution: Self-grade must be between 0 and 100

### Parsing Failed
```
Error: Failed to parse PDF: [details]
```
Solution: Check if PDF is corrupted or encrypted

## Tips

1. **Use validation first**: Run `validate` before `grade` to catch issues early
2. **Start with single submissions**: Test with one submission before batch processing
3. **Check cost estimates**: Monitor API costs in the output
4. **Use verbose mode**: Add `-v` flag when debugging issues
5. **Organize outputs**: Use `--output-dir` to keep reports organized by batch

## Getting Help

```bash
# General help
python autograder.py --help

# Command-specific help
python autograder.py grade --help
python autograder.py batch --help
python autograder.py validate --help
python autograder.py config --help

# Version info
python autograder.py --version
```
