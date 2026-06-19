# CPG Sales Analytics Platform

A full-stack data platform for CPG sales performance analysis — featuring a data pipeline, revenue forecasting, AI-powered insights, and a business dashboard.

## Architecture

```
Raw CSVs → Ingestion Pipeline → DuckDB → ML Model (Linear Regression)
                                       → Groq LLM (Natural Language Insights)
                                       → FastAPI (REST API)
                                       → Streamlit Dashboard
```

## Quick Start (Docker — recommended)

Prerequisites: Docker Desktop installed, `.env` file configured.

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd <project-dir>

# 2. Copy environment template and add your Groq API key
cp .env.example .env
# Edit .env and set GROQ_API_KEY (free at console.groq.com)

# 3. Start everything
docker-compose up --build

# 4. Open the dashboard
# UI:  http://localhost:8501
# API: http://localhost:8000/docs
```

## Local Development Setup

```bash
# Python 3.11+ required
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Generate synthetic data
python scripts/generate_data.py

# Run ingestion pipeline (creates DuckDB)
python -m src.ingestion.db

# Train forecasting model
python -m src.forecasting.model

# Start API
uvicorn src.api.main:app --reload

# Start UI (new terminal)
streamlit run ui/app.py

# Run tests
pytest tests/ -v
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | Optional | `""` | Free API key from console.groq.com. AI features degrade gracefully without it. |
| `DATABASE_PATH` | No | `data/cpg_sales.duckdb` | Path to DuckDB file |
| `MODEL_PATH` | No | `models/revenue_forecast.joblib` | Path to trained model |
| `DATA_DIR` | No | `data/raw` | Directory containing raw CSVs |
| `API_PORT` | No | `8000` | FastAPI port |

## API Reference

Interactive docs available at `http://localhost:8000/docs` when running.

Key endpoints:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Service health check and DB connectivity |
| `GET` | `/api/metrics` | Aggregate KPIs: revenue, transactions, AOV, top categories/regions, monthly trend |
| `GET` | `/api/categories` | List of all product categories |
| `GET` | `/api/regions` | List of all sales regions |
| `POST` | `/api/forecast` | Revenue predictions by category, region, and months ahead |
| `POST` | `/api/ask` | Natural language Q&A over sales data (powered by Groq LLM) |
| `POST` | `/api/summarize` | AI-generated trend summaries, with optional category/region filters |

## Project Structure

```
├── src/
│   ├── config.py           # Centralized config via pydantic-settings
│   ├── ingestion/          # Data loading, cleaning, DuckDB storage
│   ├── forecasting/        # Feature engineering, model training, prediction
│   ├── insights/           # Groq LLM integration, Q&A, summarization
│   └── api/                # FastAPI app, routers, schemas
├── ui/app.py               # Streamlit dashboard
├── scripts/generate_data.py # Synthetic data generation
├── tests/                  # pytest test suite
├── docs/                   # ADRs and extension points
├── Dockerfile.api
├── Dockerfile.ui
├── docker-compose.yml
└── .github/workflows/ci.yml
```

## Running Tests

```bash
pytest tests/ -v
```

Tests use an in-memory DuckDB database seeded with synthetic data — no external services required.

## Extending This System

See [docs/extension-points.md](docs/extension-points.md) for documented extension points covering authentication, PostgreSQL migration, real data ingestion, better forecasting models, scheduled pipelines, observability, and LLM provider swapping.
