# CPG Sales Analytics Platform

A full-stack data platform for CPG (Consumer Packaged Goods) sales performance analysis — featuring a data ingestion pipeline, ML revenue forecasting, AI-powered natural language insights, a REST API, and a business dashboard.

Built as part of the Sigmoid AIA Engineer take-home evaluation.

---

## Architecture

```
Raw CSVs  ──►  Ingestion Pipeline  ──►  DuckDB (local database)
                                              │
                              ┌───────────────┼───────────────┐
                              ▼               ▼               ▼
                     ML Model          Gemini LLM        FastAPI
                  (LinearRegression)  (AI Insights)    (REST API)
                                                            │
                                                            ▼
                                                    Streamlit Dashboard
                                                      localhost:8501
```

**Tech stack at a glance:**

| Layer | Technology |
|---|---|
| Database | DuckDB (embedded, no server needed) |
| ML | scikit-learn LinearRegression |
| AI/LLM | Google Gemini 2.5 Flash (free tier) |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit |
| Tests | pytest (96 tests) |
| Infra | Docker + GitHub Actions CI |

---

## Prerequisites

- **Python 3.11 or higher** — check with `python --version`
- **pip** — comes with Python
- A **Google Gemini API key** (free, no billing required) — get one at [aistudio.google.com](https://aistudio.google.com) → Get API key

---

## Local Setup — Step by Step

### Step 1: Clone the repository

```bash
git clone https://github.com/SaiAnveshReddy/Sigmoid_AI.git
cd Sigmoid_AI
```

### Step 2: Create and activate a virtual environment

**Windows (PowerShell or CMD):**
```
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

You should see `(.venv)` in your terminal prompt after activation.

### Step 3: Install dependencies

```
pip install -r requirements.txt
```

This installs all required packages: DuckDB, pandas, scikit-learn, FastAPI, Streamlit, Google Gemini SDK, and more.

### Step 4: Configure environment variables

Copy the example environment file and add your Gemini API key:

**Windows:**
```
copy .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Open `.env` in any text editor and set your key:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

All other values in `.env` can stay as defaults.

> **Note:** The AI features (summarize, Q&A) degrade gracefully if `GEMINI_API_KEY` is not set — the rest of the platform still works normally.

### Step 5: Generate synthetic data

```
python scripts/generate_data.py
```

This creates three CSV files in `data/raw/`:
- `products.csv` — 30 CPG products across Beverages, Snacks, and Dairy
- `stores.csv` — 20 stores across 4 regions (North, South, East, West)
- `transactions.csv` — ~30,000 transactions over 3 years with intentional quality issues

### Step 6: Run the ingestion pipeline

```
set PYTHONPATH=%CD%
python -m src.ingestion.db
```

**macOS / Linux:**
```bash
PYTHONPATH=$(pwd) python -m src.ingestion.db
```

This cleans the raw data and loads 27,657 rows into `data/cpg_sales.duckdb`.

### Step 7: Train the forecasting model

```
set PYTHONPATH=%CD%
python -m src.forecasting.model
```

**macOS / Linux:**
```bash
PYTHONPATH=$(pwd) python -m src.forecasting.model
```

This trains a LinearRegression model and saves it to `models/revenue_forecast.joblib`.

---

## Running the Application

You need **two terminal windows** open at the same time — one for the API, one for the dashboard.

### Terminal 1 — Start the API server

**Windows:**
```
set PYTHONPATH=%CD%
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

**macOS / Linux:**
```bash
PYTHONPATH=$(pwd) uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Wait until you see:
```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Terminal 2 — Start the Streamlit dashboard

**Windows:**
```
python -m streamlit run ui/app.py --server.port 8501
```

**macOS / Linux:**
```bash
streamlit run ui/app.py --server.port 8501
```

Wait until you see:
```
  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```

### Open in your browser

| Service | URL |
|---|---|
| Dashboard | http://localhost:8501 |
| API (interactive docs) | http://localhost:8000/docs |
| API health check | http://localhost:8000/health |

---

## Dashboard Pages

| Page | What you see |
|---|---|
| **Overview** | Total revenue (~$2.4M), transactions, avg order value, revenue by category and region, monthly trend chart |
| **Revenue Forecast** | Select category + region + months ahead → LinearRegression prediction chart |
| **AI Insights** | Gemini-generated summaries of your data; ask any question in plain English |
| **Data Explorer** | Raw monthly revenue table, system info, DB/model status |

---

## Running Tests

```
set PYTHONPATH=%CD%
pytest tests/ -v
```

**macOS / Linux:**
```bash
PYTHONPATH=$(pwd) pytest tests/ -v
```

Expected output: **96 passed**. All tests use a temporary in-memory DuckDB — no external services or API keys needed.

---

## Docker Setup (alternative)

If you have Docker Desktop installed, you can run everything in containers:

```bash
# 1. Copy and configure .env
cp .env.example .env
# Edit .env and set GEMINI_API_KEY

# 2. Build and start both services
docker-compose up --build

# 3. Open in browser
# Dashboard: http://localhost:8501
# API docs:  http://localhost:8000/docs
```

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | Optional | `""` | Free Google Gemini key from aistudio.google.com. AI features degrade gracefully without it. |
| `DATABASE_PATH` | No | `data/cpg_sales.duckdb` | Path to DuckDB database file |
| `MODEL_PATH` | No | `models/revenue_forecast.joblib` | Path to trained ML model |
| `DATA_DIR` | No | `data/raw` | Directory containing raw CSV files |
| `API_HOST` | No | `0.0.0.0` | FastAPI bind address |
| `API_PORT` | No | `8000` | FastAPI port |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |

---

## API Reference

Interactive docs with request/response examples: `http://localhost:8000/docs`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Service health check and DB connectivity |
| `GET` | `/api/metrics` | Aggregate KPIs: revenue, transactions, AOV, top categories/regions, monthly trend |
| `GET` | `/api/categories` | List all product categories |
| `GET` | `/api/regions` | List all sales regions |
| `POST` | `/api/forecast` | Revenue predictions by category, region, and months ahead |
| `POST` | `/api/summarize` | AI-generated trend summary (optional category/region filter) |
| `POST` | `/api/ask` | Natural language Q&A over sales data |

---

## Project Structure

```
├── src/
│   ├── config.py               # Centralized config via pydantic-settings (.env)
│   ├── ingestion/
│   │   ├── loader.py           # Load raw CSVs into DataFrames
│   │   ├── cleaner.py          # Remove dupes, nulls, bad dates, negative prices
│   │   └── db.py               # DuckDB schema, upserts, pipeline orchestration
│   ├── forecasting/
│   │   ├── features.py         # Feature engineering (sin/cos encoding, lag)
│   │   ├── model.py            # Train and save LinearRegression pipeline
│   │   └── predictor.py        # Load model and generate predictions
│   ├── insights/
│   │   ├── llm_client.py       # Google Gemini API wrapper (graceful degradation)
│   │   └── summarizer.py       # Build prompts from DB data, call LLM
│   └── api/
│       ├── main.py             # FastAPI app, lifespan (auto-ingest + auto-train)
│       ├── routers/            # Route handlers: metrics, forecast, insights
│       └── schemas.py          # Pydantic v2 request/response models
├── ui/
│   └── app.py                  # Streamlit 4-page dashboard
├── scripts/
│   └── generate_data.py        # Synthetic CPG data generator (seed=42)
├── tests/                      # 96 pytest tests (no mocked DB)
├── docs/
│   ├── adr/001-database-choice.md
│   └── extension-points.md
├── Dockerfile.api
├── Dockerfile.ui
├── docker-compose.yml
├── .github/workflows/ci.yml
├── .env.example
└── requirements.txt
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'src'`**
You need to set `PYTHONPATH` before running any `python` or `pytest` command:
- Windows: `set PYTHONPATH=%CD%`
- macOS/Linux: `export PYTHONPATH=$(pwd)`

**`localhost:8501` — site can't be reached**
Both servers must be running simultaneously in separate terminal windows. Make sure Terminal 1 (API) shows "Application startup complete" before opening the browser.

**`AI insights unavailable` message in dashboard**
`GEMINI_API_KEY` is not set in `.env`. The platform works without it — only the AI Insights page is affected.

**`FileNotFoundError: data/raw/transactions.csv`**
Run `python scripts/generate_data.py` first (Step 5).

**`FileNotFoundError: models/revenue_forecast.joblib`**
Run `python -m src.forecasting.model` first (Step 7). The API auto-trains on startup, so this resolves itself once the API starts.
