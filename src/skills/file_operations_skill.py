"""
File operations skill for reading and writing various file formats.

This skill provides stateless functions for file I/O operations including
JSON, YAML, Markdown, and plain text files.
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging


class FileOperationsSkill:
    """
    Skill for file operations (read/write JSON, YAML, Markdown, text).

    All methods are stateless and can be called independently.

    Example:
        >>> skill = FileOperationsSkill()
        >>> data = skill.read_json(Path("config.json"))
        >>> skill.write_text(Path("report.md"), "# Report\\n...")
    """

    def __init__(self):
        """Initialize the file operations skill."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def read_text(self, file_path: Path, encoding: str = 'utf-8') -> str:
        """
        Read text file.

        Args:
            file_path: Path to text file
            encoding: File encoding (default: utf-8)

        Returns:
            File contents as string

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file can't be read
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            raise IOError(f"Failed to read file: {e}") from e

    def write_text(
        self,
        file_path: Path,
        content: str,
        encoding: str = 'utf-8',
        create_dirs: bool = True
    ) -> None:
        """
        Write text file.

        Args:
            file_path: Path to write to
            content: Text content
            encoding: File encoding (default: utf-8)
            create_dirs: Create parent directories if needed

        Raises:
            IOError: If file can't be written
        """
        try:
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)

            self.logger.debug(f"Wrote {len(content)} characters to {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to write {file_path}: {e}")
            raise IOError(f"Failed to write file: {e}") from e

    def read_json(self, file_path: Path, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Read JSON file.

        Args:
            file_path: Path to JSON file
            encoding: File encoding (default: utf-8)

        Returns:
            Parsed JSON data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If JSON is invalid
            IOError: If file can't be read
        """
        text = self.read_text(file_path, encoding)

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in {file_path}: {e}")
            raise

    def write_json(
        self,
        file_path: Path,
        data: Dict[str, Any],
        indent: int = 2,
        encoding: str = 'utf-8',
        create_dirs: bool = True
    ) -> None:
        """
        Write JSON file.

        Args:
            file_path: Path to write to
            data: Data to serialize as JSON
            indent: Indentation spaces (default: 2)
            encoding: File encoding (default: utf-8)
            create_dirs: Create parent directories if needed

        Raises:
            IOError: If file can't be written
        """
        try:
            json_str = json.dumps(data, indent=indent, ensure_ascii=False)
            self.write_text(file_path, json_str, encoding, create_dirs)
        except Exception as e:
            self.logger.error(f"Failed to write JSON to {file_path}: {e}")
            raise IOError(f"Failed to write JSON: {e}") from e

    def read_yaml(self, file_path: Path, encoding: str = 'utf-8') -> Dict[str, Any]:
        """
        Read YAML file.

        Args:
            file_path: Path to YAML file
            encoding: File encoding (default: utf-8)

        Returns:
            Parsed YAML data as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML is invalid
            IOError: If file can't be read
        """
        text = self.read_text(file_path, encoding)

        try:
            return yaml.safe_load(text) or {}
        except yaml.YAMLError as e:
            self.logger.error(f"Invalid YAML in {file_path}: {e}")
            raise

    def write_yaml(
        self,
        file_path: Path,
        data: Dict[str, Any],
        encoding: str = 'utf-8',
        create_dirs: bool = True
    ) -> None:
        """
        Write YAML file.

        Args:
            file_path: Path to write to
            data: Data to serialize as YAML
            encoding: File encoding (default: utf-8)
            create_dirs: Create parent directories if needed

        Raises:
            IOError: If file can't be written
        """
        try:
            yaml_str = yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
            self.write_text(file_path, yaml_str, encoding, create_dirs)
        except Exception as e:
            self.logger.error(f"Failed to write YAML to {file_path}: {e}")
            raise IOError(f"Failed to write YAML: {e}") from e

    def read_bytes(self, file_path: Path) -> bytes:
        """
        Read binary file.

        Args:
            file_path: Path to binary file

        Returns:
            File contents as bytes

        Raises:
            FileNotFoundError: If file doesn't exist
            IOError: If file can't be read
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Failed to read {file_path}: {e}")
            raise IOError(f"Failed to read file: {e}") from e

    def write_bytes(
        self,
        file_path: Path,
        content: bytes,
        create_dirs: bool = True
    ) -> None:
        """
        Write binary file.

        Args:
            file_path: Path to write to
            content: Binary content
            create_dirs: Create parent directories if needed

        Raises:
            IOError: If file can't be written
        """
        try:
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'wb') as f:
                f.write(content)

            self.logger.debug(f"Wrote {len(content)} bytes to {file_path}")

        except Exception as e:
            self.logger.error(f"Failed to write {file_path}: {e}")
            raise IOError(f"Failed to write file: {e}") from e

    def append_text(
        self,
        file_path: Path,
        content: str,
        encoding: str = 'utf-8',
        create_dirs: bool = True
    ) -> None:
        """
        Append text to file.

        Args:
            file_path: Path to file
            content: Text to append
            encoding: File encoding (default: utf-8)
            create_dirs: Create parent directories if needed

        Raises:
            IOError: If file can't be written
        """
        try:
            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'a', encoding=encoding) as f:
                f.write(content)

        except Exception as e:
            self.logger.error(f"Failed to append to {file_path}: {e}")
            raise IOError(f"Failed to append to file: {e}") from e

    def file_exists(self, file_path: Path) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Path to check

        Returns:
            True if file exists, False otherwise
        """
        return file_path.exists() and file_path.is_file()

    def dir_exists(self, dir_path: Path) -> bool:
        """
        Check if directory exists.

        Args:
            dir_path: Path to check

        Returns:
            True if directory exists, False otherwise
        """
        return dir_path.exists() and dir_path.is_dir()

    def ensure_dir(self, dir_path: Path) -> None:
        """
        Ensure directory exists (create if needed).

        Args:
            dir_path: Path to directory

        Raises:
            IOError: If directory can't be created
        """
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to create directory {dir_path}: {e}")
            raise IOError(f"Failed to create directory: {e}") from e

    def list_files(
        self,
        dir_path: Path,
        pattern: str = "*",
        recursive: bool = False
    ) -> List[Path]:
        """
        List files in directory matching pattern.

        Args:
            dir_path: Directory to search
            pattern: Glob pattern (default: all files)
            recursive: Search recursively (default: False)

        Returns:
            List of file paths

        Raises:
            FileNotFoundError: If directory doesn't exist
        """
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {dir_path}")

        if recursive:
            return list(dir_path.rglob(pattern))
        else:
            return list(dir_path.glob(pattern))

    def get_file_size(self, file_path: Path) -> int:
        """
        Get file size in bytes.

        Args:
            file_path: Path to file

        Returns:
            File size in bytes

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return file_path.stat().st_size

    def copy_file(self, source: Path, destination: Path, create_dirs: bool = True) -> None:
        """
        Copy file from source to destination.

        Args:
            source: Source file path
            destination: Destination file path
            create_dirs: Create destination directories if needed

        Raises:
            FileNotFoundError: If source doesn't exist
            IOError: If copy fails
        """
        if not source.exists():
            raise FileNotFoundError(f"Source file not found: {source}")

        try:
            if create_dirs:
                destination.parent.mkdir(parents=True, exist_ok=True)

            content = self.read_bytes(source)
            self.write_bytes(destination, content, create_dirs=False)

            self.logger.debug(f"Copied {source} to {destination}")

        except Exception as e:
            self.logger.error(f"Failed to copy {source} to {destination}: {e}")
            raise IOError(f"Failed to copy file: {e}") from e
