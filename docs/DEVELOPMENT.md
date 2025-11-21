# Development Guide

This guide is for developers who want to extend or contribute to Construct Cost AI.

## Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/emersonrafaels/construct-cost-ai.git
cd construct-cost-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\Activate.ps1  # Windows

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### 2. Configure Development Environment

```bash
# Copy example environment
cp .env.example .env

# Edit .env for your local settings
# For development, you can leave mock mode enabled
```

### 3. Verify Installation

```bash
# Run tests
pytest

# Start API (should work without errors)
python run_api.py

# Try CLI
construct-cost-cli version
```

## Code Organization

### Package Structure

```
src/construct_cost_ai/
├── __init__.py           # Package version
├── api/                  # REST API layer
│   ├── app.py            # FastAPI app factory
│   ├── routes.py         # Endpoint definitions
│   └── schemas.py        # Request/response models
├── domain/               # Business logic (framework-agnostic)
│   ├── models.py         # Domain models (Pydantic)
│   ├── orchestrator.py   # Main orchestration logic
│   └── validators/       # Validator implementations
│       ├── base.py       # Abstract base classes
│       └── deterministic.py  # Concrete validators
└── infra/                # Infrastructure concerns
    ├── ai/
    │   └── stackspot_client.py  # StackSpot AI HTTP client
    ├── config/
    │   └── config.py     # Dynaconf configuration
    └── logging/
        └── logging_config.py    # Loguru setup
```

### Design Principles

1. **Domain-Driven Design**: Core logic in `domain/`, independent of frameworks
2. **Dependency Inversion**: Abstractions (base classes) in domain, implementations in infra
3. **Single Responsibility**: Each module has one clear purpose
4. **Open-Closed**: Easy to extend without modifying existing code

## Adding New Features

### Adding a New Validator

**Step 1**: Create the validator class

```python
# src/construct_cost_ai/domain/validators/deterministic.py

from construct_cost_ai.domain.validators.base import BaseDeterministicValidator
from construct_cost_ai.domain.models import Budget, Finding, Severity

class MaterialWasteValidator(BaseDeterministicValidator):
    """Validates material waste factors are within acceptable ranges."""
    
    def __init__(self, max_waste_factor: float = 0.10):
        super().__init__(name="Material Waste Validator")
        self.max_waste_factor = max_waste_factor
    
    def validate(self, budget: Budget) -> list[Finding]:
        findings = []
        
        for item in budget.items:
            waste_factor = self._calculate_waste_factor(item)
            
            if waste_factor > self.max_waste_factor:
                findings.append(
                    Finding(
                        code="WASTE_FACTOR_001",
                        severity=Severity.WARNING,
                        message=f"Waste factor {waste_factor:.1%} exceeds maximum {self.max_waste_factor:.1%}",
                        item_id=item.item_id,
                        group=item.group,
                        details={
                            "waste_factor": waste_factor,
                            "max_allowed": self.max_waste_factor,
                        },
                        validator=self.name,
                    )
                )
        
        return findings
    
    def _calculate_waste_factor(self, item):
        # Your calculation logic
        return 0.12  # Placeholder
```

**Step 2**: Register in the orchestrator

```python
# In routes.py or wherever you create the orchestrator
from construct_cost_ai.domain.validators.deterministic import MaterialWasteValidator

validators = [
    QuantityDeviationValidator(),
    UnitPriceThresholdValidator(),
    OutOfCatalogValidator(),
    MaterialWasteValidator(),  # Add here
]
```

**Step 3**: Add tests

```python
# tests/test_validators.py

def test_material_waste_validator(sample_budget):
    validator = MaterialWasteValidator(max_waste_factor=0.10)
    findings = validator.validate(sample_budget)
    
    assert isinstance(findings, list)
    for finding in findings:
        assert finding.code == "WASTE_FACTOR_001"
        assert finding.validator == validator.name
```

### Adding a New API Endpoint

**Step 1**: Define request/response schemas

```python
# src/construct_cost_ai/api/schemas.py

class ExportReportRequest(BaseModel):
    validation_id: str
    format: str = Field(..., pattern="^(pdf|csv|xlsx)$")

class ExportReportResponse(BaseModel):
    download_url: str
    expires_at: datetime
```

**Step 2**: Implement the endpoint

```python
# src/construct_cost_ai/api/routes.py

@router.post("/export-report", response_model=ExportReportResponse)
async def export_report(request: ExportReportRequest):
    """Export validation results in specified format."""
    try:
        # Implementation
        return ExportReportResponse(
            download_url=f"/downloads/{request.validation_id}.{request.format}",
            expires_at=datetime.now() + timedelta(hours=24),
        )
    except Exception as e:
        logger.error(f"Export error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
```

**Step 3**: Add tests

```python
# tests/test_api.py

def test_export_report():
    response = client.post(
        "/export-report",
        json={"validation_id": "test-123", "format": "pdf"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data
```

### Adding a New AI Agent

**Step 1**: Create the agent class

```python
# src/construct_cost_ai/infra/ai/my_custom_agent.py

from construct_cost_ai.domain.models import Budget

class CustomAIAgent:
    """Custom AI agent for specialized analysis."""
    
    def analyze_budget_context(self, budget: Budget, additional_context: dict = None) -> dict:
        # Call your AI service
        # Process results
        return {
            "explanations": ["Custom analysis..."],
            "risk_assessment": "MEDIUM",
            "suggestions": ["Custom suggestion..."],
        }
```

**Step 2**: Use it in the orchestrator

