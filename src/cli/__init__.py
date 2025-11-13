"""
CLI module for AutoGrader.

Provides command-line interface for grading submissions, batch processing,
validation, and configuration management.
"""

from cli.commands import cli
from cli.output import output

__all__ = ['cli', 'output']
