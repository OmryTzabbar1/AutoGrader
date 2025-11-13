# Workspace Directory

This directory contains temporary files, intermediate results, and outputs from the grading system.

## Structure

```
workspace/
├── inputs/              # Input files and metadata
│   └── *.json          # Grading request JSON files
├── intermediate/        # Intermediate processing results
│   └── evaluations/    # Individual criterion evaluations
│       └── *.json      # Saved evaluation results
└── outputs/            # Final output reports
    ├── *_report.md     # Markdown reports
    ├── *_result.json   # JSON exports
    └── batch_results.csv  # Batch processing CSV
```

## Directory Purpose

### inputs/
Stores input data and metadata for grading requests. Used by the orchestrator to pass data between agents.

### intermediate/
Stores intermediate results from individual agents for:
- Debugging failed evaluations
- Recovery after interruptions
- Performance analysis

### outputs/
Contains final grading reports in various formats:
- **Markdown (.md)**: Human-readable detailed reports
- **JSON (.json)**: Machine-readable structured data
- **CSV (.csv)**: Batch results for spreadsheet analysis

## Cleanup

These directories can be safely cleaned between grading sessions:

```bash
# Clean all workspace files
rm -rf workspace/inputs/* workspace/intermediate/* workspace/outputs/*

# Or selectively clean old files
find workspace -name "*.json" -mtime +7 -delete
```

## Caching

The `.cache/` directory (in project root) stores parsed PDF documents to avoid re-parsing on subsequent runs. Clear it if you update PDF processing logic or to free disk space:

```bash
# Clear PDF cache
rm -rf .cache/parsed_docs/*
```

## .gitignore

This directory is included in `.gitignore` to prevent committing:
- Large output files
- Temporary processing data
- Student submission content
- API response data

Keep workspace contents local and do not commit to version control.
