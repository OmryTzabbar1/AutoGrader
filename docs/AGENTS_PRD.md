# Product Requirements Document (PRD)
# Claude Code Agents & Skills for Auto-Grading System

**Version:** 1.0  
**Author:** Auto-Grading System Team  
**Date:** November 2025  
**Status:** Draft

---

## 1. Project Overview & Background

### 1.1 Context
We need to implement the auto-grading system using **Claude Code agents** - specialized AI assistants that can autonomously execute tasks within the development workflow. Each agent will be responsible for specific aspects of the grading pipeline, and each will have access to custom **skills** (reusable capabilities).

### 1.2 Problem Statement
Building a complex auto-grading system requires:
- **Specialized expertise** in different domains (PDF parsing, LLM evaluation, report generation)
- **Parallel execution** of independent tasks (evaluating multiple criteria simultaneously)
- **Consistent behavior** across multiple grading sessions
- **Modular architecture** that allows independent development and testing

Traditional monolithic approaches are difficult to:
- Develop incrementally with clear separation of concerns
- Test individual components in isolation
- Scale across multiple submissions
- Maintain and extend with new criteria or features

### 1.3 Solution
Create a **multi-agent system** in Claude Code where:
- Each **agent** is a specialized AI assistant with a clear responsibility
- Each **skill** is a reusable capability that agents can invoke
- Agents communicate through well-defined interfaces (files, APIs, data structures)
- The system orchestrates agents to complete the full grading workflow

### 1.4 Target Users
- **Primary:** Developers building the auto-grading system
- **Secondary:** System maintainers and extenders
- **Tertiary:** Instructors using the final system (indirectly)

### 1.5 Success Metrics
- Agent development time: <8 hours per agent
- Code reusability: 70%+ of code in shared skills
- Test coverage: 85%+ per agent
- Inter-agent communication latency: <1 second
- System reliability: 99%+ successful grading runs

---

## 2. Objectives & Goals

### 2.1 Primary Objectives
1. Decompose the auto-grading system into independent, testable agents
2. Create reusable skills that multiple agents can leverage
3. Implement agent orchestration for the complete grading workflow
4. Enable parallel execution of criterion evaluations
5. Maintain clear separation of concerns and single responsibility

### 2.2 Secondary Objectives
1. Create templates for adding new criterion evaluators easily
2. Build monitoring and observability into agent execution
3. Enable graceful degradation when individual agents fail
4. Support both synchronous and asynchronous execution modes
5. Create comprehensive documentation for each agent and skill

---

## 3. Functional Requirements

### 3.1 Agent Architecture

**FR-1.1:** System SHALL implement the following specialized agents:
1. **OrchestratorAgent**: Coordinates the entire grading workflow
2. **ParserAgent**: Extracts content from PDF submissions
3. **EvaluatorAgent**: Evaluates submissions against specific criteria
4. **ScoringAgent**: Calculates final scores with weighted averaging
5. **ReporterAgent**: Generates comprehensive grading reports
6. **ValidationAgent**: Validates inputs and outputs
7. **CostTrackerAgent**: Monitors API usage and costs

**FR-1.2:** Each agent SHALL have:
- Clear input/output contracts (defined with Pydantic models)
- Dedicated configuration file
- Independent test suite
- Error handling and recovery logic
- Logging and observability hooks
- Documentation of responsibilities and dependencies

**FR-1.3:** Agents SHALL communicate via:
- Structured JSON files for large data (parsed PDFs, evaluation results)
- Return values for small data (scores, flags)
- Message queues for asynchronous operations (future)
- Shared state manager for coordination

### 3.2 Skills Architecture

**FR-2.1:** System SHALL implement the following reusable skills:

#### Core Skills
1. **PDFProcessingSkill**: PDF parsing, text extraction, structure detection
2. **LLMEvaluationSkill**: Claude API interaction, prompt engineering, response parsing
3. **DataValidationSkill**: Input validation, schema checking, sanitization
4. **FileOperationsSkill**: Reading/writing JSON, YAML, Markdown files
5. **ReportingSkill**: Template rendering, format conversion (MD→PDF)

#### Specialized Skills
6. **CodeAnalysisSkill**: Detect code blocks, analyze structure, identify patterns
7. **DiagramExtractionSkill**: Extract and categorize diagrams from PDFs
8. **TableParsingSkill**: Parse tables, extract structured data
9. **CostCalculationSkill**: Track tokens, calculate costs, monitor budgets
10. **CachingSkill**: Cache parsed PDFs, LLM responses, intermediate results

