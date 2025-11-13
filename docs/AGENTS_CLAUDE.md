# CLAUDE.MD - Agent Development Guide
# Auto-Grading System with Claude Code Agents

**Purpose:** Train Claude Code on how to build, test, and coordinate specialized agents for the auto-grading system.

---

## Project Identity

### What We're Building
A **multi-agent auto-grading system** where specialized AI agents work together to grade M.Sc. Computer Science projects. Each agent is an autonomous component with clear responsibilities, and agents communicate through well-defined interfaces.

### Why Agents?
Traditional monolithic approach:
```
[PDF Input] → [Giant Grading Function] → [Report Output]
```

Agent-based approach:
```
[PDF Input] → [Parser Agent] → [Parsed Document]
                                       ↓
[Orchestrator Agent] ← [7x Evaluator Agents in parallel]
          ↓
[Scoring Agent] → [Reporter Agent] → [Report Output]
```

**Benefits:**
- **Modularity:** Each agent can be developed, tested, and deployed independently
- **Parallelism:** Multiple EvaluatorAgents run simultaneously
- **Maintainability:** Adding new criteria = adding new EvaluatorAgent instance
- **Resilience:** One agent failure doesn't crash entire system
- **Clarity:** Clear separation of concerns, easy to understand

---

## Core Concepts

### 1. Agents vs. Skills

**Agent:**
- An autonomous component that orchestrates work
- Has clear inputs and outputs
- Makes decisions
- Coordinates with other agents
- Maintains execution context

**Skill:**
- A reusable function or module
- Stateless (no memory between calls)
- Pure logic (same input → same output)
- Used BY agents to accomplish tasks
- Shared across multiple agents

**Example:**
```python
# SKILL: PDFProcessingSkill (reusable function)
def parse_pdf(pdf_path: Path) -> ParsedDocument:
    """Pure function - no state, just logic."""
    return parsed_document

# AGENT: ParserAgent (autonomous component)
class ParserAgent:
    """Agent that orchestrates PDF parsing."""
    
    def __init__(self):
        self.skill = PDFProcessingSkill()
        self.state = {}
    
    async def execute(self, pdf_path: Path) -> AgentResult:
        # Validate input
        if not self._validate_pdf(pdf_path):
            return AgentResult(error="Invalid PDF")
        
        # Use skill to do work
        parsed = self.skill.parse_pdf(pdf_path)
        
        # Save result for other agents
        output_path = self._save_to_json(parsed)
        
        # Return result with metadata
        return AgentResult(
            success=True,
            output_path=output_path,
            metadata={"pages": parsed.total_pages}
        )
```

### 2. Agent Lifecycle

```
1. Initialize (load config, set up skills)
2. Receive Task (inputs from orchestrator or previous agent)
3. Validate Inputs (check preconditions)
4. Execute Work (use skills to accomplish task)
5. Produce Outputs (structured data for next agent)
6. Return Result (success/failure + outputs + metadata)
7. Cleanup (release resources)
```

### 3. Agent Communication

**Preferred: JSON Files (Structured)**
```python
# Agent A writes output
result = {"score": 85, "evidence": ["Page 5: ..."]}
Path("outputs/evaluation.json").write_text(json.dumps(result))

# Agent B reads input
data = json.loads(Path("outputs/evaluation.json").read_text())
```

**Alternative: Return Values (Simple)**
```python
# For small, simple data
result = await parser_agent.execute(pdf_path)
evaluation = await evaluator_agent.execute(result.parsed_document)
```

**Anti-Pattern: Global State**
```python
# ❌ DON'T DO THIS
global_state = {"parsed_doc": None}

class ParserAgent:
    def execute(self):
        global global_state
        global_state["parsed_doc"] = self.parse()  # BAD!
```

---

## Agent Development Patterns

### Pattern 1: Base Agent Class

All agents inherit from this:

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TInput = TypeVar('TInput')
TOutput = TypeVar('TOutput')

