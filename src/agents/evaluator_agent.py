"""
Evaluator agent for assessing individual evaluation criteria.

This agent evaluates a single criterion against a parsed document using
Claude API and produces structured feedback with scores and evidence.
"""

from pathlib import Path
from typing import Any, Dict, List
import time

from models.agent_result import AgentResult
from models.core import CriterionEvaluation, CodeBlock, Section
from models.io import EvaluatorInput
from agents.base_agent import BaseAgent
from skills.llm_evaluation_skill import LLMEvaluationSkill
from skills.file_operations_skill import FileOperationsSkill


class EvaluatorAgent(BaseAgent[EvaluatorInput, CriterionEvaluation]):
    """
    Stateless agent that evaluates a single criterion.

    Features:
    - Criterion-specific prompt construction
    - Relevant section extraction from documents
    - Claude API evaluation with structured output
    - Evidence extraction and categorization
    - Adaptive criticism based on multiplier

    Example:
        >>> agent = EvaluatorAgent({
        ...     "criterion_id": "prd_quality",
        ...     "criterion_name": "PRD Quality",
        ...     "weight": 0.08,
        ...     "prompt_template": "prompts/prd_evaluation.txt"
        ... })
        >>> input_data = EvaluatorInput(document=parsed_doc, criticism_multiplier=1.2)
        >>> result = await agent.execute(input_data)
        >>> print(result.output.score)
        85.0
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the evaluator agent.

        Args:
            config: Agent configuration with keys:
                - criterion_id: Unique identifier for criterion
                - criterion_name: Human-readable criterion name
                - weight: Weight in final grade (0.0-1.0)
                - prompt_template: Path to prompt template file
                - keywords: Optional list of keywords for section extraction
                - required_sections: Optional list of required section titles
        """
        super().__init__(config)

        # Criterion configuration
        self.criterion_id = config['criterion_id']
        self.criterion_name = config['criterion_name']
        self.weight = config['weight']
        self.prompt_template_path = Path(config['prompt_template'])

        # Section extraction configuration
        self.keywords = config.get('keywords', [])
        self.required_sections = config.get('required_sections', [])

        # Initialize skills
        self.llm_skill = LLMEvaluationSkill()
        self.file_ops = FileOperationsSkill()

        # Load prompt template
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        """
        Load the prompt template for this criterion.

        Returns:
            Prompt template string

        Raises:
            FileNotFoundError: If template file doesn't exist
        """
        if not self.prompt_template_path.exists():
            # Fallback to generic template
            self.logger.warning(
                f"Prompt template not found: {self.prompt_template_path}, "
                f"using generic template"
            )
            return self._get_generic_prompt_template()

        try:
            return self.file_ops.read_text(self.prompt_template_path)
        except Exception as e:
            self.logger.error(f"Failed to load prompt template: {e}")
            return self._get_generic_prompt_template()

    def _get_generic_prompt_template(self) -> str:
        """
        Get a generic fallback prompt template.

        Returns:
            Generic prompt template string
        """
        return """You are evaluating the "{criterion_name}" criterion for a software project submission.

Evaluate the provided document sections and code blocks based on the following criterion:
{criterion_name}

Provide your evaluation as a JSON object with the following structure:
{{
    "score": <float between 0-100>,
    "evidence": [<list of specific quotes or references from the document>],
    "strengths": [<list of identified strengths>],
    "weaknesses": [<list of identified weaknesses>],
    "suggestions": [<list of actionable improvement suggestions>],
    "severity": "<one of: critical, important, minor, strength>"
}}

Be thorough and specific in your evaluation. Reference concrete examples from the document.
"""

    async def execute(self, input_data: EvaluatorInput) -> AgentResult[CriterionEvaluation]:
        """
        Evaluate a single criterion against the parsed document.

        Args:
            input_data: EvaluatorInput with document and criticism multiplier

        Returns:
            AgentResult with CriterionEvaluation
        """
        self.log_execution_start(
            input_data,
            criterion=self.criterion_id,
            criticism_multiplier=input_data.criticism_multiplier,
            pages=input_data.document.total_pages
        )

        start_time = time.time()

        try:
            # Extract relevant sections from document
            relevant_content = self._extract_relevant_content(input_data.document)

            if not relevant_content.strip():
                self.logger.warning(
                    f"No relevant content found for {self.criterion_id}, "
                    f"using full document"
                )
                relevant_content = input_data.document.full_text[:10000]  # Limit to 10k chars

            # Construct evaluation prompt
            prompt = self._construct_prompt(
                relevant_content,
                input_data.criticism_multiplier
            )

            # Call Claude API
            self.logger.info(f"Calling Claude API for {self.criterion_id}")
            evaluation_response = await self.llm_skill.evaluate_with_claude(
                prompt=self.prompt_template,
                context=relevant_content,
                criticism_multiplier=input_data.criticism_multiplier
            )

            # Parse response into CriterionEvaluation
            evaluation = self._parse_evaluation_response(evaluation_response)

            # Save intermediate result
            self._save_intermediate_result(evaluation)

            execution_time = time.time() - start_time
            self.log_execution_end(
                True,
                execution_time,
                score=evaluation.score,
                severity=evaluation.severity
            )

            return AgentResult.success_result(
                output=evaluation,
                metadata={
                    "criterion_id": self.criterion_id,
                    "content_length": len(relevant_content),
                    "api_cost": evaluation_response.get('cost', 0.0)
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - start_time
            self.log_execution_end(False, execution_time)
            return self.handle_error(e)

    def _extract_relevant_content(self, document) -> str:
        """
        Extract sections and code blocks relevant to this criterion.

        Args:
            document: ParsedDocument to extract from

        Returns:
            Concatenated relevant content
        """
        relevant_parts = []

        # Extract sections matching keywords or required titles
        for section in document.structure.sections:
            if self._is_section_relevant(section):
                relevant_parts.append(f"## {section.title}\n{section.content}\n")

        # Extract relevant code blocks (if criterion is code-related)
        if self._is_code_criterion():
            for code_block in document.code_blocks:
                if len(relevant_parts) < 10:  # Limit to 10 code blocks
                    language_tag = f" ({code_block.language})" if code_block.language else ""
                    relevant_parts.append(
                        f"### Code Block{language_tag}\n```\n{code_block.content}\n```\n"
                    )

        # If no relevant sections found, use full text excerpt
        if not relevant_parts:
            return document.full_text[:5000]  # First 5000 chars

        return "\n".join(relevant_parts)

    def _is_section_relevant(self, section: Section) -> bool:
        """
        Check if a section is relevant to this criterion.

        Args:
            section: Document section

        Returns:
            True if section is relevant
        """
        title_lower = section.title.lower()

        # Check required sections
        for required in self.required_sections:
            if required.lower() in title_lower:
                return True

        # Check keywords
        for keyword in self.keywords:
            if keyword.lower() in title_lower or keyword.lower() in section.content.lower():
                return True

        return False

    def _is_code_criterion(self) -> bool:
        """
        Check if this criterion evaluates code quality.

        Returns:
            True if code-related criterion
        """
        code_criteria = [
            'code_documentation',
            'code_principles',
            'project_structure',
            'unit_tests',
            'error_handling'
        ]
        return self.criterion_id in code_criteria

    def _construct_prompt(self, content: str, criticism_multiplier: float) -> str:
        """
        Construct the full evaluation prompt.

        Args:
            content: Relevant document content
            criticism_multiplier: Criticism adjustment factor

        Returns:
            Full prompt string
        """
        # Add criticism context to prompt
        if criticism_multiplier >= 1.5:
            criticism_note = "Apply very strict evaluation standards."
        elif criticism_multiplier >= 1.2:
            criticism_note = "Apply strict evaluation standards."
        elif criticism_multiplier <= 0.6:
            criticism_note = "Apply supportive evaluation standards."
        elif criticism_multiplier <= 0.8:
            criticism_note = "Apply encouraging evaluation standards."
        else:
            criticism_note = "Apply balanced evaluation standards."

        return f"{self.prompt_template}\n\n{criticism_note}\n\n### Document Content:\n{content}"

    def _parse_evaluation_response(self, response: Dict[str, Any]) -> CriterionEvaluation:
        """
        Parse LLM response into CriterionEvaluation.

        Args:
            response: Response from LLMEvaluationSkill

        Returns:
            CriterionEvaluation object
        """
        # Response should contain parsed JSON from Claude
        evaluation_data = response.get('evaluation', {})

        return CriterionEvaluation(
            criterion_id=self.criterion_id,
            criterion_name=self.criterion_name,
            weight=self.weight,
            score=float(evaluation_data.get('score', 0.0)),
            evidence=evaluation_data.get('evidence', []),
            strengths=evaluation_data.get('strengths', []),
            weaknesses=evaluation_data.get('weaknesses', []),
            suggestions=evaluation_data.get('suggestions', []),
            severity=evaluation_data.get('severity', 'minor')
        )

    def _save_intermediate_result(self, evaluation: CriterionEvaluation) -> None:
        """
        Save evaluation to workspace for debugging and recovery.

        Args:
            evaluation: Evaluation result to save
        """
        try:
            output_dir = Path("workspace/intermediate/evaluations")
            self.file_ops.ensure_dir(output_dir)

            output_file = output_dir / f"{self.criterion_id}.json"
            self.file_ops.write_json(output_file, evaluation.model_dump())

            self.logger.debug(f"Saved intermediate result to {output_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save intermediate result: {e}")