**FR-2.2:** Each skill SHALL:
- Be importable as a Python module
- Have clear function signatures with type hints
- Include docstrings with usage examples
- Have independent unit tests
- Be version-controlled with semantic versioning
- Document all dependencies

**FR-2.3:** Skills SHALL be:
- Stateless (no internal state between calls)
- Idempotent (same inputs → same outputs)
- Thread-safe (for parallel agent execution)
- Testable in isolation

### 3.3 Agent Definitions

#### Agent 1: OrchestratorAgent
**Responsibility:** Coordinate the complete grading workflow

**Inputs:**
- PDF file path
- Self-assessed grade (0-100)
- Configuration settings

**Outputs:**
- Complete GradingResult object
- Generated report files
- Execution summary

**Process:**
1. Validate inputs using ValidationAgent
2. Delegate PDF parsing to ParserAgent
3. Calculate criticism multiplier
4. Spawn multiple EvaluatorAgents (one per criterion category)
5. Collect evaluation results
6. Delegate scoring to ScoringAgent
7. Delegate report generation to ReporterAgent
8. Track costs via CostTrackerAgent
9. Return final result

**Skills Used:**
- FileOperationsSkill
- DataValidationSkill
- CostCalculationSkill

---

#### Agent 2: ParserAgent
**Responsibility:** Extract structured content from PDF submissions

**Inputs:**
- PDF file path
- Parsing configuration (engines, options)

**Outputs:**
- ParsedDocument object (JSON)
- Extracted images (if applicable)
- Parsing metadata (page count, warnings, errors)

**Process:**
1. Validate PDF file exists and is readable
2. Attempt parsing with primary engine (PyMuPDF)
3. If fails, retry with fallback engine (pdfplumber)
4. Extract text with page numbers
5. Detect and extract code blocks
6. Extract document structure (headings, sections)
7. Extract diagrams and tables
8. Save ParsedDocument to JSON file
9. Return file path and metadata

**Skills Used:**
- PDFProcessingSkill (primary)
- CodeAnalysisSkill
- DiagramExtractionSkill
- TableParsingSkill
- FileOperationsSkill
- CachingSkill

**Error Handling:**
- If both parsers fail: Return minimal ParsedDocument with error flag
- If code detection fails: Log warning, continue with text-only
- If structure detection fails: Treat as flat document

---

#### Agent 3: EvaluatorAgent
**Responsibility:** Evaluate submission against ONE specific criterion

**Inputs:**
- ParsedDocument object
- Criterion definition (name, weight, rubric)
- Criticism multiplier
- Evaluation prompt template

**Outputs:**
- CriterionEvaluation object
- Raw LLM response (for debugging)
- Evaluation metadata (tokens used, time taken)

**Process:**
1. Load criterion-specific prompt template
2. Extract relevant sections from ParsedDocument
3. Construct evaluation prompt with context
4. Call Claude API via LLMEvaluationSkill
5. Parse structured JSON response
6. Validate response against schema
7. Apply criticism multiplier adjustments
8. Return CriterionEvaluation object

**Skills Used:**
- LLMEvaluationSkill (primary)
- FileOperationsSkill
- DataValidationSkill
- CostCalculationSkill

**Design Pattern:**
This agent is **stateless and reusable**. The OrchestratorAgent spawns multiple instances:
- EvaluatorAgent(criterion="prd_quality")
- EvaluatorAgent(criterion="code_structure")
- EvaluatorAgent(criterion="unit_tests")
- etc.

**Configuration:**
Each instance receives:
- Criterion-specific weight
- Custom prompt template
- Rubric guidelines
- Keywords for section extraction

---

#### Agent 4: ScoringAgent
**Responsibility:** Calculate final grades from criterion evaluations

**Inputs:**
- List of CriterionEvaluation objects
- Criticism multiplier
- Scoring configuration (weights, severity factors)

**Outputs:**
- Final numerical score (0-100)
- Category breakdown (scores per category)
- Weighted contribution analysis
- Score comparison to self-grade

**Process:**
1. Validate all evaluations are present
2. Group evaluations by category
3. Apply severity factors (critical, important, minor)
4. Apply criticism multiplier to deductions
5. Calculate weighted average
6. Generate category breakdown
7. Compare to self-assessed grade
8. Return GradingResult object

**Skills Used:**
- DataValidationSkill
- FileOperationsSkill

**Algorithm:**
```python
for eval in evaluations:
    severity_factor = get_severity_factor(eval.severity)
    adjusted_score = eval.score * severity_factor
    
    if criticism_multiplier > 1.0 and eval.score < 100:
        penalty = (100 - eval.score) * (criticism_multiplier - 1.0) * 0.2
        adjusted_score -= penalty
    
    weighted_sum += adjusted_score * eval.weight

final_score = weighted_sum / total_weight
```