class BaseAgent(ABC, Generic[TInput, TOutput]):
    """Base class for all agents."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    async def execute(self, input_data: TInput) -> AgentResult[TOutput]:
        """Main execution method - implement in subclasses."""
        pass
    
    def validate_input(self, input_data: TInput) -> bool:
        """Override to add input validation."""
        return True
    
    def handle_error(self, error: Exception) -> AgentResult[TOutput]:
        """Standard error handling."""
        self.logger.error(f"Agent failed: {error}", exc_info=True)
        return AgentResult(
            success=False,
            error=str(error),
            output=None
        )
```

### Pattern 2: Agent Result Standard

All agents return this structure:

```python
@dataclass
class AgentResult(Generic[T]):
    """Standard result from any agent."""
    success: bool
    output: Optional[T] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    
    def __post_init__(self):
        if not self.success and self.error is None:
            raise ValueError("Failed result must have error message")
```

### Pattern 3: Skill Integration

Agents use skills via composition:

```python
class ParserAgent(BaseAgent[Path, ParsedDocument]):
    """Agent that parses PDF submissions."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        # Initialize skills this agent needs
        self.pdf_skill = PDFProcessingSkill(config.get("pdf_config"))
        self.code_skill = CodeAnalysisSkill()
        self.cache_skill = CachingSkill(cache_dir=".cache")
    
    async def execute(self, pdf_path: Path) -> AgentResult[ParsedDocument]:
        start_time = time.time()
        
        try:
            # Check cache first
            if cached := self.cache_skill.get(pdf_path):
                self.logger.info(f"Using cached parsing for {pdf_path.name}")
                return AgentResult(
                    success=True,
                    output=cached,
                    metadata={"from_cache": True}
                )
            
            # Parse PDF using skill
            parsed = self.pdf_skill.parse_pdf(pdf_path)
            
            # Analyze code blocks using skill
            for code_block in parsed.code_blocks:
                code_block.language = self.code_skill.detect_language(
                    code_block.content
                )
            
            # Cache result
            self.cache_skill.set(pdf_path, parsed)
            
            return AgentResult(
                success=True,
                output=parsed,
                metadata={
                    "pages": parsed.total_pages,
                    "code_blocks": len(parsed.code_blocks)
                },
                execution_time=time.time() - start_time
            )
        
        except Exception as e:
            return self.handle_error(e)
```

### Pattern 4: Parallel Agent Execution

Orchestrator spawns multiple agents in parallel:

```python
class OrchestratorAgent(BaseAgent[GradingRequest, GradingResult]):
    """Coordinates all other agents."""
    
    async def execute(self, request: GradingRequest) -> AgentResult[GradingResult]:
        # Step 1: Parse PDF (sequential - needed by everyone)
        parser = ParserAgent(self.config["parser"])
        parse_result = await parser.execute(request.pdf_path)
        
        if not parse_result.success:
            return self.handle_error(Exception(parse_result.error))
        
        parsed_doc = parse_result.output
        
        # Step 2: Spawn multiple evaluators in parallel
        evaluator_configs = self.config["evaluators"]
        
        async def evaluate_criterion(criterion_config):
            agent = EvaluatorAgent(criterion_config)
            return await agent.execute(EvaluatorInput(
                document=parsed_doc,
                criticism_multiplier=request.criticism_multiplier
            ))
        
        # Run all evaluations concurrently
        evaluation_results = await asyncio.gather(
            *[evaluate_criterion(cfg) for cfg in evaluator_configs],
            return_exceptions=True  # Don't fail if one evaluator fails
        )
        
        # Collect successful evaluations
        evaluations = []
        for result in evaluation_results:
            if isinstance(result, Exception):
                self.logger.error(f"Evaluator failed: {result}")
                # Create error placeholder
                evaluations.append(self._create_error_evaluation(result))
            elif result.success:
                evaluations.append(result.output)
        
        # Step 3: Calculate scores (sequential - needs all evaluations)
        scorer = ScoringAgent(self.config["scoring"])
        score_result = await scorer.execute(ScoringInput(
            evaluations=evaluations,
            criticism_multiplier=request.criticism_multiplier
        ))
        
        # Step 4: Generate reports (sequential - needs final score)
        reporter = ReporterAgent(self.config["reporting"])
        report_result = await reporter.execute(ReportInput(
            grading_result=score_result.output
        ))
        
        return AgentResult(
            success=True,
            output=score_result.output,
            metadata={
                "report_paths": report_result.output.report_paths,
                "evaluations_completed": len(evaluations),
                "evaluations_failed": len([r for r in evaluation_results if isinstance(r, Exception)])
            }
        )
