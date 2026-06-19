"""
FastAPI integration tests using httpx.AsyncClient (no real server).

All tests override the DB dependency to use a temporary in-memory DuckDB.
LLM calls are mocked to avoid real API requests.

Run with:
    pytest tests/test_api.py -v
"""
from __future__ import annotations

import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import AsyncIterator, Generator
from unittest.mock import MagicMock, patch

import duckdb
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_test_db(db_path: str) -> None:
    """
    Create schema and seed minimal data into a DuckDB at db_path.
    2 categories × 2 regions × 12 months of synthetic transactions.
    """
    conn = duckdb.connect(db_path)

    conn.execute("""
        CREATE TABLE products (
            sku_id VARCHAR PRIMARY KEY, product_name VARCHAR,
            category VARCHAR, brand VARCHAR, package_size VARCHAR,
            list_price FLOAT, launch_date DATE
        )
    """)
    conn.execute("""
        CREATE TABLE stores (
            store_id VARCHAR PRIMARY KEY, store_name VARCHAR,
            region VARCHAR, state VARCHAR, city VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE transactions (
            transaction_id VARCHAR PRIMARY KEY, txn_date DATE,
            store_id VARCHAR, sku_id VARCHAR, quantity INTEGER,
            unit_price FLOAT, revenue FLOAT, source VARCHAR,
            ingested_at TIMESTAMP
        )
    """)

    categories = [("SKU001", "Cola 1L", "Beverages"), ("SKU002", "Chips 200g", "Snacks")]
    regions = [("STR001", "Store North", "North"), ("STR002", "Store South", "South")]

    for sku_id, name, cat in categories:
        conn.execute(
            "INSERT INTO products VALUES (?, ?, ?, ?, ?, ?, ?)",
            [sku_id, name, cat, "BrandX", "1kg", 3.0, "2022-01-01"],
        )
    for store_id, name, reg in regions:
        conn.execute(
            "INSERT INTO stores VALUES (?, ?, ?, ?, ?)",
            [store_id, name, reg, "StateX", "CityX"],
        )

    import random
    rng = random.Random(1)
    txn_id = 0
    for month_offset in range(12):
        year = 2023
        month = month_offset + 1
        txn_date = f"{year}-{month:02d}-15"
        for sku_id, _, _ in categories:
            for store_id, _, _ in regions:
                revenue = 5000.0 + rng.uniform(-500, 500)
                txn_id += 1
                conn.execute(
                    "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, 'test', CURRENT_TIMESTAMP)",
                    [
                        f"TXN{txn_id:05d}",
                        txn_date,
                        store_id,
                        sku_id,
                        50,
                        round(revenue / 50, 2),
                        round(revenue, 2),
                    ],
                )

    conn.close()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def test_db_path(tmp_path_factory):
    """
    Create a module-scoped temporary DuckDB file with seeded data.
    Also trains a model so forecast tests can run.
    """
    tmp_path = tmp_path_factory.mktemp("api_test_db")
    db_path = str(tmp_path / "api_test.duckdb")
    _create_test_db(db_path)
    return db_path


@pytest.fixture(scope="module")
def trained_model_path(test_db_path, tmp_path_factory):
    """Train a model on the test DB and return the model path."""
    tmp_path = tmp_path_factory.mktemp("api_test_model")
    model_path = str(tmp_path / "model.joblib")

    conn = duckdb.connect(test_db_path)
    from src.forecasting.model import train
    train(conn, model_path)
    conn.close()
    return model_path


@pytest_asyncio.fixture()
async def async_client(test_db_path, trained_model_path) -> AsyncIterator[AsyncClient]:
    """
    AsyncClient pointed at the FastAPI app with:
    - DB dependency overridden to use test_db_path
    - model_path patched to trained_model_path
    - LLM calls mocked
    - Lifespan disabled (we control setup manually)
    """
    from src.api.main import app
    from src.api.routers.data import get_db as data_get_db
    from src.api.routers.forecast import get_db as forecast_get_db
    from src.api.routers.insights import get_db as insights_get_db

    def override_get_db() -> Generator[duckdb.DuckDBPyConnection, None, None]:
        conn = duckdb.connect(test_db_path)
        try:
            yield conn
        finally:
            conn.close()

    app.dependency_overrides[data_get_db] = override_get_db
    app.dependency_overrides[forecast_get_db] = override_get_db
    app.dependency_overrides[insights_get_db] = override_get_db

    # Patch settings.model_path for the forecast router's lru_cache loader.
    # We must also clear the lru_cache so it picks up the new path.
    from src.api.routers import forecast as forecast_router_mod
    forecast_router_mod._load_model_cached.cache_clear()

    with patch("src.api.routers.forecast.settings") as mock_settings:
        mock_settings.model_path = trained_model_path
        mock_settings.database_path = test_db_path

        # Also patch the health check settings
        with patch("src.api.main.settings") as mock_main_settings:
            mock_main_settings.database_path = test_db_path
            mock_main_settings.model_path = trained_model_path
            mock_main_settings.log_level = "INFO"

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                yield client

    # Cleanup
    app.dependency_overrides.clear()
    forecast_router_mod._load_model_cached.cache_clear()


# ---------------------------------------------------------------------------
# Health endpoint
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_health_endpoint_returns_ok(test_db_path):
    """GET /health should return status='ok' and db_connected=True."""
    from src.api.main import app
    with patch("src.api.main.settings") as mock_settings:
        mock_settings.database_path = test_db_path
        mock_settings.model_path = "models/nonexistent.joblib"
        mock_settings.log_level = "INFO"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "db_connected" in data


