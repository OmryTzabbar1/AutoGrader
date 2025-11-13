"""
Base agent class for all AutoGrader agents.

This module provides the abstract base class that all agents inherit from,
defining the common interface and shared functionality.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Generic, Optional, TypeVar
import logging
import time

# Type variables for input and output types
TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')


class BaseAgent(ABC, Generic[TInput, TOutput]):
    """
    Abstract base class for all agents in the AutoGrader system.

    All agents must inherit from this class and implement the execute() method.
    This ensures consistent behavior across all agents and provides common
    functionality like logging, error handling, and validation.

    Type Parameters:
        TInput: The type of input data the agent accepts
        TOutput: The type of output data the agent produces

    Attributes:
        config (Dict[str, Any]): Agent configuration dictionary
        logger (logging.Logger): Agent-specific logger

    Example:
        >>> class MyAgent(BaseAgent[str, int]):
        ...     async def execute(self, input_data: str) -> AgentResult[int]:
        ...         return AgentResult(success=True, output=len(input_data))
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the base agent.

        Args:
            config: Configuration dictionary for the agent
        """
        self.config = config
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        """
        Set up agent-specific logger.

        Returns:
            Configured logger instance
        """
        logger_name = self.__class__.__name__
        logger = logging.getLogger(logger_name)

        # Only configure if not already configured
        if not logger.handlers:
            logger.setLevel(logging.INFO)

            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)

            # Formatter with agent name
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger

    @abstractmethod
    async def execute(self, input_data: TInput) -> 'AgentResult[TOutput]':
        """
        Execute the agent's main task.

        This is the primary method that must be implemented by all agents.
        It takes input data, processes it, and returns a result.

        Args:
            input_data: The input data for the agent to process

        Returns:
            AgentResult containing the output and execution metadata

        Raises:
            Should not raise exceptions - catch and return in AgentResult
        """
        pass

    def validate_input(self, input_data: TInput) -> bool:
        """
        Validate input data before processing.

        Override this method in subclasses to add custom validation logic.

        Args:
            input_data: The input data to validate

        Returns:
            True if input is valid, False otherwise
        """
        return True

    def handle_error(self, error: Exception) -> 'AgentResult[TOutput]':
        """
        Handle errors that occur during agent execution.

        This method provides standardized error handling across all agents.
        It logs the error and returns a failed AgentResult.

        Args:
            error: The exception that occurred

        Returns:
            AgentResult with success=False and error message
        """
        self.logger.error(
            f"Agent execution failed: {error}",
            exc_info=True,
            extra={"agent": self.__class__.__name__}
        )

        # Import here to avoid circular dependency
        from models.agent_result import AgentResult

        return AgentResult(
            success=False,
            output=None,
            error=str(error),
            metadata={"error_type": type(error).__name__}
        )

    def log_execution_start(self, input_data: TInput, **kwargs) -> None:
        """
        Log the start of agent execution.

        Args:
            input_data: The input data being processed
            **kwargs: Additional metadata to log
        """
        self.logger.info(
            f"Starting execution",
            extra={
                "agent": self.__class__.__name__,
                "input_type": type(input_data).__name__,
                **kwargs
            }
        )

    def log_execution_end(
        self,
        success: bool,
        execution_time: float,
        **kwargs
    ) -> None:
        """
        Log the end of agent execution.

        Args:
            success: Whether execution was successful
            execution_time: Time taken in seconds
            **kwargs: Additional metadata to log
        """
        log_level = logging.INFO if success else logging.ERROR
        self.logger.log(
            log_level,
            f"Execution {'completed' if success else 'failed'} in {execution_time:.2f}s",
            extra={
                "agent": self.__class__.__name__,
                "success": success,
                "execution_time": execution_time,
                **kwargs
            }
        )

    async def _timed_execute(self, input_data: TInput) -> 'AgentResult[TOutput]':
        """
        Execute the agent with automatic timing.

        This is a helper method that wraps execute() with timing logic.

        Args:
            input_data: The input data to process

        Returns:
            AgentResult with execution_time set
        """
        start_time = time.time()

        try:
            result = await self.execute(input_data)
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            result = self.handle_error(e)
            result.execution_time = execution_time
            return result

    def get_config_value(
        self,
        key: str,
        default: Any = None,
        required: bool = False
    ) -> Any:
        """
        Get a configuration value with optional default and required check.

        Args:
            key: Configuration key to retrieve
            default: Default value if key not found
            required: If True, raise error if key not found

        Returns:
            Configuration value

        Raises:
            ValueError: If required=True and key not found
        """
        if key in self.config:
            return self.config[key]

        if required:
            raise ValueError(
                f"Required configuration key '{key}' not found for {self.__class__.__name__}"
            )

        return default

    def __repr__(self) -> str:
        """String representation of the agent."""
        return f"{self.__class__.__name__}(config_keys={list(self.config.keys())})"
