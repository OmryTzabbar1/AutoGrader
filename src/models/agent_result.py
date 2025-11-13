"""
Agent result model for standardized agent outputs.

This module defines the AgentResult dataclass used by all agents to return
their execution results in a consistent format.
"""

from typing import Any, Dict, Generic, Optional, TypeVar
from dataclasses import dataclass, field

T = TypeVar('T')


@dataclass
class AgentResult(Generic[T]):
    """
    Standard result structure returned by all agents.

    This class provides a consistent interface for agent outputs, including
    success status, output data, error information, and execution metadata.

    Type Parameters:
        T: The type of output data

    Attributes:
        success: Whether the agent execution succeeded
        output: The output data (None if failed)
        error: Error message if execution failed (None if succeeded)
        metadata: Additional metadata about execution
        execution_time: Time taken to execute in seconds

    Examples:
        >>> # Successful execution
        >>> result = AgentResult(success=True, output="processed data")
        >>> print(result.success)
        True

        >>> # Failed execution
        >>> result = AgentResult(
        ...     success=False,
        ...     error="Failed to parse PDF",
        ...     metadata={"file": "submission.pdf"}
        ... )
        >>> print(result.error)
        Failed to parse PDF
    """

    success: bool
    output: Optional[T] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0

    def __post_init__(self):
        """
        Validate the result after initialization.

        Ensures that failed results have an error message and successful
        results have output (unless explicitly None is valid output).
        """
        if not self.success and self.error is None:
            raise ValueError(
                "Failed AgentResult must have an error message"
            )

        if self.success and self.output is None and self.error is not None:
            raise ValueError(
                "Successful AgentResult cannot have an error message"
            )

    def add_metadata(self, key: str, value: Any) -> 'AgentResult[T]':
        """
        Add a metadata entry to the result.

        Args:
            key: Metadata key
            value: Metadata value

        Returns:
            Self for method chaining
        """
        self.metadata[key] = value
        return self

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """
        Get a metadata value with optional default.

        Args:
            key: Metadata key to retrieve
            default: Default value if key not found

        Returns:
            Metadata value or default
        """
        return self.metadata.get(key, default)

    def is_success(self) -> bool:
        """
        Check if the result represents a successful execution.

        Returns:
            True if successful, False otherwise
        """
        return self.success

    def is_failure(self) -> bool:
        """
        Check if the result represents a failed execution.

        Returns:
            True if failed, False otherwise
        """
        return not self.success

    def get_output_or_raise(self) -> T:
        """
        Get the output or raise an exception if failed.

        Returns:
            The output data

        Raises:
            RuntimeError: If execution failed
        """
        if not self.success:
            raise RuntimeError(f"Agent execution failed: {self.error}")
        return self.output

    def get_output_or_default(self, default: T) -> T:
        """
        Get the output or return a default value if failed.

        Args:
            default: Default value to return if failed

        Returns:
            Output data or default value
        """
        return self.output if self.success else default

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary.

        Returns:
            Dictionary representation of the result
        """
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "metadata": self.metadata,
            "execution_time": self.execution_time
        }

    def __repr__(self) -> str:
        """String representation of the result."""
        status = "Success" if self.success else "Failure"
        time_str = f"{self.execution_time:.2f}s" if self.execution_time > 0 else "N/A"
        if self.success:
            return f"AgentResult({status}, output_type={type(self.output).__name__}, time={time_str})"
        else:
            return f"AgentResult({status}, error='{self.error}', time={time_str})"

    @classmethod
    def success_result(
        cls,
        output: T,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time: float = 0.0
    ) -> 'AgentResult[T]':
        """
        Factory method to create a successful result.

        Args:
            output: The output data
            metadata: Optional metadata dictionary
            execution_time: Execution time in seconds

        Returns:
            AgentResult with success=True
        """
        return cls(
            success=True,
            output=output,
            metadata=metadata or {},
            execution_time=execution_time
        )

    @classmethod
    def failure_result(
        cls,
        error: str,
        metadata: Optional[Dict[str, Any]] = None,
        execution_time: float = 0.0
    ) -> 'AgentResult[T]':
        """
        Factory method to create a failed result.

        Args:
            error: Error message
            metadata: Optional metadata dictionary
            execution_time: Execution time in seconds

        Returns:
            AgentResult with success=False
        """
        return cls(
            success=False,
            output=None,
            error=error,
            metadata=metadata or {},
            execution_time=execution_time
        )
