# Quick Start Guide

This guide will help you get Construct Cost AI up and running in minutes.

## Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- Git (optional, for cloning)

## Installation Steps

### 1. Get the Code

```bash
# If using Git
git clone https://github.com/emersonrafaels/construct-cost-ai.git
cd construct-cost-ai

# Or download and extract the ZIP file, then navigate to the folder
```

### 2. Create Virtual Environment

**Windows (PowerShell):**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux/Mac:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

**Option A: Using pip (recommended for users)**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Optional: for development/testing
```

**Option B: Using setuptools (recommended for developers)**
```bash
pip install -e ".[dev]"
```

### 4. Configure Environment

```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` to add your StackSpot AI API key (optional for testing, uses mock mode by default):
```env
STACKSPOT_AI_API_KEY=your-api-key-here
```

## Running the Application

### Option 1: FastAPI REST API

**Start the server:**
```bash
# Using the run script
python run_api.py

# Or using uvicorn directly
uvicorn construct_cost_ai.api.app:app --reload --host 0.0.0.0 --port 8000
```

**Test the API:**
1. Open http://localhost:8000/docs in your browser
2. Try the `/health` endpoint
3. Use `/validate-budget` with the sample data:

```bash
# Windows (PowerShell)
Invoke-WebRequest -Uri http://localhost:8000/validate-budget `
  -Method POST `
  -ContentType "application/json" `
  -InFile examples/sample_budget.json

# Linux/Mac
curl -X POST "http://localhost:8000/validate-budget" \
  -H "Content-Type: application/json" \
  -d @examples/sample_budget.json
```

### Option 2: Streamlit Web UI

**Start Streamlit:**
```bash
streamlit run app/streamlit_app.py
```

**Use the UI:**
1. Browser opens automatically at http://localhost:8501
2. Upload `examples/sample_budget.json`
3. Fill in metadata (Residential, 150m², SP)
4. Click "Validate Budget"

### Option 3: CLI Tool

**Basic validation:**
```bash
# Using the installed command
construct-cost-cli validate examples/sample_budget.json \
  --archetype Residential \
  --area 150 \
  --region SP

# Or using Python module
python -m construct_cost_ai.cli.main validate examples/sample_budget.json \
  --archetype Residential \
  --area 150 \
  --region SP
```

**Save results to file:**
```bash
construct-cost-cli validate examples/sample_budget.json \
  --archetype Residential \
  --area 150 \
  --region SP \
  --output results.json
```

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=construct_cost_ai --cov-report=html

# View coverage report
# Windows
start htmlcov/index.html

# Linux/Mac
open htmlcov/index.html
```

## Next Steps

1. **Customize Validators**: Edit `src/construct_cost_ai/domain/validators/deterministic.py`
2. **Configure Thresholds**: Edit `settings.toml`
3. **Integrate Real AI**: Set `mock_mode=False` in StackSpot client
4. **Add Your Data**: Create reference databases for LPU, SINAPI, etc.

## Troubleshooting

### Import Errors

If you see import errors like `Import "loguru" could not be resolved`:
```bash
pip install -r requirements.txt
```

### Port Already in Use

If port 8000 or 8501 is busy:
```bash
# FastAPI - use different port
uvicorn construct_cost_ai.api.app:app --port 8001

# Streamlit - use different port
streamlit run app/streamlit_app.py --server.port 8502
```

### Virtual Environment Not Activated

Make sure you see `(venv)` in your terminal prompt. If not:
```bash
# Windows
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

## Common Commands Reference

| Task | Command |
|------|---------|
| Start API | `python run_api.py` |
| Start Streamlit | `streamlit run app/streamlit_app.py` |
| Run CLI | `construct-cost-cli validate <file>` |
| Run tests | `pytest` |
| Format code | `black src/` |
| Lint code | `ruff check src/` |

## Support

- **Documentation**: See [README.md](README.md) for full documentation
- **Issues**: Open an issue on GitHub
- **Examples**: Check `examples/` directory for sample data

Happy validating! 🏗️