# ---------------------------------------------------------------------------
# Data endpoints
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_metrics_endpoint_returns_expected_shape(async_client):
    """GET /api/metrics must return all required fields."""
    response = await async_client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_revenue" in data
    assert "total_transactions" in data
    assert "avg_order_value" in data
    assert "top_categories" in data
    assert "top_regions" in data
    assert "revenue_by_month" in data
    assert isinstance(data["top_categories"], list)
    assert isinstance(data["top_regions"], list)
    assert isinstance(data["revenue_by_month"], list)


@pytest.mark.anyio
async def test_metrics_total_transactions_is_positive(async_client):
    response = await async_client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["total_transactions"] > 0


@pytest.mark.anyio
async def test_categories_endpoint_returns_list(async_client):
    """GET /api/categories must return a non-empty list of strings."""
    response = await async_client.get("/api/categories")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(c, str) for c in data)


@pytest.mark.anyio
async def test_categories_are_sorted(async_client):
    response = await async_client.get("/api/categories")
    data = response.json()
    assert data == sorted(data)


@pytest.mark.anyio
async def test_regions_endpoint_returns_list(async_client):
    """GET /api/regions must return a non-empty list of strings."""
    response = await async_client.get("/api/regions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(r, str) for r in data)


@pytest.mark.anyio
async def test_regions_are_sorted(async_client):
    response = await async_client.get("/api/regions")
    data = response.json()
    assert data == sorted(data)


# ---------------------------------------------------------------------------
# Forecast endpoints
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_forecast_endpoint_returns_predictions(async_client):
    """POST /api/forecast with valid category/region should return 3 predictions."""
    payload = {"category": "Beverages", "region": "North", "months_ahead": 3}
    response = await async_client.post("/api/forecast", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["category"] == "Beverages"
    assert data["region"] == "North"
    assert "predictions" in data
    assert len(data["predictions"]) == 3


@pytest.mark.anyio
async def test_forecast_predictions_have_correct_keys(async_client):
    payload = {"category": "Beverages", "region": "North", "months_ahead": 2}
    response = await async_client.post("/api/forecast", json=payload)
    assert response.status_code == 200
    for pred in response.json()["predictions"]:
        assert "period" in pred
        assert "predicted_revenue" in pred


@pytest.mark.anyio
async def test_forecast_predictions_are_non_negative(async_client):
    payload = {"category": "Snacks", "region": "South", "months_ahead": 6}
    response = await async_client.post("/api/forecast", json=payload)
    assert response.status_code == 200
    for pred in response.json()["predictions"]:
        assert pred["predicted_revenue"] >= 0.0


@pytest.mark.anyio
async def test_forecast_endpoint_returns_400_for_unknown_category(async_client):
    """POST /api/forecast with unknown category must return HTTP 400."""
    payload = {"category": "DoesNotExist", "region": "North", "months_ahead": 1}
    response = await async_client.post("/api/forecast", json=payload)
    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.anyio
async def test_forecast_endpoint_returns_400_for_unknown_region(async_client):
    payload = {"category": "Beverages", "region": "Mars", "months_ahead": 1}
    response = await async_client.post("/api/forecast", json=payload)
    assert response.status_code == 400


@pytest.mark.anyio
async def test_forecast_months_ahead_validation(async_client):
    """months_ahead must be between 1 and 12; 0 should be rejected."""
    payload = {"category": "Beverages", "region": "North", "months_ahead": 0}
    response = await async_client.post("/api/forecast", json=payload)
    assert response.status_code == 422  # FastAPI validation error


@pytest.mark.anyio
async def test_forecast_months_ahead_max_validation(async_client):
    """months_ahead > 12 should be rejected with 422."""
    payload = {"category": "Beverages", "region": "North", "months_ahead": 13}
    response = await async_client.post("/api/forecast", json=payload)
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Insights endpoints
# ---------------------------------------------------------------------------

@pytest.mark.anyio
async def test_summarize_endpoint_returns_summary(async_client):
    """POST /api/summarize with mocked LLM must return a summary string."""
    with patch("src.insights.summarizer.chat_completion", return_value="Mocked summary"):
        response = await async_client.post("/api/summarize", json={})
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert isinstance(data["summary"], str)
    assert len(data["summary"]) > 0


@pytest.mark.anyio
async def test_summarize_with_category_filter(async_client):
    with patch("src.insights.summarizer.chat_completion", return_value="Beverages summary"):
        response = await async_client.post(
            "/api/summarize", json={"category": "Beverages"}
        )
    assert response.status_code == 200
    assert response.json()["summary"] == "Beverages summary"


@pytest.mark.anyio
async def test_ask_endpoint_returns_answer(async_client):
    """POST /api/ask with mocked LLM must return an answer string."""
    with patch("src.insights.summarizer.chat_completion", return_value="Mocked answer"):
        response = await async_client.post(
            "/api/ask", json={"question": "What is the top selling category?"}
        )
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert isinstance(data["answer"], str)
    assert len(data["answer"]) > 0


@pytest.mark.anyio
async def test_ask_endpoint_question_min_length_validation(async_client):
    """question must be at least 3 characters; shorter should return 422."""
    response = await async_client.post("/api/ask", json={"question": "Hi"})
    assert response.status_code == 422


@pytest.mark.anyio
async def test_ask_endpoint_missing_question_returns_422(async_client):
    """Omitting the question field must return 422."""
    response = await async_client.post("/api/ask", json={})
    assert response.status_code == 422