```python
from construct_cost_ai.infra.ai.my_custom_agent import CustomAIAgent

orchestrator = BudgetValidationOrchestrator(
    deterministic_validators=validators,
    ai_agent=CustomAIAgent(),
)
```

## Testing

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_orchestrator.py

# Specific test function
pytest tests/test_api.py::test_health_check -v

# With coverage
pytest --cov=construct_cost_ai --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Writing Tests

**Use fixtures** (defined in `tests/conftest.py`):

```python
def test_my_feature(sample_budget, sample_metadata):
    # sample_budget and sample_metadata are automatically provided
    result = my_function(sample_budget)
    assert result.success
```

**Mock external dependencies**:

```python
from unittest.mock import MagicMock

def test_with_mocked_ai():
    mock_ai = MagicMock()
    mock_ai.analyze_budget_context.return_value = {
        "explanations": ["Test explanation"],
        "risk_assessment": "LOW",
    }
    
    orchestrator = BudgetValidationOrchestrator(
        deterministic_validators=[],
        ai_agent=mock_ai,
    )
    
    # Test behavior
```

### Test Structure

```python
def test_descriptive_name():
    """What this test verifies."""
    # Arrange: Set up test data
    budget = create_test_budget()
    
    # Act: Execute the code under test
    result = validate_budget(budget)
    
    # Assert: Verify expected outcomes
    assert result.success
    assert len(result.findings) == expected_count
```

## Code Quality

### Formatting

```bash
# Format code with Black
black src/ tests/

# Check formatting
black --check src/ tests/
```

### Linting

```bash
# Lint with Ruff
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/
```

### Type Checking

```bash
# Run mypy
mypy src/
```

### Pre-commit Checklist

Before committing, run:
```bash
black src/ tests/
ruff check --fix src/ tests/
pytest
```

## Logging Best Practices

### Use Loguru

```python
from loguru import logger

# Log levels
logger.debug("Detailed diagnostic info")
logger.info("General information")
logger.warning("Warning message")
logger.error("Error occurred")
logger.critical("Critical failure")

# With context
logger.info(f"Processing budget {budget.metadata.project_id}")

# With exception info
try:
    risky_operation()
except Exception as e:
    logger.error(f"Operation failed: {e}", exc_info=True)
```

### Log Important Events

- Validator start/completion
- API requests received
- AI client calls (URL, duration, status)
- Errors with full context
- Performance metrics

## Configuration Management

### Adding New Settings

**Step 1**: Add to `settings.toml`

```toml
[default]
my_new_setting = "default_value"

[development]
my_new_setting = "dev_value"

[production]
my_new_setting = "prod_value"
```

**Step 2**: Use in code

```python
from construct_cost_ai.infra.config import settings

value = settings.get("my_new_setting")
```

**Step 3**: Document in README

Add to the configuration table in README.md.

## Debugging

### Debug API

```bash
# Run with auto-reload
uvicorn construct_cost_ai.api.app:app --reload

# Access logs
tail -f logs/construct_cost_ai.log
```

### Debug Streamlit

```bash
streamlit run app/streamlit_app.py --server.runOnSave true
```

### Debug CLI

```bash
# Add breakpoints with pdb
import pdb; pdb.set_trace()

# Or use rich.inspect
from rich import inspect
inspect(my_object)
```

### Common Issues

**Import errors**: Make sure package is installed in editable mode
```bash
pip install -e .
```

**Config not loading**: Check ENV_FOR_DYNACONF
```bash
echo $ENV_FOR_DYNACONF  # Linux/Mac
echo %ENV_FOR_DYNACONF%  # Windows
```

**Tests failing**: Clear pytest cache
```bash
pytest --cache-clear
```

## Performance Optimization

### Profiling

```python
import time

start = time.time()
result = expensive_operation()
duration = (time.time() - start) * 1000
logger.info(f"Operation took {duration:.2f}ms")
```

### Async Operations

For I/O-bound operations (AI calls, database queries):

```python
async def validate_async(budget: Budget):
    # Use async HTTP client
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
    return response.json()
```

## Git Workflow

### Branch Naming

- `feature/add-material-waste-validator`
- `bugfix/fix-quantity-calculation`
- `docs/update-readme`

### Commit Messages

```
feat: Add material waste factor validator

- Implements MaterialWasteValidator class
- Adds tests for waste factor calculation
- Updates documentation
```

### Pull Request Template

1. **Description**: What does this PR do?
2. **Changes**: List of changes
3. **Testing**: How was it tested?
4. **Screenshots**: If UI changes
5. **Checklist**: Tests pass, docs updated, etc.

## Release Process

1. Update version in `src/construct_cost_ai/__init__.py`
2. Update `pyproject.toml` version
3. Update CHANGELOG.md
4. Create git tag: `git tag v0.2.0`
5. Push tag: `git push origin v0.2.0`

## Deployment

### Environment Variables

Required for production:
```env
ENV_FOR_DYNACONF=production
STACKSPOT_AI_API_KEY=actual-api-key
LOG_LEVEL=WARNING
```

### Docker (Future)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install .

CMD ["uvicorn", "construct_cost_ai.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Pydantic Docs**: https://docs.pydantic.dev/
- **Dynaconf Docs**: https://www.dynaconf.com/
- **Loguru Docs**: https://loguru.readthedocs.io/
- **pytest Docs**: https://docs.pytest.org/

## Getting Help

1. Check documentation (README, ARCHITECTURE, this guide)
2. Look at existing code examples
3. Run tests to see expected behavior
4. Check logs for error details
5. Open an issue on GitHub

Happy coding! 🚀
