"""
Workspace management utilities for the AutoGrader system.

This module provides functionality to manage the workspace directory structure
used for agent communication and file exchange.
"""

from pathlib import Path
from typing import Optional
import shutil
import logging


class WorkspaceManager:
    """
    Manages the workspace directory structure for agent communication.

    The workspace is organized as:
    workspace/
    ├── inputs/         # User-provided inputs (PDFs, requests)
    ├── intermediate/   # Agent-to-agent data exchange
    │   └── evaluations/ # Evaluation results per criterion
    └── outputs/        # Final deliverables (reports, results)

    Example:
        >>> workspace = WorkspaceManager()
        >>> workspace.initialize()
        >>> parsed_doc_path = workspace.get_intermediate_path("parsed_document.json")
        >>> evaluation_path = workspace.get_evaluation_path("prd_quality.json")
    """

    def __init__(self, root_path: Optional[Path] = None):
        """
        Initialize the workspace manager.

        Args:
            root_path: Root path for workspace (defaults to workspace/ in project root)
        """
        if root_path is None:
            root_path = self._find_workspace_root()

        self.root = root_path
        self.inputs_dir = self.root / "inputs"
        self.intermediate_dir = self.root / "intermediate"
        self.evaluations_dir = self.intermediate_dir / "evaluations"
        self.outputs_dir = self.root / "outputs"

        self.logger = logging.getLogger(self.__class__.__name__)

    def _find_workspace_root(self) -> Path:
        """
        Find the workspace root directory.

        Returns:
            Path to workspace directory
        """
        current = Path.cwd()

        # Look for workspace directory
        while current != current.parent:
            workspace_path = current / "workspace"
            if workspace_path.exists() and workspace_path.is_dir():
                return workspace_path
            current = current.parent

        # Create in current directory if not found
        workspace_path = Path.cwd() / "workspace"
        return workspace_path

    def initialize(self, clean: bool = False) -> None:
        """
        Initialize the workspace directory structure.

        Creates all necessary directories if they don't exist.
        Optionally cleans intermediate and output directories.

        Args:
            clean: If True, remove all intermediate and output files
        """
        # Create directories
        self.inputs_dir.mkdir(parents=True, exist_ok=True)
        self.intermediate_dir.mkdir(parents=True, exist_ok=True)
        self.evaluations_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"Workspace initialized at {self.root}")

        # Clean if requested
        if clean:
            self.clean_intermediate()
            self.clean_outputs()

    def clean_intermediate(self) -> None:
        """Remove all intermediate files."""
        if self.intermediate_dir.exists():
            for item in self.intermediate_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir() and item != self.evaluations_dir:
                    shutil.rmtree(item)

        # Clean evaluations directory
        if self.evaluations_dir.exists():
            for item in self.evaluations_dir.iterdir():
                if item.is_file():
                    item.unlink()

        self.logger.info("Intermediate files cleaned")

    def clean_outputs(self) -> None:
        """Remove all output files."""
        if self.outputs_dir.exists():
            for item in self.outputs_dir.iterdir():
                if item.is_file():
                    item.unlink()

        self.logger.info("Output files cleaned")

    def clean_all(self) -> None:
        """Remove all workspace files (inputs, intermediate, outputs)."""
        self.clean_intermediate()
        self.clean_outputs()

        if self.inputs_dir.exists():
            for item in self.inputs_dir.iterdir():
                if item.is_file():
                    item.unlink()

        self.logger.info("All workspace files cleaned")

    def get_input_path(self, filename: str) -> Path:
        """
        Get path for an input file.

        Args:
            filename: Name of the input file

        Returns:
            Full path to input file
        """
        return self.inputs_dir / filename

    def get_intermediate_path(self, filename: str) -> Path:
        """
        Get path for an intermediate file.

        Args:
            filename: Name of the intermediate file

        Returns:
            Full path to intermediate file
        """
        return self.intermediate_dir / filename

    def get_evaluation_path(self, criterion_id: str) -> Path:
        """
        Get path for a criterion evaluation file.

        Args:
            criterion_id: Criterion identifier (e.g., "prd_quality")

        Returns:
            Full path to evaluation JSON file
        """
        filename = f"{criterion_id}.json"
        return self.evaluations_dir / filename

    def get_output_path(self, filename: str) -> Path:
        """
        Get path for an output file.

        Args:
            filename: Name of the output file

        Returns:
            Full path to output file
        """
        return self.outputs_dir / filename

    def list_inputs(self, pattern: str = "*") -> list[Path]:
        """
        List all input files matching a pattern.

        Args:
            pattern: Glob pattern (default: all files)

        Returns:
            List of input file paths
        """
        if not self.inputs_dir.exists():
            return []
        return list(self.inputs_dir.glob(pattern))

    def list_evaluations(self) -> list[Path]:
        """
        List all evaluation files.

        Returns:
            List of evaluation file paths
        """
        if not self.evaluations_dir.exists():
            return []
        return list(self.evaluations_dir.glob("*.json"))

    def list_outputs(self, pattern: str = "*") -> list[Path]:
        """
        List all output files matching a pattern.

        Args:
            pattern: Glob pattern (default: all files)

        Returns:
            List of output file paths
        """
        if not self.outputs_dir.exists():
            return []
        return list(self.outputs_dir.glob(pattern))

    def exists(self, file_type: str, filename: str) -> bool:
        """
        Check if a file exists in the workspace.

        Args:
            file_type: Type of file ("input", "intermediate", "evaluation", "output")
            filename: Name of the file

        Returns:
            True if file exists, False otherwise
        """
        if file_type == "input":
            return self.get_input_path(filename).exists()
        elif file_type == "intermediate":
            return self.get_intermediate_path(filename).exists()
        elif file_type == "evaluation":
            return self.get_evaluation_path(filename).exists()
        elif file_type == "output":
            return self.get_output_path(filename).exists()
        else:
            raise ValueError(f"Unknown file_type: {file_type}")

    def get_workspace_stats(self) -> dict[str, int]:
        """
        Get statistics about workspace contents.

        Returns:
            Dictionary with counts of files in each directory
        """
        return {
            "inputs": len(self.list_inputs()) if self.inputs_dir.exists() else 0,
            "evaluations": len(self.list_evaluations()) if self.evaluations_dir.exists() else 0,
            "outputs": len(self.list_outputs()) if self.outputs_dir.exists() else 0,
        }

    def __repr__(self) -> str:
        """String representation of the workspace manager."""
        stats = self.get_workspace_stats()
        return (
            f"WorkspaceManager(root={self.root}, "
            f"inputs={stats['inputs']}, "
            f"evaluations={stats['evaluations']}, "
            f"outputs={stats['outputs']})"
        )


# Singleton instance
_workspace_manager: Optional[WorkspaceManager] = None


def get_workspace() -> WorkspaceManager:
    """Get or create the singleton WorkspaceManager instance."""
    global _workspace_manager
    if _workspace_manager is None:
        _workspace_manager = WorkspaceManager()
        _workspace_manager.initialize()
    return _workspace_manager
