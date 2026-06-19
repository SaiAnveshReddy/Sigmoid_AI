"""
Data summarization and Q&A using DuckDB queries + LLM narrative.

Functions
---------
get_data_context(conn, category, region) -> dict
summarize(conn, category, region) -> str
answer_question(conn, question) -> str
"""
from __future__ import annotations

import logging
from typing import Any

from src.insights.llm_client import chat_completion

logger = logging.getLogger("insights.summarizer")

_SYSTEM_PROMPT = "You are a helpful data analyst."


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _safe_float(value: Any, default: float = 0.0) -> float:
    """Return float(value) or default if value is None / not castable."""
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Return int(value) or default if value is None / not castable."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_str(value: Any, default: str = "N/A") -> str:
    """Return str(value) or default if value is None."""
    if value is None:
        return default
    return str(value)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_data_context(
    conn,
    category: str | None,
    region: str | None,
) -> dict:
    """
    Query DuckDB for aggregate statistics, optionally filtered by category
    and/or region.

    Returns
    -------
    dict with keys:
        total_revenue, total_transactions, avg_order_value,
        top_sku, date_range (str "YYYY-MM-DD to YYYY-MM-DD"),
        period_months (int)
    All numeric values default to 0 (never None).
    """
    # ------------------------------------------------------------------
    # Build WHERE clause fragments
    # ------------------------------------------------------------------
    filters: list[str] = []
    if category:
        safe_cat = category.replace("'", "''")
        filters.append(f"p.category = '{safe_cat}'")
    if region:
        safe_reg = region.replace("'", "''")
        filters.append(f"s.region = '{safe_reg}'")

    where_clause = ("WHERE " + " AND ".join(filters)) if filters else ""

    # ------------------------------------------------------------------
    # Aggregate metrics query
    # ------------------------------------------------------------------
    agg_sql = f"""
        SELECT
            COALESCE(SUM(t.revenue), 0)           AS total_revenue,
            COALESCE(COUNT(t.transaction_id), 0)  AS total_transactions,
            COALESCE(AVG(t.revenue), 0)           AS avg_order_value,
            MIN(t.txn_date)                        AS min_date,
            MAX(t.txn_date)                        AS max_date
        FROM transactions t
        JOIN products p ON t.sku_id   = p.sku_id
        JOIN stores   s ON t.store_id = s.store_id
        {where_clause}
    """
    row = conn.execute(agg_sql).fetchone()

    total_revenue = _safe_float(row[0]) if row else 0.0
    total_transactions = _safe_int(row[1]) if row else 0
    avg_order_value = _safe_float(row[2]) if row else 0.0
    min_date = row[3] if row else None
    max_date = row[4] if row else None

    # Period in months
    period_months = 0
    if min_date and max_date:
        try:
            # date objects from DuckDB can be Python date or string
            from datetime import date as _date
            if hasattr(min_date, "year"):
                period_months = (
                    (max_date.year - min_date.year) * 12
                    + (max_date.month - min_date.month)
                    + 1
                )
            else:
                # Parse strings
                from datetime import datetime
                min_dt = datetime.strptime(str(min_date)[:10], "%Y-%m-%d")
                max_dt = datetime.strptime(str(max_date)[:10], "%Y-%m-%d")
                period_months = (
                    (max_dt.year - min_dt.year) * 12
                    + (max_dt.month - min_dt.month)
                    + 1
                )
        except Exception:
            period_months = 0

    date_range = (
        f"{str(min_date)[:10]} to {str(max_date)[:10]}"
        if min_date and max_date
        else "N/A"
    )

    # ------------------------------------------------------------------
    # Top SKU by revenue
    # ------------------------------------------------------------------
    sku_sql = f"""
        SELECT
            p.product_name,
            COALESCE(SUM(t.revenue), 0) AS sku_revenue
        FROM transactions t
        JOIN products p ON t.sku_id   = p.sku_id
        JOIN stores   s ON t.store_id = s.store_id
        {where_clause}
        GROUP BY p.product_name
        ORDER BY sku_revenue DESC
        LIMIT 1
    """
    sku_row = conn.execute(sku_sql).fetchone()
    top_sku = _safe_str(sku_row[0]) if sku_row else "N/A"

    context = {
        "total_revenue": total_revenue,
        "total_transactions": total_transactions,
        "avg_order_value": avg_order_value,
        "top_sku": top_sku,
        "date_range": date_range,
        "period_months": period_months,
    }
    logger.debug("get_data_context result: %s", context)
    return context


