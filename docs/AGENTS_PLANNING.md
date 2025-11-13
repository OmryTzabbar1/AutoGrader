# PLANNING.MD - Agent Architecture & Implementation
# Auto-Grading System with Claude Code Agents

**Version:** 1.0  
**Last Updated:** November 2025

---

## Table of Contents
1. [Agent System Architecture](#agent-system-architecture)
2. [Agent Specifications](#agent-specifications)
3. [Skill Specifications](#skill-specifications)
4. [Communication Protocols](#communication-protocols)
5. [Data Flow Diagrams](#data-flow-diagrams)
6. [File Structure](#file-structure)
7. [Configuration Management](#configuration-management)
8. [Testing Strategy](#testing-strategy)

---

## 1. Agent System Architecture

### High-Level Agent Topology

```
                    ┌────────────────────┐
                    │  Orchestrator      │
                    │     Agent          │
                    └──────────┬─────────┘
                               │
                ┌──────────────┼──────────────┐
                ↓              ↓              ↓
        ┌──────────────┐ ┌──────────┐ ┌──────────────┐
        │  Validation  │ │  Parser  │ │ Cost Tracker │
        │    Agent     │ │  Agent   │ │    Agent     │
        └──────────────┘ └─────┬────┘ └──────────────┘
                               │
                               ↓
                    ┌──────────────────────┐
                    │  Parsed Document     │
                    │  (JSON File)         │
                    └──────────┬───────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ↓                      ↓                      ↓
┌───────────────┐      ┌───────────────┐     ┌───────────────┐
│  Evaluator    │      │  Evaluator    │ ... │  Evaluator    │
│  Agent        │      │  Agent        │     │  Agent        │
│ (PRD Quality) │      │(Code Structure│     │ (Unit Tests)  │
└───────┬───────┘      └───────┬───────┘     └───────┬───────┘
        │                      │                     │
        └──────────────────────┼─────────────────────┘
                               ↓
                    ┌──────────────────────┐
                    │  Evaluation Results  │
                    │  (JSON Files)        │
                    └──────────┬───────────┘
                               │
                               ↓
                        ┌─────────────┐
                        │   Scoring   │
                        │    Agent    │
                        └──────┬──────┘
                               │
                               ↓
                        ┌─────────────┐
                        │  Reporter   │
                        │    Agent    │
                        └──────┬──────┘
                               │
                               ↓
                        ┌─────────────┐
                        │   Reports   │
                        │   (MD, PDF) │
                        └─────────────┘
```

### Agent Classification

**Type 1: Coordinator Agents**
- OrchestratorAgent
- *Role:* Manages workflow, spawns other agents, aggregates results

**Type 2: Processing Agents**
- ParserAgent
- ValidationAgent
- *Role:* Transform data (input → output)

**Type 3: Worker Agents**
- EvaluatorAgent (multiple instances)
- *Role:* Execute specific tasks independently

**Type 4: Support Agents**
- CostTrackerAgent
- *Role:* Monitoring, observability, auxiliary functions

**Type 5: Output Agents**
- ScoringAgent
- ReporterAgent
- *Role:* Produce final deliverables

---

## 2. Agent Specifications

### 2.1 OrchestratorAgent

**File:** `src/agents/orchestrator_agent.py`

**Class Definition:**
```python
from typing import List
from models import GradingRequest, GradingResult, AgentResult
from agents.base_agent import BaseAgent

class OrchestratorAgent(BaseAgent[GradingRequest, GradingResult]):
    """
    Coordinates the complete grading workflow.
    
    Responsibilities:
    - Validate grading request
    - Delegate PDF parsing
    - Spawn evaluator agents in parallel
    - Aggregate evaluation results
    - Delegate scoring and reporting
    - Track costs and performance
    
    Configuration:
    - max_parallel_evaluations: int (default: 10)
    - timeout_seconds: int (default: 300)
    - retry_failed_evaluations: bool (default: False)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.validation_agent = ValidationAgent(config.get("validation", {}))
        self.parser_agent = ParserAgent(config.get("parser", {}))
        self.scoring_agent = ScoringAgent(config.get("scoring", {}))
        self.reporter_agent = ReporterAgent(config.get("reporter", {}))
        self.cost_tracker = CostTrackerAgent(config.get("cost_tracker", {}))
    
    async def execute(self, request: GradingRequest) -> AgentResult[GradingResult]:
        """Execute complete grading workflow."""
        
        # Step 1: Validate request
        validation = await self.validation_agent.execute(request)
        if not validation.success:
            return AgentResult(success=False, error=validation.error)
        
        # Step 2: Parse PDF
        parse_result = await self.parser_agent.execute(request.pdf_path)
        if not parse_result.success:
            return AgentResult(success=False, error=parse_result.error)
        
        parsed_doc = parse_result.output
        
        # Step 3: Calculate criticism multiplier
        criticism_multiplier = self._calculate_criticism_multiplier(
            request.self_grade
        )
        
        # Step 4: Spawn evaluator agents (parallel)
        evaluations = await self._run_parallel_evaluations(
            parsed_doc,
            criticism_multiplier
        )
        
        # Step 5: Calculate final score
        score_result = await self.scoring_agent.execute(ScoringInput(
            evaluations=evaluations,
            criticism_multiplier=criticism_multiplier
        ))
        
        # Step 6: Generate reports
        report_result = await self.reporter_agent.execute(
            score_result.output
        )
        
        # Step 7: Track costs
        await self.cost_tracker.finalize(request.pdf_path.stem)
        
        return AgentResult(
            success=True,
            output=score_result.output,
            metadata={
                "report_paths": report_result.output.paths,
                "total_cost": self.cost_tracker.get_total_cost()
            }
        )
    
    async def _run_parallel_evaluations(
        self,
        document: ParsedDocument,
        criticism_multiplier: float
    ) -> List[CriterionEvaluation]:
        """Spawn multiple EvaluatorAgents in parallel."""
        
        criteria_configs = self.config["evaluators"]
        
        async def evaluate_one(criterion_config):
            agent = EvaluatorAgent(criterion_config)
            return await agent.execute(EvaluatorInput(
                document=document,
                criticism_multiplier=criticism_multiplier
            ))
        
        # Run in parallel with timeout
        results = await asyncio.wait_for(
            asyncio.gather(
                *[evaluate_one(cfg) for cfg in criteria_configs],
                return_exceptions=True
            ),
            timeout=self.config.get("timeout_seconds", 300)
        )
        
        # Extract successful evaluations
        evaluations = []
        for result in results:
            if isinstance(result, Exception):
                self.logger.error(f"Evaluation failed: {result}")
                evaluations.append(self._create_error_placeholder(result))
            elif result.success:
                evaluations.append(result.output)
        
        return evaluations
    
    def _calculate_criticism_multiplier(self, self_grade: int) -> float:
        """Calculate adaptive criticism multiplier."""
        if 90 <= self_grade <= 100:
            return 1.5
        elif 80 <= self_grade < 90:
            return 1.2
        elif 70 <= self_grade < 80:
            return 1.0
        elif 60 <= self_grade < 70:
            return 0.8
        else:
            return 0.6
```

**Configuration File:** `config/orchestrator.yaml`
```yaml
orchestrator:
  max_parallel_evaluations: 10
  timeout_seconds: 300
  retry_failed_evaluations: false

evaluators:
  - criterion: "prd_quality"
    weight: 0.08
    prompt_template: "prompts/prd_evaluation.txt"
  - criterion: "architecture_doc"
    weight: 0.07
    prompt_template: "prompts/architecture_evaluation.txt"
  # ... all criteria
```

---

### 2.2 ParserAgent

**File:** `src/agents/parser_agent.py`

**Class Definition:**
```python
from pathlib import Path
from models import ParsedDocument, AgentResult
from agents.base_agent import BaseAgent
from skills.pdf_processing_skill import PDFProcessingSkill
from skills.code_analysis_skill import CodeAnalysisSkill
from skills.caching_skill import CachingSkill

class ParserAgent(BaseAgent[Path, ParsedDocument]):
    """
    Parse PDF submissions and extract structured content.
    
    Responsibilities:
    - Validate PDF file
    - Extract text with page numbers
    - Detect code blocks and programming languages
    - Extract document structure (sections, headings)
    - Cache results for performance
    
    Configuration:
    - engine: str (primary parser: 'pymupdf' or 'pdfplumber')
    - fallback_engine: str (backup parser)
    - cache_enabled: bool (default: True)
    - extract_images: bool (default: False)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.pdf_skill = PDFProcessingSkill(config)
        self.code_skill = CodeAnalysisSkill()
        self.cache = CachingSkill(cache_dir=".cache/parsed_docs")
    
    async def execute(self, pdf_path: Path) -> AgentResult[ParsedDocument]:
        """Parse PDF and return structured document."""
        
        start_time = time.time()
        
        # Check cache
        if self.config.get("cache_enabled", True):
            cached = self.cache.get(pdf_path)
            if cached:
                self.logger.info(f"Using cached parsing for {pdf_path.name}")
                return AgentResult(
                    success=True,
                    output=cached,
                    metadata={"from_cache": True},
                    execution_time=time.time() - start_time
                )
        
        # Parse PDF
        try:
            parsed = self.pdf_skill.parse_pdf(
                pdf_path,
                engine=self.config.get("engine", "pymupdf")
            )
        except PDFParsingError as e:
            # Try fallback
            self.logger.warning(f"Primary parser failed: {e}, trying fallback")
            try:
                parsed = self.pdf_skill.parse_pdf(
                    pdf_path,
                    engine=self.config.get("fallback_engine", "pdfplumber")
                )
            except Exception as fallback_error:
                return AgentResult(
                    success=False,
                    error=f"All parsers failed: {fallback_error}"
                )
        
        # Enhance with code analysis
        for code_block in parsed.code_blocks:
            code_block.language = self.code_skill.detect_language(
                code_block.content
            )
        
        # Cache result
        if self.config.get("cache_enabled", True):
            self.cache.set(pdf_path, parsed)
        
        # Save to JSON for other agents
        output_path = Path("workspace/intermediate/parsed_document.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(parsed.model_dump_json(indent=2))
        
        return AgentResult(
            success=True,
            output=parsed,
            metadata={
                "output_path": str(output_path),
                "pages": parsed.total_pages,
                "code_blocks": len(parsed.code_blocks),
                "sections": len(parsed.structure.sections)
            },
            execution_time=time.time() - start_time
        )
```

---

### 2.3 EvaluatorAgent

**File:** `src/agents/evaluator_agent.py`

**Class Definition:**
```python
from models import EvaluatorInput, CriterionEvaluation, AgentResult
from agents.base_agent import BaseAgent
from skills.llm_evaluation_skill import LLMEvaluationSkill
from skills.file_operations_skill import FileOperationsSkill

class EvaluatorAgent(BaseAgent[EvaluatorInput, CriterionEvaluation]):
    """
    Evaluate submission against ONE specific criterion.
    
    This agent is stateless and reusable. The orchestrator spawns
    multiple instances with different configurations.
    
    Responsibilities:
    - Extract relevant sections from document
    - Construct criterion-specific evaluation prompt
    - Call Claude API for evaluation
    - Parse and validate response
    - Apply criticism multiplier adjustments
    
    Configuration:
    - criterion: str (e.g., "prd_quality")
    - weight: float (e.g., 0.08)
    - prompt_template: str (path to template file)
    - keywords: List[str] (for section extraction)
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.criterion = config["criterion"]
        self.weight = config["weight"]
        self.llm_skill = LLMEvaluationSkill()
        self.file_ops = FileOperationsSkill()
    
    async def execute(
        self,
        input_data: EvaluatorInput
    ) -> AgentResult[CriterionEvaluation]:
        """Evaluate document against criterion."""
        
        start_time = time.time()
        
        # Load prompt template
        template = self.file_ops.read_text(
            Path(self.config["prompt_template"])
        )
        
        # Extract relevant sections
        keywords = self.config.get("keywords", [self.criterion])
        relevant_content = self._extract_relevant_sections(
            input_data.document,
            keywords
        )
        
        # Construct prompt
        prompt = template.format(
            criterion_name=self.criterion,
            context=relevant_content,
            criticism_multiplier=input_data.criticism_multiplier,
            weight=self.weight
        )
        
        # Call Claude API
        try:
            response = await self.llm_skill.evaluate_with_claude(
                prompt=prompt,
                context=relevant_content,
                criticism_multiplier=input_data.criticism_multiplier
            )
        except APIError as e:
            return AgentResult(
                success=False,
                error=f"Claude API failed: {e}"
            )
        
        # Parse response into structured evaluation
        evaluation = CriterionEvaluation(
            criterion_id=self.criterion,
            criterion_name=self.criterion.replace("_", " ").title(),
            weight=self.weight,
            score=response["score"],
            evidence=response["evidence"],
            strengths=response["strengths"],
            weaknesses=response["weaknesses"],
            suggestions=response["suggestions"],
            severity=response["severity"]
        )
        
        # Save to JSON
        output_path = Path(f"workspace/intermediate/evaluations/{self.criterion}.json")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(evaluation.model_dump_json(indent=2))
        
        return AgentResult(
            success=True,
            output=evaluation,
            metadata={
                "output_path": str(output_path),
                "tokens_used": response.get("tokens_used"),
                "cost": response.get("cost")
            },
            execution_time=time.time() - start_time
        )
    
    def _extract_relevant_sections(
        self,
        document: ParsedDocument,
        keywords: List[str]
    ) -> str:
        """Extract sections relevant to this criterion."""
        relevant = []
        
        for page_num, text in document.text_content.items():
            if any(kw.lower() in text.lower() for kw in keywords):
                relevant.append(f"=== Page {page_num} ===\n{text}")
        
        return "\n\n".join(relevant) if relevant else "No relevant content found."
```

---

### 2.4 ScoringAgent

**File:** `src/agents/scoring_agent.py`

**Class Definition:**
```python
from typing import List
from models import ScoringInput, GradingResult, AgentResult
from agents.base_agent import BaseAgent

class ScoringAgent(BaseAgent[ScoringInput, GradingResult]):
    """
    Calculate final grade from criterion evaluations.
    
    Responsibilities:
    - Apply weighted averaging
    - Apply severity factors
    - Apply criticism multiplier to deductions
    - Generate category breakdowns
    - Compare to self-assessed grade
    
    Configuration:
    - severity_factors: Dict[str, float]
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.severity_factors = config.get("severity_factors", {
            "critical": 0.5,
            "important": 0.8,
            "minor": 0.95,
            "strength": 1.0
        })
    
    async def execute(
        self,
        input_data: ScoringInput
    ) -> AgentResult[GradingResult]:
        """Calculate final score from evaluations."""
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for evaluation in input_data.evaluations:
            # Apply severity factor
            severity_factor = self.severity_factors[evaluation.severity]
            adjusted_score = evaluation.score * severity_factor
            
            # Apply criticism multiplier
            if input_data.criticism_multiplier > 1.0 and evaluation.score < 100:
                penalty = (100 - evaluation.score) * \
                         (input_data.criticism_multiplier - 1.0) * 0.2
                adjusted_score -= penalty
            elif input_data.criticism_multiplier < 1.0 and evaluation.score < 100:
                bonus = (100 - evaluation.score) * \
                       (1.0 - input_data.criticism_multiplier) * 0.3
                adjusted_score += bonus
            
            weighted_sum += adjusted_score * evaluation.weight
            total_weight += evaluation.weight
        
        final_score = weighted_sum / total_weight if total_weight > 0 else 0
        
        # Generate category breakdown
        breakdown = self._create_breakdown(input_data.evaluations)
        
        # Compare to self-grade
        comparison = self._generate_comparison_message(
            final_score,
            input_data.self_grade
        )
        
        result = GradingResult(
            submission_id="",  # Set by orchestrator
            self_grade=input_data.self_grade,
            final_score=round(final_score, 2),
            criticism_multiplier=input_data.criticism_multiplier,
            evaluations=input_data.evaluations,
            breakdown=breakdown,
            comparison_message=comparison
        )
        
        return AgentResult(success=True, output=result)
```

---

### 2.5 ReporterAgent

**File:** `src/agents/reporter_agent.py`

**Class Definition:**
```python
from pathlib import Path
from models import GradingResult, ReportOutput, AgentResult
from agents.base_agent import BaseAgent
from skills.reporting_skill import ReportingSkill
from skills.file_operations_skill import FileOperationsSkill

class ReporterAgent(BaseAgent[GradingResult, ReportOutput]):
    """
    Generate comprehensive grading reports.
    
    Responsibilities:
    - Render Markdown reports from templates
    - Convert to PDF if requested
    - Export JSON and CSV formats
    - Save all outputs to designated directory
    
    Configuration:
    - output_dir: str (default: "workspace/outputs")
    - formats: List[str] (e.g., ["markdown", "pdf", "json"])
    - template_dir: str (default: "templates")
    """
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.reporting_skill = ReportingSkill(config.get("template_dir"))
        self.file_ops = FileOperationsSkill()
        self.output_dir = Path(config.get("output_dir", "workspace/outputs"))
    
    async def execute(
        self,
        grading_result: GradingResult
    ) -> AgentResult[ReportOutput]:
        """Generate reports in requested formats."""
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        report_paths = {}
        
        # Generate Markdown report
        if "markdown" in self.config.get("formats", ["markdown"]):
            md_content = self.reporting_skill.render_markdown_report(
                grading_result
            )
            md_path = self.output_dir / f"{grading_result.submission_id}_report.md"
            self.file_ops.write_text(md_path, md_content)
            report_paths["markdown"] = str(md_path)
        
        # Convert to PDF if requested
        if "pdf" in self.config.get("formats", []):
            pdf_bytes = self.reporting_skill.convert_markdown_to_pdf(md_content)
            pdf_path = self.output_dir / f"{grading_result.submission_id}_report.pdf"
            self.file_ops.write_bytes(pdf_path, pdf_bytes)
            report_paths["pdf"] = str(pdf_path)
        
        # Export JSON
        if "json" in self.config.get("formats", []):
            json_content = grading_result.model_dump_json(indent=2)
            json_path = self.output_dir / f"{grading_result.submission_id}_result.json"
            self.file_ops.write_text(json_path, json_content)
            report_paths["json"] = str(json_path)
        
        output = ReportOutput(paths=report_paths)
        
        return AgentResult(
            success=True,
            output=output,
            metadata={"formats_generated": list(report_paths.keys())}
        )
```

---

## 3. Skill Specifications

### 3.1 PDFProcessingSkill

**File:** `src/skills/pdf_processing_skill.py`

```python
import fitz  # PyMuPDF
import pdfplumber
from pathlib import Path
from typing import Dict, List
from models import ParsedDocument, CodeBlock, DocumentStructure

class PDFProcessingSkill:
    """Skill for parsing and extracting content from PDFs."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    def parse_pdf(
        self,
        pdf_path: Path,
        engine: str = "pymupdf"
    ) -> ParsedDocument:
        """
        Parse PDF and extract structured content.
        
        Args:
            pdf_path: Path to PDF file
            engine: Parser engine ('pymupdf' or 'pdfplumber')
        
        Returns:
            ParsedDocument with extracted content
        
        Raises:
            PDFParsingError: If parsing fails
        """
        if engine == "pymupdf":
            return self._parse_with_pymupdf(pdf_path)
        elif engine == "pdfplumber":
            return self._parse_with_pdfplumber(pdf_path)
        else:
            raise ValueError(f"Unknown engine: {engine}")
    
    def _parse_with_pymupdf(self, pdf_path: Path) -> ParsedDocument:
        """Parse using PyMuPDF (fast, accurate)."""
        doc = fitz.open(pdf_path)
        
        text_content = {}
        for page_num, page in enumerate(doc, start=1):
            text_content[page_num] = page.get_text()
        
        code_blocks = self._detect_code_blocks(text_content)
        structure = self._extract_structure(doc)
        
        doc.close()
        
        return ParsedDocument(
            file_path=pdf_path,
            total_pages=len(text_content),
            text_content=text_content,
            code_blocks=code_blocks,
            structure=structure
        )
    
    def _detect_code_blocks(
        self,
        text_content: Dict[int, str]
    ) -> List[CodeBlock]:
        """Detect code blocks using heuristics."""
        code_blocks = []
        
        for page_num, text in text_content.items():
            lines = text.split('\n')
            in_code_block = False
            current_block = []
            
            for line in lines:
                # Simple heuristic: indented lines with special chars
                if self._looks_like_code(line):
                    in_code_block = True
                    current_block.append(line)
                elif in_code_block and line.strip():
                    current_block.append(line)
                elif in_code_block and not line.strip():
                    # End of code block
                    if len(current_block) >= 3:  # Min 3 lines
                        code_blocks.append(CodeBlock(
                            content='\n'.join(current_block),
                            page_number=page_num,
                            line_count=len(current_block)
                        ))
                    current_block = []
                    in_code_block = False
        
        return code_blocks
    
    def _looks_like_code(self, line: str) -> bool:
        """Heuristic to detect if line is code."""
        code_indicators = ['def ', 'class ', 'import ', '    ', '\t', '{', '}', '(', ')', ';']
        return any(indicator in line for indicator in code_indicators)
```

---

### 3.2 LLMEvaluationSkill

**File:** `src/skills/llm_evaluation_skill.py`

```python
import anthropic
import json
from typing import Dict, Any

class LLMEvaluationSkill:
    """Skill for Claude API interaction and evaluation."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.client = anthropic.Anthropic(
            api_key=os.getenv("CLAUDE_API_KEY")
        )
    
    async def evaluate_with_claude(
        self,
        prompt: str,
        context: str,
        *,
        criticism_multiplier: float = 1.0,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
        temperature: float = 0.0
    ) -> Dict[str, Any]:
        """
        Call Claude API for evaluation.
        
        Returns structured JSON with:
        - score: float (0-100)
        - evidence: List[str]
        - strengths: List[str]
        - weaknesses: List[str]
        - suggestions: List[str]
        - severity: str
        """
        
        full_prompt = self._construct_full_prompt(
            prompt,
            context,
            criticism_multiplier
        )
        
        response = await self._call_api_with_retry(
            prompt=full_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        # Parse structured response
        return self._parse_response(response)
    
    def _construct_full_prompt(
        self,
        template: str,
        context: str,
        criticism_multiplier: float
    ) -> str:
        """Build complete evaluation prompt."""
        return f"""
{template}

CRITICISM MULTIPLIER: {criticism_multiplier}x

CONTENT TO EVALUATE:
{context}

Respond ONLY with valid JSON in this exact format:
{{
  "score": <0-100>,
  "evidence": ["Page X: ...", "Page Y: ..."],
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "suggestions": ["...", "..."],
  "severity": "critical|important|minor|strength"
}}
"""
    
    async def _call_api_with_retry(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        max_retries: int = 3
    ) -> anthropic.Message:
        """Call API with exponential backoff retry."""
        for attempt in range(max_retries):
            try:
                response = self.client.messages.create(
                    model=model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=[{"role": "user", "content": prompt}]
                )
                return response
            except anthropic.APIError as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
    
    def _parse_response(self, response: anthropic.Message) -> Dict[str, Any]:
        """Parse JSON from Claude response."""
        text = response.content[0].text
        
        # Strip markdown code blocks if present
        text = text.replace("```json", "").replace("```", "").strip()
        
        try:
            parsed = json.loads(text)
            # Add metadata
            parsed["tokens_used"] = response.usage.input_tokens + response.usage.output_tokens
            parsed["cost"] = self._calculate_cost(response.usage)
            return parsed
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response from Claude: {e}")
    
    def _calculate_cost(self, usage: anthropic.Usage) -> float:
        """Calculate cost based on token usage."""
        input_cost = (usage.input_tokens / 1_000_000) * 3.00
        output_cost = (usage.output_tokens / 1_000_000) * 15.00
        return input_cost + output_cost
```

---

## 4. Communication Protocols

### Agent-to-Agent Communication

**Method 1: JSON Files (Recommended for large data)**
```python
# Agent A (Producer)
output_path = Path("workspace/intermediate/parsed_document.json")
output_path.write_text(parsed_doc.model_dump_json())

# Agent B (Consumer)
parsed_doc = ParsedDocument.model_validate_json(
    Path("workspace/intermediate/parsed_document.json").read_text()
)
```

**Method 2: Return Values (For small data)**
```python
# Synchronous
result = await agent.execute(input_data)
next_input = result.output

# Asynchronous gathering
results = await asyncio.gather(*[agent.execute(data) for agent in agents])
```

### Workspace Structure
```
workspace/
├── inputs/                    # User-provided inputs
│   ├── submission.pdf
│   └── grading_request.json
├── intermediate/              # Agent-to-agent data
│   ├── parsed_document.json
│   ├── evaluations/
│   │   ├── prd_quality.json
│   │   ├── code_structure.json
│   │   └── unit_tests.json
│   └── scoring_result.json
└── outputs/                   # Final deliverables
    ├── grading_report.md
    ├── grading_report.pdf
    └── grading_result.json
```

---

## 5. Testing Strategy

### Unit Tests (Per Agent)
```python
# tests/agents/test_parser_agent.py
@pytest.mark.asyncio
async def test_parser_agent_valid_pdf():
    agent = ParserAgent({"engine": "pymupdf"})
    result = await agent.execute(Path("tests/fixtures/sample.pdf"))
    
    assert result.success
    assert result.output.total_pages > 0

@pytest.mark.asyncio
async def test_parser_agent_fallback():
    agent = ParserAgent({
        "engine": "pymupdf",
        "fallback_engine": "pdfplumber"
    })
    # Test with PDF that requires fallback
    result = await agent.execute(Path("tests/fixtures/complex.pdf"))
    assert result.success
```

### Integration Tests (Multi-Agent)
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_full_workflow():
    orchestrator = OrchestratorAgent(load_config("config/test.yaml"))
    request = GradingRequest(
        pdf_path=Path("tests/fixtures/complete_project.pdf"),
        self_grade=85
    )
    
    result = await orchestrator.execute(request)
    
    assert result.success
    assert result.output.final_score > 0
    assert len(result.output.evaluations) >= 7
```

---

**Last Updated:** November 2025  
**For Implementation:** See AGENTS_TASKS.md
