"""
Orchestrator agent for coordinating the entire grading workflow.

This agent manages the complete grading pipeline, spawning and coordinating
all specialized agents to evaluate a submission.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List
import time

from models.agent_result import AgentResult
from models.core import GradingRequest, GradingResult, CriterionEvaluation
from models.io import EvaluatorInput, ScoringInput
from agents.base_agent import BaseAgent
from agents.validation_agent import ValidationAgent
from agents.parser_agent import ParserAgent
from agents.evaluator_agent import EvaluatorAgent
from agents.scoring_agent import ScoringAgent
from agents.reporter_agent import ReporterAgent
from agents.cost_tracker_agent import CostTrackerAgent
from config.config_loader import ConfigLoader


class OrchestratorAgent(BaseAgent[GradingRequest, GradingResult]):
    """
    Master agent that orchestrates the entire grading workflow.

    Workflow:
    1. Validate input (ValidationAgent)
    2. Parse PDF (ParserAgent)
    3. Calculate criticism multiplier based on self-grade
    4. Spawn EvaluatorAgents in parallel for all criteria (asyncio.gather)
    5. Aggregate evaluations (ScoringAgent)
    6. Generate reports (ReporterAgent)
    7. Track costs (CostTrackerAgent)

    Features:
    - Parallel evaluation execution
    - Error recovery and partial results
    - Cost tracking throughout pipeline
    - Comprehensive logging

    Example:
        >>> orchestrator = OrchestratorAgent({})
        >>> request = GradingRequest(
        ...     pdf_path=Path("submission.pdf"),
        ...     self_grade=85
        ... )
        >>> result = await orchestrator.execute(request)
        >>> print(result.output.final_score)
        82.5
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the orchestrator agent.

        Args:
            config: Agent configuration (usually empty, loads from config/default.yaml)
        """
        super().__init__(config)

        # Load full system configuration
        self.config_loader = ConfigLoader()
        self.system_config = self.config_loader.load_config()

        # Initialize sub-agents
        self.validation_agent = ValidationAgent({})
        self.parser_agent = ParserAgent(self.system_config.parser)
        self.scoring_agent = ScoringAgent(self.system_config.scoring)
        self.reporter_agent = ReporterAgent(self.system_config.reporter)
        self.cost_tracker = CostTrackerAgent(self.system_config.cost_tracking)

        # Create evaluator agents for each criterion
        self.evaluator_agents: Dict[str, EvaluatorAgent] = {}
        self._initialize_evaluators()

    def _initialize_evaluators(self) -> None:
        """
        Create an EvaluatorAgent for each configured criterion.
        """
        for criterion_config in self.system_config.evaluators:
            criterion_id = criterion_config['criterion']
            self.evaluator_agents[criterion_id] = EvaluatorAgent(criterion_config)

        self.logger.info(
            f"Initialized {len(self.evaluator_agents)} evaluator agents",
            extra={"criteria": list(self.evaluator_agents.keys())}
        )

    async def execute(self, request: GradingRequest) -> AgentResult[GradingResult]:
        """
        Execute the complete grading workflow.

        Args:
            request: Grading request with PDF path and self-grade

        Returns:
            AgentResult with complete GradingResult
        """
        self.log_execution_start(
            request,
            pdf=request.pdf_path.name,
            self_grade=request.self_grade
        )

        workflow_start = time.time()

        try:
            # Phase 1: Validate input
            self.logger.info("Phase 1: Validating grading request")
            validation_result = await self.validation_agent.execute(request)

            if not validation_result.success or not validation_result.output.is_valid:
                error_msg = "; ".join(validation_result.output.errors)
                self.logger.error(f"Validation failed: {error_msg}")
                return AgentResult.failure_result(
                    error=f"Validation failed: {error_msg}",
                    metadata={"phase": "validation"}
                )

            # Phase 2: Parse PDF
            self.logger.info("Phase 2: Parsing PDF document")
            parse_result = await self.parser_agent.execute(request.pdf_path)

            if not parse_result.success:
                return AgentResult.failure_result(
                    error=f"PDF parsing failed: {parse_result.error}",
                    metadata={"phase": "parsing"}
                )

            parsed_document = parse_result.output
            self.logger.info(
                f"Successfully parsed {parsed_document.total_pages} pages",
                extra={
                    "code_blocks": len(parsed_document.code_blocks),
                    "sections": len(parsed_document.structure.sections)
                }
            )

            # Phase 3: Calculate criticism multiplier
            criticism_multiplier = self._calculate_criticism_multiplier(request.self_grade)
            self.logger.info(
                f"Phase 3: Criticism multiplier = {criticism_multiplier:.2f}x "
                f"(self-grade: {request.self_grade})"
            )

            # Phase 4: Parallel evaluation of all criteria
            self.logger.info(
                f"Phase 4: Spawning {len(self.evaluator_agents)} evaluator agents in parallel"
            )
            evaluation_results = await self._run_parallel_evaluations(
                parsed_document,
                criticism_multiplier
            )

            # Check for evaluation failures
            successful_evaluations = [r for r in evaluation_results if r.success]
            failed_evaluations = [r for r in evaluation_results if not r.success]

            if failed_evaluations:
                self.logger.warning(
                    f"{len(failed_evaluations)} evaluations failed, "
                    f"continuing with {len(successful_evaluations)} successful ones"
                )

            if not successful_evaluations:
                return AgentResult.failure_result(
                    error="All criterion evaluations failed",
                    metadata={"phase": "evaluation", "failures": len(failed_evaluations)}
                )

            # Extract evaluations and track costs
            evaluations = [r.output for r in successful_evaluations]
            for result in successful_evaluations:
                api_cost = result.metadata.get('api_cost', 0.0)
                if api_cost > 0:
                    # Track cost (would need token info from metadata)
                    self.cost_tracker.track_api_call(
                        result.output.criterion_id,
                        input_tokens=1000,  # Placeholder - should come from metadata
                        output_tokens=500,   # Placeholder - should come from metadata
                        cost=api_cost
                    )

            self.logger.info(f"Completed {len(evaluations)} criterion evaluations")

            # Phase 5: Calculate final score
            self.logger.info("Phase 5: Calculating final score")
            scoring_input = ScoringInput(
                evaluations=evaluations,
                criticism_multiplier=criticism_multiplier,
                self_grade=request.self_grade
            )
            scoring_result = await self.scoring_agent.execute(scoring_input)

            if not scoring_result.success:
                return AgentResult.failure_result(
                    error=f"Scoring failed: {scoring_result.error}",
                    metadata={"phase": "scoring"}
                )

            grading_result = scoring_result.output
            grading_result.submission_id = self._generate_submission_id(request)
            grading_result.processing_time_seconds = time.time() - workflow_start

            self.logger.info(
                f"Final score: {grading_result.final_score:.2f} "
                f"(self-grade: {request.self_grade})"
            )

            # Phase 6: Generate reports
            self.logger.info("Phase 6: Generating reports")
            report_result = await self.reporter_agent.execute(grading_result)

            if not report_result.success:
                self.logger.warning(f"Report generation failed: {report_result.error}")
                # Continue anyway - we have the grading result
            else:
                self.logger.info(
                    f"Generated reports: {list(report_result.output.paths.keys())}"
                )

            # Phase 7: Generate cost report
            self.logger.info("Phase 7: Generating cost report")
            cost_result = await self.cost_tracker.execute(grading_result.submission_id)

            if cost_result.success:
                self.logger.info(
                    f"Total cost: ${cost_result.output.total_cost:.4f} "
                    f"({cost_result.output.api_calls} API calls)"
                )

            execution_time = time.time() - workflow_start
            self.log_execution_end(
                True,
                execution_time,
                final_score=grading_result.final_score,
                evaluations=len(evaluations)
            )

            return AgentResult.success_result(
                output=grading_result,
                metadata={
                    "total_evaluations": len(evaluations),
                    "failed_evaluations": len(failed_evaluations),
                    "criticism_multiplier": criticism_multiplier,
                    "total_cost": cost_result.output.total_cost if cost_result.success else 0.0,
                    "reports": report_result.output.paths if report_result.success else {}
                },
                execution_time=execution_time
            )

        except Exception as e:
            execution_time = time.time() - workflow_start
            self.log_execution_end(False, execution_time)
            return self.handle_error(e)

    def _calculate_criticism_multiplier(self, self_grade: int) -> float:
        """
        Calculate criticism multiplier based on self-assessed grade.

        Higher self-grades → stricter evaluation (multiplier > 1.0)
        Lower self-grades → more supportive evaluation (multiplier < 1.0)

        Args:
            self_grade: Student's self-assessed grade (0-100)

        Returns:
            Criticism multiplier (0.6 to 1.5)
        """
        if self_grade >= 90:
            return 1.5  # Very strict for high self-assessment
        elif self_grade >= 80:
            return 1.2  # Strict
        elif self_grade >= 70:
            return 1.0  # Balanced
        elif self_grade >= 60:
            return 0.8  # Encouraging
        else:
            return 0.6  # Very supportive

    async def _run_parallel_evaluations(
        self,
        document,
        criticism_multiplier: float
    ) -> List[AgentResult[CriterionEvaluation]]:
        """
        Run all criterion evaluations in parallel.

        Args:
            document: ParsedDocument to evaluate
            criticism_multiplier: Criticism adjustment factor

        Returns:
            List of AgentResults from evaluators (both successful and failed)
        """
        # Create evaluation tasks for all criteria
        evaluation_tasks = []

        for criterion_id, evaluator in self.evaluator_agents.items():
            evaluator_input = EvaluatorInput(
                document=document,
                criticism_multiplier=criticism_multiplier,
                criterion_config={}
            )

            # Create async task
            task = evaluator.execute(evaluator_input)
            evaluation_tasks.append(task)

        # Run all evaluations in parallel
        self.logger.info(f"Executing {len(evaluation_tasks)} evaluations in parallel")
        results = await asyncio.gather(*evaluation_tasks, return_exceptions=True)

        # Convert exceptions to failed AgentResults
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                criterion_id = list(self.evaluator_agents.keys())[i]
                self.logger.error(
                    f"Evaluation failed for {criterion_id}: {result}",
                    exc_info=result
                )
                processed_results.append(
                    AgentResult.failure_result(
                        error=str(result),
                        metadata={"criterion": criterion_id}
                    )
                )
            else:
                processed_results.append(result)

        return processed_results

    def _generate_submission_id(self, request: GradingRequest) -> str:
        """
        Generate a unique submission ID.

        Args:
            request: Grading request

        Returns:
            Submission ID string
        """
        import hashlib
        from datetime import datetime

        # Use PDF filename + timestamp for ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_name = request.pdf_path.stem

        return f"{pdf_name}_{timestamp}"

    def reset_cost_tracker(self) -> None:
        """Reset cost tracking for new submission batch."""
        self.cost_tracker.reset()
        self.logger.info("Cost tracker reset for new batch")

    async def process_batch(
        self,
        requests: List[GradingRequest]
    ) -> List[AgentResult[GradingResult]]:
        """
        Process multiple grading requests in sequence.

        Args:
            requests: List of grading requests

        Returns:
            List of grading results
        """
        self.logger.info(f"Processing batch of {len(requests)} submissions")
        results = []

        for i, request in enumerate(requests, 1):
            self.logger.info(f"Processing submission {i}/{len(requests)}")

            try:
                result = await self.execute(request)
                results.append(result)

                if result.success:
                    self.logger.info(
                        f"Submission {i} complete: "
                        f"Score {result.output.final_score:.2f}"
                    )
                else:
                    self.logger.error(
                        f"Submission {i} failed: {result.error}"
                    )

            except Exception as e:
                self.logger.error(
                    f"Submission {i} failed with exception: {e}",
                    exc_info=True
                )
                results.append(
                    AgentResult.failure_result(
                        error=str(e),
                        metadata={"submission_index": i}
                    )
                )

        # Generate batch summary
        successful = sum(1 for r in results if r.success)
        self.logger.info(
            f"Batch complete: {successful}/{len(requests)} successful",
            extra={
                "success_rate": f"{successful/len(requests)*100:.1f}%",
                "total_cost": self.cost_tracker.get_total_cost()
            }
        )

        return results
