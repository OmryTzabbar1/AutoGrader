"""
Configuration loading and management for the AutoGrader system.

This module provides functionality to load configuration from YAML files
and override with environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class AgentConfig(BaseModel):
    """Configuration for a specific agent."""

    enabled: bool = Field(True, description="Whether agent is enabled")
    timeout_seconds: int = Field(300, description="Execution timeout")
    config: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific config")


class OrchestratorConfig(BaseModel):
    """Configuration for the OrchestratorAgent."""

    max_parallel_evaluations: int = Field(10, description="Max parallel evaluators")
    timeout_seconds: int = Field(300, description="Total workflow timeout")
    retry_failed_evaluations: bool = Field(False, description="Retry failed evaluations")


class ParserConfig(BaseModel):
    """Configuration for the ParserAgent."""

    engine: str = Field("pymupdf", description="Primary parser engine")
    fallback_engine: str = Field("pdfplumber", description="Fallback parser engine")
    cache_enabled: bool = Field(True, description="Enable caching")
    extract_images: bool = Field(False, description="Extract images")
    extract_tables: bool = Field(True, description="Extract tables")


class EvaluatorConfig(BaseModel):
    """Configuration for an EvaluatorAgent instance."""

    criterion: str = Field(..., description="Criterion identifier")
    weight: float = Field(..., ge=0.0, le=1.0, description="Criterion weight")
    prompt_template: str = Field(..., description="Path to prompt template")
    keywords: list[str] = Field(default_factory=list, description="Keywords for section extraction")


class ScoringConfig(BaseModel):
    """Configuration for the ScoringAgent."""

    severity_factors: Dict[str, float] = Field(
        default_factory=lambda: {
            "critical": 0.5,
            "important": 0.8,
            "minor": 0.95,
            "strength": 1.0
        },
        description="Severity adjustment factors"
    )


class ReportingConfig(BaseModel):
    """Configuration for the ReporterAgent."""

    output_dir: str = Field("workspace/outputs", description="Output directory")
    formats: list[str] = Field(default_factory=lambda: ["markdown"], description="Output formats")
    template_dir: str = Field("templates", description="Template directory")


class LLMConfig(BaseModel):
    """Configuration for LLM API interaction."""

    api_key: Optional[str] = Field(None, description="API key (from env)")
    model: str = Field("claude-sonnet-4-20250514", description="Model name")
    max_tokens: int = Field(4096, description="Max output tokens")
    temperature: float = Field(0.0, description="Sampling temperature")
    max_retries: int = Field(3, description="Max retry attempts")
    timeout_seconds: int = Field(60, description="Request timeout")


class AutoGraderConfig(BaseModel):
    """
    Complete configuration for the AutoGrader system.

    This is the root configuration object that contains all agent configurations.
    """

    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)
    parser: ParserConfig = Field(default_factory=ParserConfig)
    evaluators: list[EvaluatorConfig] = Field(default_factory=list)
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)
    reporting: ReportingConfig = Field(default_factory=ReportingConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    @field_validator('evaluators')
    @classmethod
    def validate_evaluators(cls, v: list[EvaluatorConfig]) -> list[EvaluatorConfig]:
        """Ensure evaluator weights sum to approximately 1.0."""
        if v:
            total_weight = sum(e.weight for e in v)
            if not (0.95 <= total_weight <= 1.05):
                raise ValueError(
                    f"Evaluator weights should sum to ~1.0, got {total_weight:.2f}"
                )
        return v


class ConfigLoader:
    """
    Configuration loader with YAML file support and environment variable overrides.

    Example:
        >>> loader = ConfigLoader()
        >>> config = loader.load_config("config/default.yaml")
        >>> print(config.llm.model)
        claude-sonnet-4-20250514
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize the configuration loader.

        Args:
            project_root: Root directory of the project (auto-detected if None)
        """
        self.project_root = project_root or self._find_project_root()

    def _find_project_root(self) -> Path:
        """
        Find the project root directory by looking for specific marker files.

        Returns:
            Path to project root
        """
        current = Path.cwd()

        # Look for marker files/directories
        markers = ['src', 'config', 'pyproject.toml', 'setup.py']

        while current != current.parent:
            if any((current / marker).exists() for marker in markers):
                return current
            current = current.parent

        # Fallback to current directory
        return Path.cwd()

    def load_yaml(self, config_path: Path) -> Dict[str, Any]:
        """
        Load a YAML configuration file.

        Args:
            config_path: Path to YAML file (relative to project root or absolute)

        Returns:
            Dictionary of configuration values

        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        if not config_path.is_absolute():
            config_path = self.project_root / config_path

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration.

        Environment variables should be prefixed with AUTOGRADER_ and use
        double underscores for nesting. For example:
        - AUTOGRADER_LLM__API_KEY
        - AUTOGRADER_PARSER__ENGINE

        Args:
            config: Base configuration dictionary

        Returns:
            Configuration with environment overrides applied
        """
        prefix = "AUTOGRADER_"

        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # Remove prefix and split by double underscore
            key_path = key[len(prefix):].lower().split('__')

            # Navigate to the correct nested dict
            current = config
            for part in key_path[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Set the value (convert string to appropriate type)
            final_key = key_path[-1]
            current[final_key] = self._convert_env_value(value)

        # Special case: API key from environment
        if 'CLAUDE_API_KEY' in os.environ:
            if 'llm' not in config:
                config['llm'] = {}
            config['llm']['api_key'] = os.environ['CLAUDE_API_KEY']

        return config

    def _convert_env_value(self, value: str) -> Any:
        """
        Convert string environment variable value to appropriate Python type.

        Args:
            value: String value from environment

        Returns:
            Converted value (bool, int, float, or str)
        """
        # Boolean
        if value.lower() in ('true', 'yes', '1'):
            return True
        if value.lower() in ('false', 'no', '0'):
            return False

        # Number
        try:
            if '.' in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # String
        return value

    def load_config(
        self,
        config_path: Optional[Path] = None,
        apply_env: bool = True
    ) -> AutoGraderConfig:
        """
        Load complete AutoGrader configuration.

        Args:
            config_path: Path to config file (defaults to config/default.yaml)
            apply_env: Whether to apply environment variable overrides

        Returns:
            Validated AutoGraderConfig instance
        """
        if config_path is None:
            config_path = Path("config/default.yaml")

        # Load base config from YAML
        config_dict = self.load_yaml(config_path)

        # Apply environment overrides
        if apply_env:
            config_dict = self.apply_env_overrides(config_dict)

        # Validate and return
        return AutoGraderConfig(**config_dict)

    def merge_configs(
        self,
        base_config: Dict[str, Any],
        override_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Deep merge two configuration dictionaries.

        Args:
            base_config: Base configuration
            override_config: Configuration to override with

        Returns:
            Merged configuration
        """
        result = base_config.copy()

        for key, value in override_config.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self.merge_configs(result[key], value)
            else:
                result[key] = value

        return result


# Singleton instance
_config_loader: Optional[ConfigLoader] = None


def get_config_loader() -> ConfigLoader:
    """Get or create the singleton ConfigLoader instance."""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def load_config(config_path: Optional[Path] = None) -> AutoGraderConfig:
    """
    Convenience function to load configuration.

    Args:
        config_path: Path to config file (optional)

    Returns:
        AutoGraderConfig instance
    """
    loader = get_config_loader()
    return loader.load_config(config_path)