---

#### Agent 5: ReporterAgent
**Responsibility:** Generate comprehensive grading reports

**Inputs:**
- GradingResult object
- Report template selection (markdown, pdf, json)
- Output directory

**Outputs:**
- Generated report file(s)
- Report metadata (file paths, sizes, generation time)

**Process:**
1. Load appropriate template (Jinja2)
2. Prepare template context from GradingResult
3. Render Markdown report
4. If PDF requested: Convert Markdown to PDF
5. If JSON requested: Export structured data
6. If CSV requested: Generate summary row
7. Save all files to output directory
8. Return file paths

**Skills Used:**
- ReportingSkill (primary)
- FileOperationsSkill

**Report Sections:**
1. Executive Summary
2. Score Breakdown (table)
3. Detailed Evaluation (per criterion)
4. Comparison to Self-Assessment
5. Recommendations for Improvement
6. Appendix (evidence, citations)

---

#### Agent 6: ValidationAgent
**Responsibility:** Validate all inputs and outputs

**Inputs:**
- Data to validate (any type)
- Schema/rules to validate against

**Outputs:**
- Validation result (pass/fail)
- List of validation errors
- Sanitized data (if applicable)

**Process:**
1. Check data type matches expected
2. Validate against Pydantic schema
3. Check business rules (e.g., self-grade 0-100)
4. Sanitize inputs (e.g., remove null bytes from PDFs)
5. Return validation report

**Skills Used:**
- DataValidationSkill (primary)

**Validation Types:**
- **Input Validation**: PDF exists, self-grade in range, config valid
- **Intermediate Validation**: ParsedDocument complete, evaluations valid
- **Output Validation**: Report files generated, scores in range

---

#### Agent 7: CostTrackerAgent
**Responsibility:** Monitor API usage and costs

**Inputs:**
- API call metadata (tokens, model, timestamp)

**Outputs:**
- Cost report (total spent, per-criterion breakdown)
- Budget warnings/alerts
- Usage statistics

**Process:**
1. Receive API call metadata from LLMEvaluationSkill
2. Calculate cost based on model pricing
3. Aggregate costs by criterion, by submission
4. Check against budget limits
5. Generate cost report
6. Emit warnings if approaching budget

**Skills Used:**
- CostCalculationSkill (primary)
- FileOperationsSkill

**Metrics Tracked:**
- Total tokens (input + output)
- Total cost (USD)
- Cost per criterion
- Cost per submission
- Average cost across batch
- Budget remaining

---

### 3.4 Agent Communication Protocol

**FR-3.1:** Agents SHALL communicate using structured JSON files:

```
workspace/
├── inputs/
│   ├── submission.pdf
│   └── grading_request.json
├── intermediate/
│   ├── parsed_document.json
│   ├── evaluations/
│   │   ├── prd_quality.json
│   │   ├── code_structure.json
│   │   └── unit_tests.json
│   └── scoring_result.json
└── outputs/
    ├── grading_report.md
    ├── grading_report.pdf
    └── grading_result.json
```

**FR-3.2:** Agent invocation SHALL use standard Python async/await:

```python
# Orchestrator spawns agents
parser_result = await parser_agent.execute(pdf_path)
evaluations = await asyncio.gather(*[
    evaluator_agent.execute(parser_result, criterion)
    for criterion in criteria
])
scoring_result = await scoring_agent.execute(evaluations)
report_paths = await reporter_agent.execute(scoring_result)
```

**FR-3.3:** Error propagation SHALL be handled via exceptions:
- Agents raise `AgentExecutionError` on failure
- OrchestratorAgent catches and logs errors
- Failed evaluations are replaced with error placeholders
- System attempts to complete grading with partial results

---

### 3.5 Orchestration Workflow

**Complete Grading Workflow:**

