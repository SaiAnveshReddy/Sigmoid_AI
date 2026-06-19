"""
Insights API router.

Endpoints
---------
POST /api/summarize → SummarizeResponse
POST /api/ask       → AskResponse
"""
from __future__ import annotations

import logging
from typing import Generator

import duckdb
from fastapi import APIRouter, Depends

from src.api.schemas import AskRequest, AskResponse, SummarizeRequest, SummarizeResponse
from src.config import settings
from src.db import get_connection
from src.insights import summarizer

logger = logging.getLogger("api.routers.insights")

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

@router.post("/summarize", response_model=SummarizeResponse)
def post_summarize(
    body: SummarizeRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_db),
) -> SummarizeResponse:
    """Generate a natural-language summary of CPG sales data."""
    summary_text = summarizer.summarize(
        conn=conn,
        category=body.category,
        region=body.region,
    )
    logger.info(
        "post_summarize: category=%s, region=%s", body.category, body.region
    )
    return SummarizeResponse(summary=summary_text)


@router.post("/ask", response_model=AskResponse)
def post_ask(
    body: AskRequest,
    conn: duckdb.DuckDBPyConnection = Depends(get_db),
) -> AskResponse:
    """Answer a free-form question about CPG sales using LLM + data context."""
    answer_text = summarizer.answer_question(
        conn=conn,
        question=body.question,
    )
    logger.info("post_ask: question=%r", body.question)
    return AskResponse(answer=answer_text)
