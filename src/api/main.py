"""
FastAPI application entry point.

Lifespan
--------
On startup:
  1. Ensure DB schema exists (init_schema).
  2. Run ingestion pipeline if the transactions table is empty.
  3. Train the forecasting model if the model file is missing AND data exists.

Routers
-------
  /api/metrics, /api/categories, /api/regions  → data_router
  /api/forecast                                 → forecast_router
  /api/summarize, /api/ask                      → insights_router

CORS
----
  allow_origins=["*"] — intentionally permissive for development.
  Replace with a whitelist of allowed origins for production deployments.
"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

import duckdb
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routers.data import router as data_router
from src.api.routers.forecast import router as forecast_router
from src.api.routers.insights import router as insights_router
from src.api.schemas import HealthResponse
from src.config import settings

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("api.main")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_schema(conn: duckdb.DuckDBPyConnection) -> None:
    """Create tables if they do not yet exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            sku_id       VARCHAR PRIMARY KEY,
            product_name VARCHAR,
            category     VARCHAR,
            brand        VARCHAR,
            package_size VARCHAR,
            list_price   FLOAT,
            launch_date  DATE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS stores (
            store_id   VARCHAR PRIMARY KEY,
            store_name VARCHAR,
            region     VARCHAR,
            state      VARCHAR,
            city       VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id VARCHAR PRIMARY KEY,
            txn_date       DATE,
            store_id       VARCHAR,
            sku_id         VARCHAR,
            quantity       INTEGER,
            unit_price     FLOAT,
            revenue        FLOAT,
            source         VARCHAR,
            ingested_at    TIMESTAMP
        )
    """)
    logger.info("Schema verified / created.")


def _transactions_empty(conn: duckdb.DuckDBPyConnection) -> bool:
    """Return True if the transactions table has zero rows."""
    row = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()
    return (row[0] if row else 0) == 0


def _db_connected(database_path: str) -> bool:
    """Try to open the DB and run a trivial query; return success flag."""
    try:
        conn = duckdb.connect(database_path)
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: run startup tasks, then yield."""
    logger.info("Starting CPG Analytics API …")

    # Ensure data and model directories exist
    Path(settings.data_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.model_path).parent.mkdir(parents=True, exist_ok=True)

    # ----------------------------------------------------------------
    # Open a short-lived connection for startup tasks
    # ----------------------------------------------------------------
    try:
        conn = duckdb.connect(settings.database_path)
        _ensure_schema(conn)

        # ----------------------------------------------------------------
        # Auto-ingest if tables are empty
        # ----------------------------------------------------------------
        if _transactions_empty(conn):
            logger.info(
                "transactions table is empty — attempting ingestion pipeline …"
            )
            try:
                # Try the ingestion module's run_pipeline function first
                from src.ingestion.db import run_pipeline  # type: ignore[import]
                conn.close()  # release before pipeline opens its own connection
                run_pipeline(settings.data_dir, settings.database_path)
                conn = duckdb.connect(settings.database_path)
                logger.info("Ingestion pipeline completed.")
            except ImportError:
                try:
                    from src.ingestion import pipeline as ingestion_pipeline  # type: ignore[import]
                    ingestion_pipeline.run()
                    logger.info("Ingestion pipeline (legacy) completed.")
                except ImportError:
                    logger.warning(
                        "No ingestion pipeline found — skipping auto-ingest."
                    )
            except Exception as exc:
                logger.error("Ingestion pipeline failed: %s", exc)
                # Ensure conn is reopened if it was closed above
                try:
                    conn = duckdb.connect(settings.database_path)
                except Exception:
                    pass

        # ----------------------------------------------------------------
        # Auto-train if model file is missing AND data exists
        # ----------------------------------------------------------------
        model_path = Path(settings.model_path)
        if not model_path.exists() and not _transactions_empty(conn):
            logger.info(
                "Model file not found — training model …"
            )
            try:
                from src.forecasting.model import train  # noqa: PLC0415
                metrics = train(conn, settings.model_path)
                logger.info("Auto-train complete: %s", metrics)
            except Exception as exc:
                logger.error("Auto-train failed: %s", exc)
        elif model_path.exists():
            logger.info("Model file found at %s — skipping auto-train.", model_path)
        else:
            logger.warning(
                "transactions table is empty — skipping auto-train. "
                "Run ingestion first, then: python -m src.forecasting.model"
            )

        conn.close()
    except Exception as exc:
        logger.error("Startup DB tasks failed: %s", exc)

    logger.info("CPG Analytics API is ready.")
    yield
    logger.info("CPG Analytics API is shutting down.")


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    app = FastAPI(
        title="CPG Sales Analytics API",
        description=(
            "REST API for CPG sales analytics: metrics, ML-based revenue "
            "forecasting, and LLM-powered insights."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS — permissive for development; restrict origins in production.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------
    app.include_router(data_router, prefix="/api", tags=["data"])
    app.include_router(forecast_router, prefix="/api", tags=["forecast"])
    app.include_router(insights_router, prefix="/api", tags=["insights"])

    # ------------------------------------------------------------------
    # Health endpoint
    # ------------------------------------------------------------------
    @app.get("/health", response_model=HealthResponse, tags=["health"])
    def health() -> HealthResponse:
        """Liveness / readiness probe."""
        connected = _db_connected(settings.database_path)
        return HealthResponse(status="ok", db_connected=connected)

    return app


# ---------------------------------------------------------------------------
# Module-level app instance (used by uvicorn / pytest)
# ---------------------------------------------------------------------------
app = create_app()
