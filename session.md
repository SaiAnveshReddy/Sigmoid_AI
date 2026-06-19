# SYSTEM DIRECTIVE FOR AI
Whenever you read this file at the start of a new session, you must automatically assume the responsibility of updating it before we conclude. Continuously overwrite outdated granular tasks with high-level macro-achievements to conserve tokens. Keep descriptions strictly factual and concise.

## 1. Core Objective
Build a CPG sales analytics skeleton: ingest/clean synthetic transaction data → ML revenue forecasting → LLM-powered insights (Groq) → FastAPI REST API → Streamlit dashboard → Docker + GitHub Actions CI.

## 2. Architecture & Tech Stack
- **Language:** Python 3.11
- **Database:** DuckDB (data/cpg_sales.duckdb) — 3 tables: transactions, products, stores
- **ML:** scikit-learn LinearRegression pipeline (models/revenue_forecast.joblib)
- **LLM:** Groq API (llama-3.3-70b-versatile) via `groq` SDK — graceful degradation if key missing
- **API:** FastAPI + Uvicorn (port 8000), Pydantic v2 schemas
- **UI:** Streamlit (port 8501), 4 pages: Overview, Forecast, AI Insights, Data Explorer
- **Config:** pydantic-settings, .env file
- **Infra:** Docker (Dockerfile.api + Dockerfile.ui + docker-compose.yml), GitHub Actions CI

## 3. Completed Milestones
* Project scaffold: all dirs, requirements.txt, pyproject.toml, .gitignore, .env.example
* Synthetic data generation: 30k transactions, 30 products, 20 stores with realistic quality issues
* Ingestion pipeline: load → clean (dedup, nulls, date normalization, negative prices) → DuckDB upsert
* ML model: monthly aggregation, feature engineering (sin/cos months, lag, label encoding), LinearRegression, joblib serialization
* LLM integration: Groq client with graceful degradation; summarize() and answer_question() functions
* FastAPI: 7 endpoints (/health, /api/metrics, /api/categories, /api/regions, /api/forecast, /api/summarize, /api/ask)
* Streamlit UI: 4-page dashboard wired to all API endpoints
* Tests: 96 tests passing (test_ingestion, test_forecasting, test_insights, test_api)
* Docker: Dockerfile.api, Dockerfile.ui, docker-compose.yml with healthcheck
* CI: .github/workflows/ci.yml (lint + test + docker build)
* Docs: README.md, docs/adr/001-database-choice.md, docs/extension-points.md
* Git: initialized, initial commit 5943d54

## 4. Current State & Immediate Next Steps
* **Where we stopped:** All code complete, 96/96 tests passing, end-to-end smoke tested (data generated + ingested, model trained, all API endpoints verified live). Git committed.
* **Next immediate action:** User needs to (1) get free Groq API key at console.groq.com, (2) put it in .env, (3) run `docker-compose up --build` OR run locally per README. Then record video demo.
* **Known Bugs/Blockers:** None. GROQ_API_KEY placeholder in .env causes graceful degradation (correct behavior — swap for real key to enable AI features).