```

---

## Skill Development Patterns

### Pattern 1: Stateless Skills

**Good (Stateless):**
```python
class PDFProcessingSkill:
    """Stateless PDF processing functions."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        # Initialize tools, but don't store state
        self.pymupdf = fitz
        self.pdfplumber = pdfplumber
    
    def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        """Pure function - same input always gives same output."""
        # No instance variables modified here
        text = self._extract_text(pdf_path)
        structure = self._extract_structure(pdf_path)
        return ParsedDocument(text=text, structure=structure)
```

**Bad (Stateful):**
```python
class PDFProcessingSkill:
    """❌ BAD: Stores state between calls."""
    
    def __init__(self):
        self.last_parsed_doc = None  # ❌ State!
        self.parse_count = 0  # ❌ State!
    
    def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        self.parse_count += 1  # ❌ Mutating state
        self.last_parsed_doc = self._do_parse(pdf_path)  # ❌ Storing state
        return self.last_parsed_doc
```

### Pattern 2: Skill Function Signatures

Always use clear, typed signatures:

```python
class LLMEvaluationSkill:
    """Claude API interaction skill."""
    
    def evaluate_with_claude(
        self,
        prompt: str,
        context: str,
        *,  # Force keyword arguments
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.0
    ) -> EvaluationResponse:
        """
        Evaluate content using Claude API.
        
        Args:
            prompt: Evaluation prompt template
            context: Content to evaluate
            model: Claude model to use
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
        
        Returns:
            EvaluationResponse with structured data
        
        Raises:
            APIError: If Claude API call fails
            ValidationError: If response format invalid
        
        Example:
            >>> skill = LLMEvaluationSkill()
            >>> response = skill.evaluate_with_claude(
            ...     prompt="Evaluate this README",
            ...     context=readme_text
            ... )
            >>> print(response.score)
            85.0
        """
        # Implementation
```

### Pattern 3: Error Handling in Skills

Skills should raise specific exceptions:

```python
class PDFProcessingSkill:
    
    def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
        """Parse PDF with fallback engines."""
        
        # Validate input
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")
        
        if pdf_path.stat().st_size > 50 * 1024 * 1024:
            raise ValueError(f"PDF too large: {pdf_path.stat().st_size / 1024 / 1024:.1f}MB")
        
        # Try primary engine
        try:
            return self._parse_with_pymupdf(pdf_path)
        except Exception as e:
            self.logger.warning(f"PyMuPDF failed: {e}, trying fallback")
        
        # Try fallback engine
        try:
            return self._parse_with_pdfplumber(pdf_path)
        except Exception as e:
            self.logger.error(f"All parsers failed for {pdf_path.name}")
            raise PDFParsingError(
                f"Could not parse PDF: {pdf_path.name}"
            ) from e
```

---

## Testing Strategies

### Testing Agents

```python
import pytest
from unittest.mock import Mock, AsyncMock

@pytest.mark.asyncio
async def test_parser_agent_success():
    """Test ParserAgent with valid PDF."""
    # Arrange
    config = {"pdf_config": {"engine": "pymupdf"}}
    agent = ParserAgent(config)
    test_pdf = Path("tests/fixtures/sample_project.pdf")
    
    # Act
    result = await agent.execute(test_pdf)
    
    # Assert
    assert result.success
    assert result.output is not None
    assert result.output.total_pages > 0
    assert result.error is None

@pytest.mark.asyncio
async def test_parser_agent_invalid_pdf():
    """Test ParserAgent with invalid PDF."""
    # Arrange
    agent = ParserAgent({})
    invalid_pdf = Path("tests/fixtures/corrupted.pdf")
    
    # Act
    result = await agent.execute(invalid_pdf)
    
    # Assert
    assert not result.success
    assert result.error is not None
    assert "parse" in result.error.lower()

@pytest.mark.asyncio
async def test_evaluator_agent_with_mock_llm():
    """Test EvaluatorAgent without real API calls."""
    # Arrange
    config = {"criterion": "prd_quality", "weight": 0.08}
    agent = EvaluatorAgent(config)
    
    # Mock the LLM skill
    agent.llm_skill.evaluate_with_claude = AsyncMock(return_value={
        "score": 85.0,
        "evidence": ["Page 5: PRD section found"],
        "strengths": ["Clear problem statement"],
        "weaknesses": ["Missing competitive analysis"],
        "suggestions": ["Add market analysis"],
        "severity": "minor"
    })
    
    # Act
    parsed_doc = ParsedDocument(...)  # Create test document
    result = await agent.execute(EvaluatorInput(
        document=parsed_doc,
        criticism_multiplier=1.0
    ))
    
    # Assert
    assert result.success
    assert result.output.score == 85.0
    assert agent.llm_skill.evaluate_with_claude.called
```

### Testing Skills

```python
def test_pdf_processing_skill_basic():
    """Test PDF parsing with sample file."""
    skill = PDFProcessingSkill()
    pdf_path = Path("tests/fixtures/sample.pdf")
    
    parsed = skill.parse_pdf(pdf_path)
    
    assert parsed.total_pages == 3
    assert len(parsed.text_content) == 3
    assert "README" in parsed.text_content[1]

def test_pdf_processing_skill_code_detection():
    """Test code block detection."""
    skill = PDFProcessingSkill()
    pdf_path = Path("tests/fixtures/with_code.pdf")
    
    parsed = skill.parse_pdf(pdf_path)
    
    assert len(parsed.code_blocks) > 0
    assert parsed.code_blocks[0].language == "python"

def test_llm_evaluation_skill_structured_response():
    """Test LLM skill returns structured data."""
    skill = LLMEvaluationSkill()
    
    # This would use a real API call in integration tests
    # For unit tests, mock the Anthropic client
    skill.client = Mock()
    skill.client.messages.create.return_value = Mock(
        content=[Mock(text='{"score": 75, "evidence": [...]}')]
    )
    
    response = skill.evaluate_with_claude(
        prompt="Test prompt",
        context="Test context"
    )
    
    assert response.score == 75
    assert isinstance(response.evidence, list)
```

### Integration Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_grading_workflow():
    """Test complete orchestration from PDF to report."""
    # Arrange
    orchestrator = OrchestratorAgent(load_config("config/test_config.yaml"))
    request = GradingRequest(
        pdf_path=Path("tests/fixtures/complete_project.pdf"),
        self_grade=85
    )
    
    # Act
    result = await orchestrator.execute(request)
    
    # Assert
    assert result.success
    assert result.output.final_score > 0
    assert result.output.final_score <= 100
    assert len(result.output.evaluations) >= 7  # At least 7 criteria
    assert Path(result.metadata["report_paths"]["markdown"]).exists()
```

---

## Best Practices

### 1. Agent Responsibilities

**DO:**
- ✅ Keep agents focused on ONE clear responsibility
- ✅ Make agent inputs/outputs explicit (Pydantic models)
- ✅ Log all agent actions with structured logging
- ✅ Handle errors gracefully and return error results
- ✅ Document what the agent does and why

**DON'T:**
- ❌ Create "god agents" that do everything
- ❌ Share state between agents via global variables
- ❌ Crash the whole system if one agent fails
- ❌ Mix business logic with orchestration logic

### 2. Skill Design

**DO:**
- ✅ Keep skills stateless and pure
- ✅ Make skills reusable across multiple agents
- ✅ Use clear function signatures with type hints
- ✅ Include docstrings with examples
- ✅ Raise specific exceptions, not generic ones

**DON'T:**
- ❌ Store state in skill instances
- ❌ Make skills dependent on each other
- ❌ Put agent logic in skills
- ❌ Use vague function names like `process()` or `handle()`

### 3. Configuration

**DO:**
- ✅ Use YAML files for configuration
- ✅ Allow environment variable overrides
- ✅ Validate config on load (Pydantic)
- ✅ Provide sensible defaults
- ✅ Document all config options

**Example:**
```yaml
# config/orchestrator.yaml
orchestrator:
  max_parallel_evaluations: 10
  timeout_seconds: 300
  retry_failed_evaluations: true

parser:
  engine: "pymupdf"
  fallback_engine: "pdfplumber"
  cache_enabled: true

evaluators:
  - criterion: "prd_quality"
    weight: 0.08
    prompt_template: "prompts/prd_evaluation.txt"
  - criterion: "code_structure"
    weight: 0.10
    prompt_template: "prompts/code_structure.txt"
```

### 4. Error Handling

**Levels of Error Handling:**

1. **Skill Level:** Raise specific exceptions
```python
def parse_pdf(self, pdf_path: Path) -> ParsedDocument:
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
```

2. **Agent Level:** Catch exceptions, return error result
```python
async def execute(self, input_data: TInput) -> AgentResult[TOutput]:
    try:
        result = self._do_work(input_data)
        return AgentResult(success=True, output=result)
    except Exception as e:
        return self.handle_error(e)
```

3. **Orchestrator Level:** Graceful degradation
```python
evaluation_results = await asyncio.gather(
    *evaluator_tasks,
    return_exceptions=True
)

# Continue with successful evaluations
successful = [r for r in evaluation_results if not isinstance(r, Exception)]
```

### 5. Logging

**Structured Logging:**
```python
class EvaluatorAgent(BaseAgent):
    
    async def execute(self, input_data: EvaluatorInput) -> AgentResult:
        self.logger.info(
            "Starting evaluation",
            extra={
                "criterion": self.config["criterion"],
                "document_pages": input_data.document.total_pages,
                "criticism_multiplier": input_data.criticism_multiplier
            }
        )
        
        result = await self._evaluate()
        
        self.logger.info(
            "Evaluation complete",
            extra={
                "criterion": self.config["criterion"],
                "score": result.score,
                "execution_time": result.execution_time,
                "tokens_used": result.metadata.get("tokens_used")
            }
        )
        
        return AgentResult(success=True, output=result)
```

---

## Common Pitfalls

### Pitfall 1: Circular Dependencies
```python
# ❌ DON'T
from agents.evaluator_agent import EvaluatorAgent

class OrchestratorAgent:
    def __init__(self):
        self.evaluator = EvaluatorAgent()  # Imports create cycle

# ✅ DO
class OrchestratorAgent:
    def _create_evaluator(self, config):
        # Import locally to avoid circular dependencies
        from agents.evaluator_agent import EvaluatorAgent
        return EvaluatorAgent(config)
```

### Pitfall 2: Blocking Operations in Async Agents
```python
# ❌ DON'T
async def execute(self, input_data):
    result = self.blocking_skill.parse()  # Blocks event loop!
    return result

# ✅ DO
async def execute(self, input_data):
    # Run blocking operations in executor
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(
        None,
        self.blocking_skill.parse,
        input_data
    )
    return result
```

### Pitfall 3: Not Handling Agent Failures
```python
# ❌ DON'T
results = await asyncio.gather(*agent_tasks)  # Raises if any fail

# ✅ DO
results = await asyncio.gather(*agent_tasks, return_exceptions=True)
for result in results:
    if isinstance(result, Exception):
        # Handle failure gracefully
```

---

## Quick Reference

### Agent Template
```python
class MyAgent(BaseAgent[InputType, OutputType]):
    """Agent that does X."""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.skill = MySkill(config.get("skill_config"))
    
    async def execute(self, input_data: InputType) -> AgentResult[OutputType]:
        try:
            # Validate
            if not self.validate_input(input_data):
                return AgentResult(success=False, error="Invalid input")
            
            # Work
            result = await self._do_work(input_data)
            
            # Return
            return AgentResult(success=True, output=result)
        except Exception as e:
            return self.handle_error(e)
    
    async def _do_work(self, input_data: InputType) -> OutputType:
        # Implementation
        pass
```

### Skill Template
```python
class MySkill:
    """Skill that does Y."""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
    
    def do_something(
        self,
        input: str,
        *,
        option: bool = False
    ) -> Result:
        """
        Do something useful.
        
        Args:
            input: Description
            option: Description
        
        Returns:
            Result object
        
        Example:
            >>> skill = MySkill()
            >>> result = skill.do_something("test")
        """
        # Implementation
        return Result(...)
```

---

**Last Updated:** November 2025  
**For Questions:** See AGENTS_PRD.md and AGENTS_PLANNING.md
