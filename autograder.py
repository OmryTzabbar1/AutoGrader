#!/usr/bin/env python3
"""
AutoGrader - Main entry point.

AI-powered academic project grading system for M.Sc. Computer Science projects.
"""

import sys
from pathlib import Path

# Add src to Python path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

from cli.commands import cli


if __name__ == '__main__':
    cli()