```
1. OrchestratorAgent receives (pdf, self_grade)
2. OrchestratorAgent → ValidationAgent: validate inputs
3. OrchestratorAgent → ParserAgent: parse PDF
4. ParserAgent → returns ParsedDocument
5. OrchestratorAgent calculates criticism_multiplier
6. OrchestratorAgent spawns 7x EvaluatorAgents in parallel:
   - EvaluatorAgent(criterion="prd_quality")
   - EvaluatorAgent(criterion="architecture_doc")
   - EvaluatorAgent(criterion="readme")
   - EvaluatorAgent(criterion="project_structure")
   - EvaluatorAgent(criterion="code_documentation")
   - EvaluatorAgent(criterion="unit_tests")
   - EvaluatorAgent(criterion="error_handling")
   [... continues for all criteria ...]
7. Each EvaluatorAgent:
   - Extracts relevant content
   - Calls Claude API
   - Returns CriterionEvaluation
8. OrchestratorAgent collects all evaluations
9. OrchestratorAgent → ScoringAgent: calculate final score
10. ScoringAgent → returns GradingResult
11. OrchestratorAgent → ReporterAgent: generate reports
12. ReporterAgent → returns report file paths
13. OrchestratorAgent → CostTrackerAgent: log costs
14. OrchestratorAgent returns complete result
```

**Parallel Execution:**
Steps 6-7 execute in parallel using `asyncio.gather()`, reducing total time from ~10 minutes to ~3 minutes.

---

## 4. Non-Functional Requirements

### 4.1 Performance
**NFR-1.1:** Agent spawning SHALL complete in <100ms per agent

**NFR-1.2:** Inter-agent communication SHALL have <50ms overhead

**NFR-1.3:** Parallel evaluation SHALL reduce total time by 60%+

**NFR-1.4:** Memory usage SHALL remain <2GB even with 10 parallel evaluations

### 4.2 Reliability
**NFR-2.1:** Individual agent failures SHALL NOT crash entire system

**NFR-2.2:** System SHALL complete grading with ≥80% criteria evaluated

**NFR-2.3:** Agents SHALL be restartable (no persistent state corruption)

**NFR-2.4:** All agent executions SHALL be logged for debugging

### 4.3 Maintainability
**NFR-3.1:** New criterion evaluators SHALL require <2 hours to add

**NFR-3.2:** Agent code SHALL be <300 lines per agent

**NFR-3.3:** Skills SHALL be <200 lines per skill

**NFR-3.4:** Code duplication SHALL be <10% across agents

### 4.4 Testability
**NFR-4.1:** Each agent SHALL have ≥90% test coverage

**NFR-4.2:** Skills SHALL be testable without Claude API calls (mocking)

**NFR-4.3:** Integration tests SHALL cover all agent-to-agent interactions

**NFR-4.4:** Test execution SHALL complete in <2 minutes

### 4.5 Observability
**NFR-5.1:** All agent executions SHALL emit structured logs

**NFR-5.2:** Agent execution times SHALL be tracked and reportable

**NFR-5.3:** System SHALL generate execution trace for debugging

**NFR-5.4:** Cost tracking SHALL be accurate within $0.01

---

## 5. Skills Specifications

### 5.1 PDFProcessingSkill

**Functions:**
```python
def parse_pdf(pdf_path: Path, engine: str = "pymupdf") -> ParsedDocument:
    """Parse PDF and extract structured content."""
    
def extract_text_by_page(pdf_path: Path) -> Dict[int, str]:
    """Extract text content organized by page number."""
    
def detect_code_blocks(text: str) -> List[CodeBlock]:
    """Identify and extract code blocks from text."""
    
def extract_document_structure(pdf_path: Path) -> DocumentStructure:
    """Extract headings, sections, and table of contents."""
```

**Dependencies:**
- PyMuPDF (fitz)
- pdfplumber (fallback)

**Configuration:**
```yaml
pdf_processing:
  primary_engine: "pymupdf"
  fallback_engine: "pdfplumber"
  extract_images: true
  extract_tables: true
  code_detection_threshold: 0.8
```

---

### 5.2 LLMEvaluationSkill

**Functions:**
```python
def evaluate_with_claude(
    prompt: str,
    context: str,
    model: str = "claude-sonnet-4-20250514"
) -> Dict[str, Any]:
    """Call Claude API and return structured response."""
    
def construct_evaluation_prompt(
    criterion_name: str,
    context: str,
    criticism_multiplier: float,
    template: str
) -> str:
    """Build evaluation prompt from template."""
    
def parse_structured_response(response: str) -> Dict[str, Any]:
    """Parse JSON from Claude response, handling errors."""
```

**Dependencies:**
- anthropic library
- Environment variable: CLAUDE_API_KEY

**Retry Logic:**
```python
@retry(max_attempts=3, backoff=exponential, exceptions=[APIError])
def evaluate_with_claude(...):
    # Implementation
```

---

### 5.3 DataValidationSkill

