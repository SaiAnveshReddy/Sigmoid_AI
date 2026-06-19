"""
Pydantic v2 schemas for all API request and response models.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    db_connected: bool


# ---------------------------------------------------------------------------
# Forecasting
# ---------------------------------------------------------------------------

class ForecastRequest(BaseModel):
    category: str
    region: str
    months_ahead: int = Field(default=3, ge=1, le=12)


class PredictionPoint(BaseModel):
    period: str  # "2024-01"
    predicted_revenue: float


class ForecastResponse(BaseModel):
    category: str
    region: str
    predictions: list[PredictionPoint]


# ---------------------------------------------------------------------------
# LLM Insights
# ---------------------------------------------------------------------------

class AskRequest(BaseModel):
    question: str = Field(min_length=3)


class AskResponse(BaseModel):
    answer: str


class SummarizeRequest(BaseModel):
    category: str | None = None
    region: str | None = None


class SummarizeResponse(BaseModel):
    summary: str


# ---------------------------------------------------------------------------
# Data / Metrics
# ---------------------------------------------------------------------------

class MetricsResponse(BaseModel):
    total_revenue: float
    total_transactions: int
    avg_order_value: float
    top_categories: list[dict]
    top_regions: list[dict]
    revenue_by_month: list[dict]
