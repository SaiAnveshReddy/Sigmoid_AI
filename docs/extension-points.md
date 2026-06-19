# Extension Points for the Inheriting Team

This document describes what to build next and where to plug in.

## 1. Authentication & Authorization

**Where:** Add FastAPI middleware in `src/api/main.py`  
**What:** JWT tokens or API keys. Add `Authorization: Bearer <token>` header validation.  
**Why not done:** Out of scope for skeleton; document it as the first production requirement.

## 2. Database Migration to PostgreSQL

**Where:** `src/ingestion/db.py` — replace `duckdb.connect()` with SQLAlchemy engine  
**What:** All SQL is ANSI-compatible. Add `POSTGRES_URL` env var, switch connection factory.  
**Why not done:** DuckDB removes the server dependency from the skeleton.

## 3. Real Data Ingestion (Replace Synthetic Data)

**Where:** `scripts/generate_data.py` → replace with `scripts/ingest_from_s3.py` or `scripts/ingest_from_api.py`  
**What:** Connect to real POS feeds. The `src/ingestion/cleaner.py` pipeline is already designed for real-world quality issues.  
**Contract:** Output must be CSVs with the same column schema in `data/raw/`.

## 4. Better Forecasting Models

**Where:** `src/forecasting/model.py` — swap the sklearn Pipeline  
**What:** Facebook Prophet for time-series seasonality; XGBoost for more features; or external ML platform (Vertex AI, SageMaker).  
**Contract:** `predictor.py` interface is stable — just change what `model_bundle` contains.

## 5. Scheduled Ingestion & Retraining

**Where:** Add `scripts/scheduled_pipeline.py` triggered by cron / Airflow / Prefect  
**What:** Daily ingestion run + model retraining when data drifts (track MAE over time).

## 6. Observability

**Where:** `src/api/main.py` — add Prometheus middleware  
**What:** Track request latency, prediction count, LLM call latency.

## 7. LLM Upgrade / Multi-Provider

**Where:** `src/insights/llm_client.py` — the single integration point  
**What:** Swap Groq for Anthropic Claude or OpenAI. Add retry logic, caching of repeated prompts.