def summarize(
    conn,
    category: str | None = None,
    region: str | None = None,
) -> str:
    """
    Produce a natural-language summary of CPG sales for the given filters.

    Calls :func:`get_data_context` to gather stats, then passes a formatted
    prompt to :func:`chat_completion`.

    Returns
    -------
    str — LLM-generated summary (or degradation message if no API key).
    """
    ctx = get_data_context(conn, category, region)

    prompt = (
        "Summarize this CPG sales data in 3-4 sentences for a business audience:\n"
        f"Category: {category or 'All'}, "
        f"Region: {region or 'All'},\n"
        f"Total Revenue: ${ctx['total_revenue']:,.2f}, "
        f"Transactions: {ctx['total_transactions']:,},\n"
        f"Avg Order: ${ctx['avg_order_value']:.2f}, "
        f"Top SKU: {ctx['top_sku']}, "
        f"Period: {ctx['period_months']} months"
    )

    logger.info(
        "summarize: category=%s, region=%s, total_revenue=%.2f",
        category,
        region,
        ctx["total_revenue"],
    )
    return chat_completion(prompt, system_prompt=_SYSTEM_PROMPT)


def answer_question(conn, question: str) -> str:
    """
    Answer an open-ended question about the CPG sales data using LLM + context.

    Pulls:
    - Total revenue
    - Top 3 categories by revenue
    - Top 3 regions by revenue
    - Recent 3-month revenue trend

    Returns
    -------
    str — LLM-generated answer (or degradation message if no API key).
    """
    # ------------------------------------------------------------------
    # Total revenue
    # ------------------------------------------------------------------
    total_rev_row = conn.execute(
        "SELECT COALESCE(SUM(revenue), 0) FROM transactions"
    ).fetchone()
    total_revenue = _safe_float(total_rev_row[0]) if total_rev_row else 0.0

    # ------------------------------------------------------------------
    # Top 3 categories by revenue
    # ------------------------------------------------------------------
    cat_rows = conn.execute(
        """
        SELECT p.category, COALESCE(SUM(t.revenue), 0) AS rev
        FROM transactions t
        JOIN products p ON t.sku_id = p.sku_id
        GROUP BY p.category
        ORDER BY rev DESC
        LIMIT 3
        """
    ).fetchall()
    top_categories = [
        f"{row[0]} (${_safe_float(row[1]):,.0f})" for row in cat_rows
    ]

    # ------------------------------------------------------------------
    # Top 3 regions by revenue
    # ------------------------------------------------------------------
    reg_rows = conn.execute(
        """
        SELECT s.region, COALESCE(SUM(t.revenue), 0) AS rev
        FROM transactions t
        JOIN stores s ON t.store_id = s.store_id
        GROUP BY s.region
        ORDER BY rev DESC
        LIMIT 3
        """
    ).fetchall()
    top_regions = [
        f"{row[0]} (${_safe_float(row[1]):,.0f})" for row in reg_rows
    ]

    # ------------------------------------------------------------------
    # Recent 3-month trend
    # ------------------------------------------------------------------
    trend_rows = conn.execute(
        """
        SELECT
            YEAR(txn_date)  AS yr,
            MONTH(txn_date) AS mo,
            COALESCE(SUM(revenue), 0) AS monthly_rev
        FROM transactions
        GROUP BY YEAR(txn_date), MONTH(txn_date)
        ORDER BY yr DESC, mo DESC
        LIMIT 3
        """
    ).fetchall()

    if len(trend_rows) >= 2:
        # trend_rows[0] is the most recent month
        newest_rev = _safe_float(trend_rows[0][2])
        oldest_rev = _safe_float(trend_rows[-1][2])
        if oldest_rev == 0:
            trend_description = "insufficient data to determine trend"
        elif newest_rev > oldest_rev:
            pct = ((newest_rev - oldest_rev) / oldest_rev) * 100
            trend_description = f"growing (up ~{pct:.1f}% over the last 3 months)"
        elif newest_rev < oldest_rev:
            pct = ((oldest_rev - newest_rev) / oldest_rev) * 100
            trend_description = f"declining (down ~{pct:.1f}% over the last 3 months)"
        else:
            trend_description = "stable over the last 3 months"
    else:
        trend_description = "insufficient data to determine trend"

    # ------------------------------------------------------------------
    # Compose prompt
    # ------------------------------------------------------------------
    prompt = (
        "You are a data analyst. Answer this question about CPG sales data:\n"
        f"Question: {question}\n"
        "Available data context:\n"
        f"- Total revenue: ${total_revenue:,.2f}\n"
        f"- Top categories: {', '.join(top_categories) or 'N/A'}\n"
        f"- Top regions: {', '.join(top_regions) or 'N/A'}\n"
        f"- Recent trend: {trend_description}\n"
        "Answer concisely in 2-3 sentences based on the data."
    )

    logger.info("answer_question: question=%r", question)
    return chat_completion(prompt, system_prompt=_SYSTEM_PROMPT)
