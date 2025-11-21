# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLIENT INTERFACES                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   FastAPI    │  │  Streamlit   │  │   Rich CLI   │          │
│  │   REST API   │  │    Web UI    │  │   Terminal   │          │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘          │
│         │                  │                  │                   │
└─────────┼──────────────────┼──────────────────┼───────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
┌─────────▼─────────────────────────────────────▼─────────────────┐
│                  ORCHESTRATION LAYER                             │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│              BudgetValidationOrchestrator                        │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  • Receives Budget + Metadata                              │ │
│  │  • Coordinates Validators                                  │ │
│  │  • Aggregates Findings                                     │ │
│  │  • Calculates Risk Level                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────┬──────────────────────┬───────────────────┘
                        │                      │
        ┌───────────────┴──────┐      ┌────────┴────────┐
        │                      │      │                 │
┌───────▼────────────┐ ┌───────▼──────▼──┐  ┌──────────▼──────────┐
│  DETERMINISTIC     │ │   AI AGENTS     │  │    DATA MODELS      │
│   VALIDATORS       │ │                 │  │                     │
├────────────────────┤ ├─────────────────┤  ├─────────────────────┤
│                    │ │                 │  │                     │
│ • Quantity         │ │ StackSpot AI    │  │ • Budget           │
│   Deviation        │ │   Client        │  │ • BudgetItem       │
│                    │ │                 │  │ • Finding          │
│ • Unit Price       │ │ ┌─────────────┐ │  │ • ValidationResult │
│   Threshold        │ │ │ HTTP Client │ │  │ • Severity         │
│                    │ │ │ (httpx)     │ │  │ • RiskLevel        │
│ • Out of Catalog   │ │ └─────────────┘ │  │                     │
│                    │ │                 │  │ (Pydantic Models)   │
│ • [Extensible]     │ │ • analyze_      │  │                     │
│                    │ │   budget_       │  │                     │
│                    │ │   context()     │  │                     │
└────────────────────┘ └─────────────────┘  └─────────────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
            ┌───────▼────────┐  ┌────────▼────────┐
            │ Real API Mode  │  │  Mock Mode      │
            ├────────────────┤  ├─────────────────┤
            │                │  │                 │
            │ HTTP POST to   │  │ Deterministic   │
            │ StackSpot AI   │  │ Responses       │
            │                │  │ (for testing)   │
            └────────────────┘  └─────────────────┘

┌──────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE LAYER                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Dynaconf   │  │    Loguru    │  │   Pydantic   │          │
│  │ Configuration│  │   Logging    │  │  Validation  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  • settings.toml                                                 │
│  • .env                                                          │
│  • Environment-specific configs                                 │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Request Initiation
```
Client → API/UI/CLI → Budget JSON + Metadata
```

### 2. Orchestration
```
Orchestrator receives Budget
    ↓
Run Deterministic Validators (parallel)
    ↓
Collect Findings (List[Finding])
    ↓
Call AI Agent (optional)
    ↓
Get AI Explanations & Risk Assessment
    ↓
Aggregate Findings by Group
    ↓
Calculate Summary & Risk Level
    ↓
Return ValidationResult
```

### 3. Response
```
ValidationResult → Client
    • findings_by_item: List[Finding]
    • findings_by_group: Dict[str, List[Finding]]
    • summary: ValidationSummary
    • explanations: List[str]
```

## Component Responsibilities

### API Layer (`src/construct_cost_ai/api/`)
- **Purpose**: HTTP interface for M2M integration
- **Components**:
  - `app.py`: FastAPI application factory
  - `routes.py`: Endpoint definitions
  - `schemas.py`: Request/response models
- **Responsibilities**:
  - Request validation (Pydantic)
  - Endpoint routing
  - Error handling
  - Orchestrator instantiation

### Domain Layer (`src/construct_cost_ai/domain/`)
- **Purpose**: Core business logic (framework-agnostic)
- **Components**:
  - `models.py`: Domain models (Budget, Finding, etc.)
  - `orchestrator.py`: Validation orchestration
  - `validators/`: Deterministic validators
- **Responsibilities**:
  - Budget validation logic
  - Findings aggregation
  - Risk calculation
  - Validator coordination

### Infrastructure Layer (`src/construct_cost_ai/infra/`)
- **Purpose**: External integrations & cross-cutting concerns
- **Components**:
  - `ai/stackspot_client.py`: StackSpot AI HTTP client
  - `config/config.py`: Dynaconf settings
  - `logging/logging_config.py`: Loguru configuration
- **Responsibilities**:
  - External API calls
  - Configuration management
  - Logging setup

### Presentation Layer
- **API**: `src/construct_cost_ai/api/` (FastAPI)
- **UI**: `app/streamlit_app.py` (Streamlit)
- **CLI**: `cli/main.py` (Typer + Rich)
- **Responsibilities**:
  - User interaction
  - Input collection
  - Result presentation

## Design Principles

### 1. Separation of Concerns
- Domain logic isolated from infrastructure
- Clear boundaries between layers
- Framework-agnostic core

### 2. Object-Oriented Design
- Abstract base classes for validators
- Protocol-based AI agent interface
- Polymorphic validator execution

### 3. Extensibility
- Easy to add new validators
- Pluggable AI agents
- Configuration-driven behavior

### 4. Testability
- Mocked dependencies for tests
- Isolated unit tests
- Integration tests for API

### 5. Observability
- Structured logging (Loguru)
- Execution time tracking
- Error logging with context

## Extension Points

### Adding a New Validator

```python
# 1. Inherit from BaseDeterministicValidator
class MyValidator(BaseDeterministicValidator):
    def validate(self, budget: Budget) -> List[Finding]:
        # Your logic here
        return findings

# 2. Register in orchestrator
orchestrator.add_validator(MyValidator())
```

### Adding a New AI Agent

```python
# 1. Implement BaseAIAgent protocol
class MyAIAgent:
    def analyze_budget_context(self, budget, context=None) -> dict:
        # Your AI logic here
        return {"explanations": [...], "risk_assessment": "..."}

# 2. Inject into orchestrator
orchestrator.set_ai_agent(MyAIAgent())
```

### Adding a New Endpoint

```python
# In src/construct_cost_ai/api/routes.py
@router.post("/my-endpoint")
async def my_endpoint(request: MyRequest):
    # Your logic here
    return response
```

## Technology Choices

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **API Framework** | FastAPI | Modern, async, auto-docs, type hints |
| **Web UI** | Streamlit | Rapid prototyping, data science friendly |
| **CLI** | Typer + Rich | Type-safe args, beautiful terminal output |
| **Configuration** | Dynaconf | Multi-env, multiple sources, type-safe |
| **Logging** | Loguru | Simple API, structured logs, rotation |
| **Validation** | Pydantic | Runtime validation, serialization, docs |
| **HTTP Client** | httpx | Async support, modern API |
| **Testing** | pytest | Industry standard, plugins, fixtures |

## Deployment Considerations

### Environment Variables
- `ENV_FOR_DYNACONF`: Switch between dev/prod configs
- `STACKSPOT_AI_API_KEY`: API authentication
- `LOG_LEVEL`: Control verbosity

### Scaling
- FastAPI is async-ready for concurrent requests
- Validators run sequentially (can be parallelized)
- AI calls are I/O-bound (async benefits)

### Monitoring
- Logs in `logs/construct_cost_ai.log`
- Execution time tracked per validation
- Error logs with full stack traces
