"""
Unit tests for FileOperationsSkill.
"""

import pytest
from pathlib import Path
import json
import yaml

from skills.file_operations_skill import FileOperationsSkill


@pytest.fixture
def file_ops():
    """Create FileOperationsSkill instance."""
    return FileOperationsSkill()


class TestFileOperationsSkill:
    """Test suite for FileOperationsSkill."""

    def test_read_text(self, file_ops, tmp_path):
        """Test reading text files."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        # Read file
        content = file_ops.read_text(test_file)

        assert content == test_content

    def test_write_text(self, file_ops, tmp_path):
        """Test writing text files."""
        test_file = tmp_path / "output.txt"
        test_content = "Test content"

        # Write file
        file_ops.write_text(test_file, test_content)

        # Verify
        assert test_file.exists()
        assert test_file.read_text() == test_content

    def test_read_json(self, file_ops, tmp_path):
        """Test reading JSON files."""
        # Create test JSON
        test_file = tmp_path / "test.json"
        test_data = {"name": "John", "age": 30}
        test_file.write_text(json.dumps(test_data))

        # Read JSON
        data = file_ops.read_json(test_file)

        assert data == test_data

    def test_write_json(self, file_ops, tmp_path):
        """Test writing JSON files."""
        test_file = tmp_path / "output.json"
        test_data = {"test": "data", "values": [1, 2, 3]}

        # Write JSON
        file_ops.write_json(test_file, test_data)

        # Verify
        assert test_file.exists()
        loaded_data = json.loads(test_file.read_text())
        assert loaded_data == test_data

    def test_read_yaml(self, file_ops, tmp_path):
        """Test reading YAML files."""
        # Create test YAML
        test_file = tmp_path / "test.yaml"
        test_data = {"name": "Test", "values": [1, 2, 3]}
        test_file.write_text(yaml.dump(test_data))

        # Read YAML
        data = file_ops.read_yaml(test_file)

        assert data == test_data

    def test_write_yaml(self, file_ops, tmp_path):
        """Test writing YAML files."""
        test_file = tmp_path / "output.yaml"
        test_data = {"key": "value", "list": ["a", "b", "c"]}

        # Write YAML
        file_ops.write_yaml(test_file, test_data)

        # Verify
        assert test_file.exists()
        loaded_data = yaml.safe_load(test_file.read_text())
        assert loaded_data == test_data

    def test_append_text(self, file_ops, tmp_path):
        """Test appending to text files."""
        test_file = tmp_path / "append.txt"

        # Write initial content
        file_ops.write_text(test_file, "Line 1\n")

        # Append content
        file_ops.append_text(test_file, "Line 2\n")
        file_ops.append_text(test_file, "Line 3\n")

        # Verify
        content = test_file.read_text()
        assert content == "Line 1\nLine 2\nLine 3\n"

    def test_ensure_dir(self, file_ops, tmp_path):
        """Test ensuring directory exists."""
        test_dir = tmp_path / "nested" / "directory" / "path"

        # Ensure directory
        file_ops.ensure_dir(test_dir)

        # Verify
        assert test_dir.exists()
        assert test_dir.is_dir()

    def test_ensure_dir_idempotent(self, file_ops, tmp_path):
        """Test ensure_dir is idempotent."""
        test_dir = tmp_path / "test_dir"

        # Call multiple times
        file_ops.ensure_dir(test_dir)
        file_ops.ensure_dir(test_dir)
        file_ops.ensure_dir(test_dir)

        # Should not raise error
        assert test_dir.exists()

    def test_file_exists(self, file_ops, tmp_path):
        """Test checking if file exists."""
        test_file = tmp_path / "exists.txt"

        # File doesn't exist yet
        assert not file_ops.file_exists(test_file)

        # Create file
        test_file.write_text("content")

        # Now it exists
        assert file_ops.file_exists(test_file)

    def test_read_bytes(self, file_ops, tmp_path):
        """Test reading binary files."""
        test_file = tmp_path / "binary.dat"
        test_data = b'\x00\x01\x02\x03\xff'

        test_file.write_bytes(test_data)

        # Read bytes
        data = file_ops.read_bytes(test_file)

        assert data == test_data

    def test_write_bytes(self, file_ops, tmp_path):
        """Test writing binary files."""
        test_file = tmp_path / "output.dat"
        test_data = b'\xde\xad\xbe\xef'

        # Write bytes
        file_ops.write_bytes(test_file, test_data)

        # Verify
        assert test_file.exists()
        assert test_file.read_bytes() == test_data

    def test_read_nonexistent_file(self, file_ops, tmp_path):
        """Test reading file that doesn't exist raises error."""
        test_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            file_ops.read_text(test_file)

    def test_invalid_json(self, file_ops, tmp_path):
        """Test reading invalid JSON raises error."""
        test_file = tmp_path / "invalid.json"
        test_file.write_text("not valid json{")

        with pytest.raises(json.JSONDecodeError):
            file_ops.read_json(test_file)

    def test_invalid_yaml(self, file_ops, tmp_path):
        """Test reading invalid YAML raises error."""
        test_file = tmp_path / "invalid.yaml"
        test_file.write_text("invalid: yaml: : content")

        with pytest.raises(yaml.YAMLError):
            file_ops.read_yaml(test_file)
