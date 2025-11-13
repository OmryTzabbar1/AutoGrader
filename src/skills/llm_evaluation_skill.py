"""
LLM evaluation skill for Claude API interaction.

This skill provides functionality to interact with Claude API for evaluating
submissions against criteria, with retry logic, cost tracking, and response parsing.
"""

import os
import json
import asyncio
import logging
from typing import Any, Dict, Optional
from datetime import datetime

try:
    import anthropic
    from anthropic import APIError, APIStatusError
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False


class LLMAPIError(Exception):
    """Raised when LLM API calls fail."""
    pass


class LLMEvaluationSkill:
    """
    Skill for Claude API interaction and evaluation.

    Features:
    - Async API calls with retry logic
    - Cost calculation and tracking
    - Structured JSON response parsing
    - Prompt construction with templates
    - Token counting

    Example:
        >>> skill = LLMEvaluationSkill()
        >>> response = await skill.evaluate_with_claude(
        ...     prompt="Evaluate this README",
        ...     context=readme_text,
        ...     criticism_multiplier=1.0
        ... )
        >>> print(response['score'])
        85.0
    """

    # Pricing for Claude Sonnet 4.5 (as of Nov 2025)
    INPUT_PRICE_PER_MILLION = 3.00   # $3 per 1M input tokens
    OUTPUT_PRICE_PER_MILLION = 15.00  # $15 per 1M output tokens

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the LLM evaluation skill.

        Args:
            config: Optional configuration dictionary

        Raises:
            RuntimeError: If anthropic library not available
            ValueError: If API key not found
        """
        if not ANTHROPIC_AVAILABLE:
            raise RuntimeError(
                "anthropic library not installed. Run: pip install anthropic"
            )

        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

        # Get API key from config or environment
        api_key = self.config.get('api_key') or os.getenv('CLAUDE_API_KEY')
        if not api_key:
            raise ValueError(
                "Claude API key not found. Set CLAUDE_API_KEY environment variable "
                "or pass api_key in config."
            )

        self.client = anthropic.Anthropic(api_key=api_key)

        # Configuration
        self.model = self.config.get('model', 'claude-sonnet-4-20250514')
        self.max_tokens = self.config.get('max_tokens', 4096)
        self.temperature = self.config.get('temperature', 0.0)
        self.max_retries = self.config.get('max_retries', 3)
        self.timeout_seconds = self.config.get('timeout_seconds', 60)

    async def evaluate_with_claude(
        self,
        prompt: str,
        context: str,
        *,
        criticism_multiplier: float = 1.0,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Call Claude API for evaluation.

        Args:
            prompt: Evaluation prompt template
            context: Content to evaluate
            criticism_multiplier: Criticism level (0.6 to 1.5)
            model: Model name (uses default if None)
            max_tokens: Max output tokens (uses default if None)
            temperature: Sampling temperature (uses default if None)

        Returns:
            Dictionary with evaluation results:
            - score: float (0-100)
            - evidence: List[str]
            - strengths: List[str]
            - weaknesses: List[str]
            - suggestions: List[str]
            - severity: str
            - tokens_used: int
            - cost: float

        Raises:
            LLMAPIError: If API call fails after all retries
        """
        full_prompt = self._construct_full_prompt(
            prompt,
            context,
            criticism_multiplier
        )

        # Use provided values or defaults
        model = model or self.model
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature or self.temperature

        # Call API with retry
        response = await self._call_api_with_retry(
            prompt=full_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )

        # Parse and return response
        return self._parse_response(response)

    def _construct_full_prompt(
        self,
        template: str,
        context: str,
        criticism_multiplier: float
    ) -> str:
        """
        Build complete evaluation prompt.

        Args:
            template: Prompt template
            context: Content to evaluate
            criticism_multiplier: Criticism level

        Returns:
            Complete prompt string
        """
        # Interpret criticism multiplier
        if criticism_multiplier >= 1.5:
            tone = "VERY STRICT - Student claims excellence, demand perfection"
        elif criticism_multiplier >= 1.2:
            tone = "STRICT - High standards expected, thorough evaluation"
        elif criticism_multiplier >= 1.0:
            tone = "BALANCED - Standard academic evaluation"
        elif criticism_multiplier >= 0.8:
            tone = "ENCOURAGING - Focus on strengths, constructive feedback"
        else:
            tone = "SUPPORTIVE - Student aware of gaps, build on positives"

        return f"""
{template}

EVALUATION TONE: {tone}
CRITICISM MULTIPLIER: {criticism_multiplier}x

CONTENT TO EVALUATE:
{context}

IMPORTANT INSTRUCTIONS:
1. Respond ONLY with valid JSON (no markdown, no extra text)
2. Be specific and cite evidence with page numbers
3. Provide actionable suggestions for improvement
4. Adjust your strictness based on the criticism multiplier above

Required JSON format:
{{
  "score": <float between 0-100>,
  "evidence": ["Page X: specific quote or finding", "Page Y: ...", ...],
  "strengths": ["Specific strength 1", "Specific strength 2", ...],
  "weaknesses": ["Specific weakness 1", "Specific weakness 2", ...],
  "suggestions": ["Actionable suggestion 1", "Actionable suggestion 2", ...],
  "severity": "critical" | "important" | "minor" | "strength"
}}

Severity guidelines:
- "critical": Major issues that would cause project failure
- "important": Significant issues affecting quality/usability
- "minor": Small issues or missing polish
- "strength": No significant issues, highlight strengths
"""

    async def _call_api_with_retry(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float
    ) -> anthropic.types.Message:
        """
        Call Claude API with exponential backoff retry.

        Args:
            prompt: Full evaluation prompt
            model: Model name
            max_tokens: Max output tokens
            temperature: Sampling temperature

        Returns:
            Claude API response message

        Raises:
            LLMAPIError: If all retries fail
        """
        for attempt in range(self.max_retries):
            try:
                self.logger.info(
                    f"Calling Claude API (attempt {attempt + 1}/{self.max_retries})",
                    extra={"model": model, "max_tokens": max_tokens}
                )

                # Make async call
                response = await asyncio.to_thread(
                    self.client.messages.create,
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}],
                    timeout=self.timeout_seconds
                )

                self.logger.info(
                    "Claude API call successful",
                    extra={
                        "input_tokens": response.usage.input_tokens,
                        "output_tokens": response.usage.output_tokens
                    }
                )

                return response

            except APIStatusError as e:
                self.logger.warning(
                    f"Claude API error (attempt {attempt + 1}): {e.status_code} - {e.message}"
                )

                # Don't retry on client errors (4xx)
                if 400 <= e.status_code < 500:
                    raise LLMAPIError(f"Client error: {e.message}") from e

                # Retry on server errors (5xx)
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    self.logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    raise LLMAPIError(f"API call failed after {self.max_retries} attempts") from e

            except APIError as e:
                self.logger.error(f"Claude API error: {e}")
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                else:
                    raise LLMAPIError(f"API call failed: {e}") from e

            except Exception as e:
                self.logger.error(f"Unexpected error during API call: {e}")
                raise LLMAPIError(f"Unexpected error: {e}") from e

        raise LLMAPIError(f"Failed after {self.max_retries} attempts")

    def _parse_response(self, response: anthropic.types.Message) -> Dict[str, Any]:
        """
        Parse structured JSON response from Claude.

        Args:
            response: Claude API response message

        Returns:
            Parsed evaluation dictionary

        Raises:
            LLMAPIError: If response format is invalid
        """
        # Extract text content
        text = response.content[0].text

        # Strip markdown code blocks if present
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        text = text.strip()

        # Parse JSON
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse JSON response: {text[:200]}...")
            raise LLMAPIError(f"Invalid JSON response: {e}") from e

        # Validate required fields
        required_fields = ['score', 'evidence', 'strengths', 'weaknesses', 'suggestions', 'severity']
        missing_fields = [field for field in required_fields if field not in parsed]
        if missing_fields:
            raise LLMAPIError(f"Missing required fields: {missing_fields}")

        # Add metadata
        parsed['tokens_used'] = response.usage.input_tokens + response.usage.output_tokens
        parsed['input_tokens'] = response.usage.input_tokens
        parsed['output_tokens'] = response.usage.output_tokens
        parsed['cost'] = self._calculate_cost(response.usage)
        parsed['model'] = response.model
        parsed['timestamp'] = datetime.now().isoformat()

        return parsed

    def _calculate_cost(self, usage: anthropic.types.Usage) -> float:
        """
        Calculate cost in USD for API call.

        Args:
            usage: Token usage from API response

        Returns:
            Cost in USD
        """
        input_cost = (usage.input_tokens / 1_000_000) * self.INPUT_PRICE_PER_MILLION
        output_cost = (usage.output_tokens / 1_000_000) * self.OUTPUT_PRICE_PER_MILLION
        return round(input_cost + output_cost, 4)

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate number of tokens in text.

        Uses rough approximation: ~4 characters per token for English text.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        return len(text) // 4

    def estimate_cost(self, prompt: str, expected_response_tokens: int = 500) -> float:
        """
        Estimate cost for an API call.

        Args:
            prompt: Full prompt text
            expected_response_tokens: Expected response length

        Returns:
            Estimated cost in USD
        """
        input_tokens = self.estimate_tokens(prompt)
        output_tokens = expected_response_tokens

        input_cost = (input_tokens / 1_000_000) * self.INPUT_PRICE_PER_MILLION
        output_cost = (output_tokens / 1_000_000) * self.OUTPUT_PRICE_PER_MILLION

        return round(input_cost + output_cost, 4)
