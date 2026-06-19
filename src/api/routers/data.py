"""
Data API router.

Endpoints
---------
GET /api/metrics     → MetricsResponse
GET /api/categories  → list[str]
GET /api/regions     → list[str]
"""
from __future__ import annotations

import logging
from typing import Generator

import duckdb
from fastapi import APIRouter, Depends

from src.api.schemas import MetricsResponse
from src.config import settings
from src.db import get_connection

logger = logging.getLogger("api.routers.data")

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
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/metrics", response_model=MetricsResponse)
def get_metrics(conn: duckdb.DuckDBPyConnection = Depends(get_db)) -> MetricsResponse:
    """Return aggregate sales metrics."""

    # -- Total revenue, transaction count, AOV --
    agg_row = conn.execute(
        """
        SELECT
            COALESCE(SUM(revenue), 0)          AS total_revenue,
            COALESCE(COUNT(transaction_id), 0) AS total_transactions,
            COALESCE(AVG(revenue), 0)           AS avg_order_value
        FROM transactions
        """
    ).fetchone()
    total_revenue = float(agg_row[0]) if agg_row else 0.0
    total_transactions = int(agg_row[1]) if agg_row else 0
    avg_order_value = float(agg_row[2]) if agg_row else 0.0

    # -- Top 5 categories by revenue --
    cat_rows = conn.execute(
        """
        SELECT p.category, COALESCE(SUM(t.revenue), 0) AS revenue
        FROM transactions t
        JOIN products p ON t.sku_id = p.sku_id
        GROUP BY p.category
        ORDER BY revenue DESC
        LIMIT 5
        """
    ).fetchall()
    top_categories = [
        {"category": row[0], "revenue": float(row[1])} for row in cat_rows
    ]

    # -- Top 5 regions by revenue --
    reg_rows = conn.execute(
        """
        SELECT s.region, COALESCE(SUM(t.revenue), 0) AS revenue
        FROM transactions t
        JOIN stores s ON t.store_id = s.store_id
        GROUP BY s.region
        ORDER BY revenue DESC
        LIMIT 5
        """
    ).fetchall()
    top_regions = [
        {"region": row[0], "revenue": float(row[1])} for row in reg_rows
    ]

    # -- Revenue by month --
    month_rows = conn.execute(
        """
        SELECT
            PRINTF('%04d-%02d', YEAR(txn_date), MONTH(txn_date)) AS period,
            COALESCE(SUM(revenue), 0) AS revenue
        FROM transactions
        GROUP BY period
        ORDER BY period ASC
        """
    ).fetchall()
    revenue_by_month = [
        {"period": row[0], "revenue": float(row[1])} for row in month_rows
    ]

    logger.info(
        "get_metrics: total_revenue=%.2f, total_transactions=%d",
        total_revenue,
        total_transactions,
    )

    return MetricsResponse(
        total_revenue=total_revenue,
        total_transactions=total_transactions,
        avg_order_value=avg_order_value,
        top_categories=top_categories,
        top_regions=top_regions,
        revenue_by_month=revenue_by_month,
    )


@router.get("/categories", response_model=list[str])
def get_categories(conn: duckdb.DuckDBPyConnection = Depends(get_db)) -> list[str]:
    """Return all distinct product categories, sorted alphabetically."""
    rows = conn.execute(
        "SELECT DISTINCT category FROM products ORDER BY category"
    ).fetchall()
    return [row[0] for row in rows]


@router.get("/regions", response_model=list[str])
def get_regions(conn: duckdb.DuckDBPyConnection = Depends(get_db)) -> list[str]:
    """Return all distinct store regions, sorted alphabetically."""
    rows = conn.execute(
        "SELECT DISTINCT region FROM stores ORDER BY region"
    ).fetchall()
    return [row[0] for row in rows]
