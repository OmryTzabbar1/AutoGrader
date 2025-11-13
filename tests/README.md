# AutoGrader Test Suite

Comprehensive test suite for the AutoGrader multi-agent grading system.

## Test Structure

```
tests/
├── unit/                   # Unit tests for individual components
│   ├── agents/            # Agent tests
│   ├── skills/            # Skill tests
│   └── models/            # Model tests
├── integration/           # Integration tests for workflows
├── fixtures/              # Test data and fixtures
├── conftest.py           # Shared pytest fixtures
└── mocks.py              # Mock objects for testing
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/unit -m unit

# Integration tests only
pytest tests/integration -m integration

# Exclude slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Test single file
pytest tests/unit/agents/test_validation_agent.py

# Test single test
pytest tests/unit/agents/test_validation_agent.py::TestValidationAgent::test_valid_request
```

## Test Markers

Tests are organized with pytest markers:

- `@pytest.mark.unit`: Unit tests for individual components
- `@pytest.mark.integration`: Integration tests for workflows
- `@pytest.mark.slow`: Tests that take significant time
- `@pytest.mark.api`: Tests requiring API access (skip by default)

## Fixtures

Common fixtures are defined in `conftest.py`:

### Path Fixtures
- `test_data_dir`: Path to test data directory
- `temp_workspace`: Temporary workspace directory
- `temp_config_file`: Temporary config file

### Model Fixtures
- `sample_code_block`: Sample code block
- `sample_section`: Sample document section
- `sample_parsed_document`: Complete parsed document
- `sample_criterion_evaluation`: Sample evaluation
- `sample_grading_result`: Complete grading result

### Mock Fixtures
- `mock_claude_response`: Mock Claude API response
- `mock_llm_skill`: Mock LLM evaluation skill
- `mock_pdf_skill`: Mock PDF processing skill

## Mock Objects

The `tests/mocks.py` module provides mock implementations:

- `MockClaudeAPI`: Simulates Claude API without actual calls
- `MockPDFParser`: Simulates PDF parsing
- `MockCostTracker`: Simulates cost tracking

Example usage:

```python
from tests.mocks import MockClaudeAPI

mock_api = MockClaudeAPI(default_score=85.0)
result = await mock_api.evaluate(prompt, context)
```

## Writing Tests

### Unit Test Example

```python
import pytest
from agents.validation_agent import ValidationAgent

@pytest.mark.unit
@pytest.mark.asyncio
async def test_validation(tmp_path):
    \"\"\"Test validation agent.\"\"\"
    agent = ValidationAgent({})

    pdf_path = tmp_path / "test.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    request = GradingRequest(pdf_path=pdf_path, self_grade=85)
    result = await agent.execute(request)

    assert result.success
    assert result.output.is_valid
```

### Integration Test Example

```python
import pytest
from unittest.mock import patch
from tests.mocks import MockClaudeAPI

@pytest.mark.integration
@pytest.mark.asyncio
async def test_workflow(tmp_path):
    \"\"\"Test complete grading workflow.\"\"\"
    with patch('skills.llm_evaluation_skill.LLMEvaluationSkill'):
        # Test workflow
        pass
```

## Coverage Goals

Target coverage by component:

- **Skills**: 90%+ coverage
- **Agents**: 85%+ coverage
- **Models**: 95%+ coverage (mostly dataclasses)
- **CLI**: 70%+ coverage
- **Overall**: 85%+ coverage

## Test Data

Test fixtures and sample PDFs are stored in `tests/fixtures/`:

- Sample PDFs for parsing tests
- Example evaluations
- Mock API responses
- Configuration samples

## Continuous Integration

Tests run automatically on:
- Pull requests
- Commits to main branch
- Nightly builds

CI configuration: `.github/workflows/test.yml`

## Troubleshooting

### Tests Fail with Import Errors

Ensure `src/` is in Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:${PWD}/src"
```

### Async Tests Not Running

Install pytest-asyncio:
```bash
pip install pytest-asyncio
```

### Coverage Reports Not Generated

Install pytest-cov:
```bash
pip install pytest-cov
```

## Best Practices

1. **Use fixtures**: Reuse common setups via fixtures
2. **Mock external dependencies**: Don't make real API calls
3. **Test edge cases**: Include boundary conditions and errors
4. **Keep tests fast**: Unit tests should run in milliseconds
5. **Descriptive names**: Test names should describe what they test
6. **One assertion focus**: Each test should verify one thing
7. **Arrange-Act-Assert**: Structure tests clearly

## Adding New Tests

When adding new components:

1. Create test file in appropriate directory
2. Use existing fixtures from `conftest.py`
3. Add new fixtures if needed
4. Mark tests with appropriate markers
5. Run tests and verify coverage
6. Update this README if adding new patterns

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [unittest.mock](https://docs.python.org/3/library/unittest.mock.html)
