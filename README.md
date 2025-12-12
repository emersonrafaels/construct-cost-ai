# Construct Cost AI - Budget Validation Orchestration Service

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**Construct Cost AI** is an intelligent orchestration service for validating construction cost estimates (budgets). It combines **deterministic rule-based validators** with **AI-powered analysis** (via StackSpot AI) to identify pricing anomalies, quantity deviations, and out-of-catalog items in construction budgets.

## 🎯 Purpose

This service validates construction budgets submitted by suppliers by:
- Applying **business rules and thresholds** (quantity limits, price ranges, catalog validation)
- Leveraging **AI agents** for contextual analysis and risk assessment
- Providing **structured findings** with severity levels and natural-language explanations
- Supporting multiple interfaces: **REST API**, **Streamlit UI**, and **CLI**

## 🏗️ Architecture

**Construct Cost AI** is designed as an **orchestration layer** (not a monolith):

- **Object-oriented design** for extensibility
- **Deterministic validators**: Rule-based checks (LPU, SINAPI, thresholds)
- **AI agents**: Probabilistic analysis via StackSpot AI HTTP API
- **Clean separation**: Domain logic, infrastructure, API, and UI layers

```
src/construct_cost_ai/
├── api/                 # FastAPI REST endpoints
├── domain/              # Core business logic
│   ├── models.py        # Pydantic domain models
│   ├── orchestrator.py  # Main orchestration class
│   └── validators/      # Deterministic validators
├── infra/               # Infrastructure layer
│   ├── ai/              # StackSpot AI client
│   ├── config/          # Dynaconf configuration
│   └── logging/         # Loguru logging setup
app/                     # Streamlit frontend
cli/                     # Rich-based CLI
tests/                   # pytest test suite
```

## ✨ Features

### Core Capabilities
- ✅ **Quantity deviation detection** (compare vs. reference data)
- ✅ **Unit price anomaly detection** (compare vs. SINAPI/LPU tables)
- ✅ **Out-of-catalog validation** (identify non-standard items)
- ✅ **AI-powered contextual analysis** (risk assessment, explanations)
- ✅ **Findings aggregation** (by item and by service group)
- ✅ **Risk level calculation** (LOW, MEDIUM, HIGH, CRITICAL)

### Interfaces
- 🌐 **FastAPI REST API** (for M2M integration, e.g., Salesforce)
- 🖥️ **Streamlit web UI** (interactive file upload and visualization)
- 💻 **Rich CLI** (terminal-based validation with pretty tables)

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- pip or uv

### Installation

```bash
# Clone the repository
git clone https://github.com/emersonrafaels/construct-cost-ai.git
cd construct-cost-ai

# Create and activate virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

# Install dependencies
pip install -e ".[dev]"
```

### Configuration

1. Copy the example environment file:
```bash
copy .env.example .env
```

2. Edit `.env` and add your StackSpot AI credentials:
```env
STACKSPOT_AI_BASE_URL=https://api.stackspot.ai/v1
STACKSPOT_AI_API_KEY=your-api-key-here
```

> **Note**: The service runs in **mock mode** by default (AI calls return simulated responses). Set `mock_mode=False` in code to enable real API calls.

## 📖 Usage

### 1️⃣ FastAPI REST API

Start the API server:

```bash
uvicorn construct_cost_ai.api.app:app --reload --host 0.0.0.0 --port 8000
```

Access the interactive API docs at: http://localhost:8000/docs

**Example API call:**

```bash
curl -X POST "http://localhost:8000/validate-budget" \
  -H "Content-Type: application/json" \
  -d @examples/sample_budget.json
```

**Endpoints:**
- `GET /health` - Health check
- `POST /validate-budget` - Validate a budget

### 2️⃣ Streamlit Web UI

Launch the Streamlit app:

```bash
streamlit run app/streamlit_app.py
```

Open your browser at: http://localhost:8501

**Features:**
- Upload budget file (JSON or CSV)
- Input project metadata (archetype, area, region)
- View validation results with interactive tables
- See AI explanations and risk assessment

### 3️⃣ Rich-based CLI

Run validation from the command line:

```bash
# Using the installed CLI command
construct-cost-cli validate examples/sample_budget.json \
  --archetype Residential \
  --area 150 \
  --region SP \
  --output results.json

# Or using Python module
python -m construct_cost_ai.cli.main validate examples/sample_budget.json \
  --archetype Commercial \
  --area 500 \
  --region RJ
```

**CLI Options:**
- `--archetype, -a`: Building archetype (Residential, Commercial, etc.)
- `--area, -s`: Square footage in m²
- `--region, -r`: Region/state code (e.g., SP, RJ)
- `--supplier`: Supplier name (optional)
- `--project-id, -p`: Project ID (optional)
- `--output, -o`: Save results to JSON file

## 🏗️ Geradores de Datasets Realistas

### Geração de Budgets Realistas

O script `create_sample_dataset_realistic_budget.py` permite gerar budgets realistas para diferentes padrões de orçamento utilizados no Itaú Unibanco. Ele suporta os seguintes padrões:

1. **Padrão 1 (sample_padrao1.xlsx)**
   - Estrutura com abas "Resumo" e "01".
   - Valores calculados dinamicamente com base em itens e capítulos.

2. **Padrão 2 - JAPJ (sample_padrao2_japj.xlsx)**
   - Planilha modelo JAPJ com aba "LPU".
   - Inclui cabeçalho detalhado e itens específicos.