**Functions:**
```python
def validate_pdf_input(pdf_path: Path) -> ValidationResult:
    """Validate PDF file exists, is readable, and not corrupted."""
    
def validate_self_grade(grade: int) -> ValidationResult:
    """Validate self-grade is 0-100."""
    
def validate_evaluation(eval: CriterionEvaluation) -> ValidationResult:
    """Validate evaluation has all required fields."""
    
def sanitize_text(text: str) -> str:
    """Remove dangerous characters from extracted text."""
```

**Validation Rules:**
- PDF max size: 50MB
- PDF must start with `%PDF`
- Self-grade must be integer 0-100
- Evaluation score must be float 0-100
- Evidence list must not be empty

---

### 5.4 ReportingSkill

**Functions:**
```python
def render_markdown_report(
    result: GradingResult,
    template_path: Path
) -> str:
    """Render Markdown report from Jinja2 template."""
    
def convert_markdown_to_pdf(markdown: str) -> bytes:
    """Convert Markdown to PDF."""
    
def export_to_json(result: GradingResult) -> str:
    """Export GradingResult to JSON."""
    
def export_to_csv_row(result: GradingResult) -> str:
    """Export summary as CSV row for batch processing."""
```

**Templates:**
Located in `templates/`:
- `grading_report.md.jinja`
- `executive_summary.md.jinja`
- `detailed_evaluation.md.jinja`

---

### 5.5 CostCalculationSkill

**Functions:**
```python
def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str
) -> float:
    """Calculate cost in USD for API call."""
    
def track_api_call(
    criterion: str,
    tokens_used: int,
    cost: float
) -> None:
    """Log API call for cost tracking."""
    
def generate_cost_report() -> CostReport:
    """Generate aggregated cost report."""
    
def check_budget(current_cost: float, budget: float) -> bool:
    """Check if within budget."""
```

**Pricing (Claude Sonnet 4.5):**
- Input: $3.00 per 1M tokens
- Output: $15.00 per 1M tokens

---

## 6. Implementation Priorities

### Phase 1: Core Infrastructure (Week 1)
1. Set up agent framework and base classes
2. Implement PDFProcessingSkill
3. Implement FileOperationsSkill
4. Implement DataValidationSkill
5. Create ParserAgent
6. Create ValidationAgent

### Phase 2: Evaluation Pipeline (Week 2)
1. Implement LLMEvaluationSkill
2. Create EvaluatorAgent base
3. Implement first 3 criterion evaluators (PRD, README, Code Structure)
4. Create ScoringAgent
5. Implement CostCalculationSkill
6. Create CostTrackerAgent

### Phase 3: Orchestration & Reporting (Week 3)
1. Create OrchestratorAgent
2. Implement parallel evaluation logic
3. Implement ReportingSkill
4. Create ReporterAgent
5. Implement remaining criterion evaluators

### Phase 4: Testing & Refinement (Week 4)
1. Write unit tests for all skills
2. Write integration tests for agent workflows
3. Performance testing and optimization
4. Documentation and examples

---

## 7. Success Criteria

### MVP Acceptance Criteria
- ✓ All 7 core agents implemented and tested
- ✓ All 5 core skills implemented and tested
- ✓ OrchestratorAgent successfully coordinates full workflow
- ✓ Parallel evaluation reduces time by 50%+
- ✓ System handles PDF parsing failures gracefully
- ✓ Complete grading report generated
- ✓ Cost tracking accurate to $0.01

### Quality Gates
- ✓ 90%+ test coverage per agent
- ✓ All agents pass integration tests
- ✓ Zero code duplication in core logic
- ✓ All skills documented with examples
- ✓ Performance benchmarks met

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Agent coordination complexity | High | Use proven patterns (async/await), extensive testing |
| Parallel execution race conditions | Medium | Use thread-safe skills, proper locking |
| Claude API rate limits | Medium | Implement exponential backoff, respect rate limits |
| Memory usage with 10 parallel evaluators | Medium | Stream large data, clean up after each evaluation |
| Agent failure cascades | High | Implement error boundaries, graceful degradation |

---

## 9. Appendix

### Agent Naming Convention
- All agents end with "Agent" (e.g., ParserAgent)
- Agent files: `src/agents/parser_agent.py`
- Agent tests: `tests/agents/test_parser_agent.py`

### Skill Naming Convention
- All skills end with "Skill" (e.g., PDFProcessingSkill)
- Skill files: `src/skills/pdf_processing_skill.py`
- Skill tests: `tests/skills/test_pdf_processing_skill.py`

### Data Models Location
- All Pydantic models in `src/models/`
- Shared between agents and skills

---

**Document Status:** Draft for Review  
**Next Steps:** Review and approve, then proceed to implementation  
**Approval Required From:** Technical Lead, Product Owner
