"""
Forecast API router.

Endpoints
---------
POST /api/forecast → ForecastResponse
"""
from __future__ import annotations

import functools
import logging
from datetime import date
from typing import Generator

import duckdb
from fastapi import APIRouter, Depends, HTTPException

from src.api.schemas import ForecastRequest, ForecastResponse, PredictionPoint
from src.config import settings
from src.db import get_connection
from src.forecasting import predictor as _predictor

logger = logging.getLogger("api.routers.forecast")

router = APIRouter()


# ---------------------------------------------------------------------------
# Dependency: DB connection per request
# ---------------------------------------------------------------------------

def get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
    """Yield a DuckDB connection and close it when the request is done."""
    conn = get_connection(settings.database_path)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Cached model loader
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _load_model_cached(model_path: str) -> dict:
    """
    Load and cache the joblib model bundle.

    Using lru_cache with the path as key means the model is loaded once per
    process lifetime (or until the cache is invalidated).

    Raises
    ------
    FileNotFoundError
        Propagated from joblib if the file does not exist.
    """
    return _predictor.load_model(model_path)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/forecast", response_model=ForecastResponse)
def post_forecast(
    body: ForecastRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_db),
) -> ForecastResponse:
    """
    Generate a revenue forecast for the given category, region, and horizon.
    """
    # -- Load model bundle (cached) --
    try:
        bundle = _load_model_cached(settings.model_path)
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Model not trained. Run: python -m src.forecasting.model",
        )

    # -- Get last known date from DB --
    row = conn.execute("SELECT MAX(txn_date) FROM transactions").fetchone()
    last_known_date: date | None = row[0] if row else None

    if last_known_date is None:
        raise HTTPException(
            status_code=503,
            detail="No transaction data found in the database.",
        )

    # DuckDB may return the date as a Python date or a string
    if not isinstance(last_known_date, date):
        from datetime import datetime
        last_known_date = datetime.strptime(str(last_known_date)[:10], "%Y-%m-%d").date()

    # -- Run predictions --
    try:
        raw_predictions = _predictor.predict(
            model_bundle=bundle,
            category=body.category,
            region=body.region,
            months_ahead=body.months_ahead,
            last_known_date=last_known_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    predictions = [
        PredictionPoint(
            period=p["period"],
            predicted_revenue=p["predicted_revenue"],
        )
        for p in raw_predictions
    ]

    logger.info(
        "post_forecast: category=%s, region=%s, months_ahead=%d → %d predictions",
        body.category,
        body.region,
        body.months_ahead,
        len(predictions),
    )

    return ForecastResponse(
        category=body.category,
        region=body.region,
        predictions=predictions,
    )