3. **Padrão 2 - FG (sample_padrao2_fg.xlsx)**
   - Planilha modelo FG com aba "LPU".
   - Similar ao padrão JAPJ, mas com dados específicos para FG.

### Exemplo de Uso

```python
from create_sample_dataset_realistic_budget import gerar_sample_padrao1, gerar_sample_padrao2_japj, gerar_sample_padrao2_fg
from pathlib import Path

# Diretório de saída
output_dir = Path("output")
output_dir.mkdir(exist_ok=True)

# Gerar budgets realistas
data_inputs = output_dir

gerar_sample_padrao1(data_inputs=data_inputs)
gerar_sample_padrao2_japj(data_inputs=data_inputs)
gerar_sample_padrao2_fg(data_inputs=data_inputs)
```

Os arquivos gerados serão salvos no diretório especificado (`output`).

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=construct_cost_ai --cov-report=html

# Run specific test file
pytest tests/test_orchestrator.py -v
```

## ⚙️ Configuration

Configuration is managed via **Dynaconf** with multiple sources:

1. **`settings.toml`** - Default settings
2. **`.env`** - Environment variables
3. **`.secrets.toml`** - Secrets (gitignored)

### Key Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `stackspot_ai_base_url` | StackSpot AI API base URL | `https://api.stackspot.ai/v1` |
| `stackspot_ai_api_key` | API key for authentication | (required) |
| `log_level` | Logging level | `INFO` |
| `quantity_deviation_threshold` | Max quantity deviation | `0.15` (15%) |
| `unit_price_deviation_threshold` | Max price deviation | `0.20` (20%) |

### Environment-Specific Settings

Switch environments using:
```bash
export ENV_FOR_DYNACONF=production
```

Environments: `development` (default), `production`

## 📊 Logging

Logging is handled by **Loguru** with structured, leveled output:

- **Console**: Colored, human-readable logs
- **File**: JSON-formatted logs with rotation (configurable)

Logs are stored in `logs/construct_cost_ai.log` (configurable via `settings.toml`).

**Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 🔌 Extending the Service

### Adding a New Deterministic Validator

1. Create a new class in `src/construct_cost_ai/domain/validators/`:

```python
from construct_cost_ai.domain.validators.base import BaseDeterministicValidator
from construct_cost_ai.domain.models import Budget, Finding

class MyCustomValidator(BaseDeterministicValidator):
    def __init__(self):
        super().__init__(name="My Custom Validator")
    
    def validate(self, budget: Budget) -> list[Finding]:
        findings = []
        # Your validation logic here
        return findings
```

2. Register it in the orchestrator:

```python
from construct_cost_ai.domain.orchestrator import BudgetValidationOrchestrator

orchestrator = BudgetValidationOrchestrator()
orchestrator.add_validator(MyCustomValidator())
```

### Integrating Real StackSpot AI

To use real StackSpot AI instead of mock responses:

1. Set your API key in `.env`
2. Modify the client initialization:

```python
from construct_cost_ai.infra.ai import StackSpotAIClient

ai_client = StackSpotAIClient(mock_mode=False)
```

## 📝 Data Models

### Input: Budget

```json
{
  "items": [
    {
      "item_id": "item_001",
      "code": "SINAPI_88307",
      "description": "CONCRETO FCK >= 25MPA",
      "group": "Structural",
      "quantity": 15.5,
      "unit": "m³",
      "unit_price": 425.50,
      "total_price": 6595.25
    }
  ],
  "metadata": {
    "archetype": "Residential",
    "square_footage": 150.0,
    "region": "SP",
    "supplier": "ABC Construtora",
    "project_id": "PRJ-2025-001"
  }
}
```

### Output: Validation Result

```json
{
  "findings_by_item": [
    {
      "code": "PRICE_ANOMALY_001",
      "severity": "WARNING",
      "message": "Unit price deviation of 22% for item 'CONCRETO...'",
      "item_id": "item_001",
      "group": "Structural",
      "validator": "Unit Price Threshold Validator"
    }
  ],
  "findings_by_group": {
    "Structural": [...],
    "Finishing": [...]
  },
  "summary": {
    "total_items": 6,
    "items_with_findings": 3,
    "total_findings": 5,
    "findings_by_severity": {
      "WARNING": 3,
      "ERROR": 2
    },
    "risk_level": "MEDIUM",
    "execution_time_ms": 125.5
  },
  "explanations": [
    "Analysis of 6 budget items totaling R$ 35,683.75...",
    "Several items show price deviations..."
  ]
}
```

## 🛠️ Tech Stack

- **Language**: Python 3.11+
- **API Framework**: FastAPI
- **Web UI**: Streamlit
- **CLI**: Typer + Rich
- **Configuration**: Dynaconf
- **Logging**: Loguru
- **Data Validation**: Pydantic
- **HTTP Client**: httpx
- **Testing**: pytest

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

## 👥 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 🐛 Troubleshooting

### Import Errors (loguru, dynaconf, etc.)

These are expected during development until dependencies are installed. Run:
```bash
pip install -e ".[dev]"
```

### StackSpot AI Connection Issues

The service runs in **mock mode** by default. To troubleshoot real API calls:
1. Verify API key in `.env`
2. Check logs in `logs/construct_cost_ai.log`
3. Review StackSpot AI client logs

## 📞 Support

For questions or issues:
- Open an issue on GitHub
- Contact: emerson@example.com

---

**Built with ❤️ for smarter construction cost validation**
