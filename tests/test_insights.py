"""
Tests for src.insights: LLM client and summarizer.

All Groq API calls are mocked — no real HTTP requests are made.
"""
from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

import duckdb
import pytest


# ---------------------------------------------------------------------------
# Shared DB fixture (local to this module — not using conftest)
# ---------------------------------------------------------------------------

@pytest.fixture()
def seeded_conn(tmp_path):
    """
    In-memory DuckDB with minimal CPG data for testing insights queries.
    """
    db_path = str(tmp_path / "insights_test.duckdb")
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

    # Products
    conn.execute("INSERT INTO products VALUES ('SKU001', 'Cola 1L', 'Beverages', 'BrandA', '1L', 2.5, '2022-01-01')")
    conn.execute("INSERT INTO products VALUES ('SKU002', 'Chips 200g', 'Snacks', 'BrandB', '200g', 1.5, '2022-01-01')")

    # Stores
    conn.execute("INSERT INTO stores VALUES ('STR001', 'Store North', 'North', 'StateN', 'CityN')")
    conn.execute("INSERT INTO stores VALUES ('STR002', 'Store South', 'South', 'StateS', 'CityS')")

    # Transactions
    txns = [
        ("T001", "2023-01-15", "STR001", "SKU001", 100, 2.5,  250.0),
        ("T002", "2023-02-15", "STR001", "SKU001", 120, 2.5,  300.0),
        ("T003", "2023-03-15", "STR002", "SKU002",  80, 1.5,  120.0),
        ("T004", "2023-04-15", "STR002", "SKU002",  90, 1.5,  135.0),
        ("T005", "2023-05-15", "STR001", "SKU002",  70, 1.5,  105.0),
        ("T006", "2023-06-15", "STR002", "SKU001",  60, 2.5,  150.0),
    ]
    for row in txns:
        conn.execute(
            "INSERT INTO transactions VALUES (?, ?, ?, ?, ?, ?, ?, 'test', CURRENT_TIMESTAMP)",
            list(row),
        )

    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Tests for src.insights.summarizer.get_data_context
# ---------------------------------------------------------------------------

class TestGetDataContext:
    def test_returns_dict(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        assert isinstance(result, dict)

    def test_has_total_revenue_key(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        assert "total_revenue" in result

    def test_has_total_transactions_key(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        assert "total_transactions" in result

    def test_has_avg_order_value_key(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        assert "avg_order_value" in result

    def test_has_top_sku_key(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        assert "top_sku" in result

    def test_has_date_range_key(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        assert "date_range" in result

    def test_has_period_months_key(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        assert "period_months" in result

    def test_total_revenue_is_numeric(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        assert isinstance(result["total_revenue"], (int, float))

    def test_no_none_values(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        result = get_data_context(seeded_conn, None, None)
        for k, v in result.items():
            assert v is not None, f"Key '{k}' should never be None"

    def test_category_filter_reduces_revenue(self, seeded_conn):
        from src.insights.summarizer import get_data_context
        all_ctx = get_data_context(seeded_conn, None, None)
        bev_ctx = get_data_context(seeded_conn, "Beverages", None)
        assert bev_ctx["total_revenue"] <= all_ctx["total_revenue"]

    def test_empty_table_returns_zeros(self, tmp_path):
        """get_data_context must never return None even on empty tables."""
        conn = duckdb.connect(str(tmp_path / "empty.duckdb"))
        conn.execute("CREATE TABLE products (sku_id VARCHAR PRIMARY KEY, product_name VARCHAR, category VARCHAR, brand VARCHAR, package_size VARCHAR, list_price FLOAT, launch_date DATE)")
        conn.execute("CREATE TABLE stores (store_id VARCHAR PRIMARY KEY, store_name VARCHAR, region VARCHAR, state VARCHAR, city VARCHAR)")
        conn.execute("CREATE TABLE transactions (transaction_id VARCHAR PRIMARY KEY, txn_date DATE, store_id VARCHAR, sku_id VARCHAR, quantity INTEGER, unit_price FLOAT, revenue FLOAT, source VARCHAR, ingested_at TIMESTAMP)")
        from src.insights.summarizer import get_data_context
        result = get_data_context(conn, None, None)
        assert result["total_revenue"] == 0
        assert result["total_transactions"] == 0
        conn.close()


# ---------------------------------------------------------------------------
# Tests for src.insights.summarizer.summarize
# ---------------------------------------------------------------------------

class TestSummarize:
    def test_returns_string(self, seeded_conn):
        with patch("src.insights.summarizer.chat_completion", return_value="Test summary"):
            from src.insights.summarizer import summarize
            result = summarize(seeded_conn, None, None)
            assert isinstance(result, str)

    def test_returns_llm_response(self, seeded_conn):
        expected = "Test summary text"
        with patch("src.insights.summarizer.chat_completion", return_value=expected):
            from src.insights.summarizer import summarize
            result = summarize(seeded_conn, None, None)
            assert result == expected

    def test_accepts_category_filter(self, seeded_conn):
        with patch("src.insights.summarizer.chat_completion", return_value="Filtered summary"):
            from src.insights.summarizer import summarize
            result = summarize(seeded_conn, category="Beverages", region=None)
            assert isinstance(result, str)

    def test_accepts_region_filter(self, seeded_conn):
        with patch("src.insights.summarizer.chat_completion", return_value="Region summary"):
            from src.insights.summarizer import summarize
            result = summarize(seeded_conn, category=None, region="North")
            assert isinstance(result, str)

    def test_calls_chat_completion_once(self, seeded_conn):
        with patch("src.insights.summarizer.chat_completion", return_value="ok") as mock_cc:
            from src.insights.summarizer import summarize
            summarize(seeded_conn, None, None)
            assert mock_cc.call_count == 1


# ---------------------------------------------------------------------------
# Tests for src.insights.summarizer.answer_question
# ---------------------------------------------------------------------------

class TestAnswerQuestion:
    def test_returns_string(self, seeded_conn):
        with patch("src.insights.summarizer.chat_completion", return_value="Answer here"):
            from src.insights.summarizer import answer_question
            result = answer_question(seeded_conn, "What is the top category?")
            assert isinstance(result, str)

    def test_returns_llm_response(self, seeded_conn):
        expected = "The top category is Beverages."
        with patch("src.insights.summarizer.chat_completion", return_value=expected):
            from src.insights.summarizer import answer_question
            result = answer_question(seeded_conn, "What is the top category?")
            assert result == expected

    def test_calls_chat_completion_once(self, seeded_conn):
        with patch("src.insights.summarizer.chat_completion", return_value="ok") as mock_cc:
            from src.insights.summarizer import answer_question
            answer_question(seeded_conn, "Which region leads in sales?")
            assert mock_cc.call_count == 1


# ---------------------------------------------------------------------------
# Tests for src.insights.llm_client
# ---------------------------------------------------------------------------

class TestLLMClient:
    def test_returns_degraded_message_when_no_key(self):
        """
        When groq_api_key is empty, chat_completion must return the degradation
        message WITHOUT contacting the Groq API.
        """
        import src.insights.llm_client as llm_mod

        with patch.object(llm_mod, "settings") as mock_settings:
            mock_settings.groq_api_key = ""
            result = llm_mod.chat_completion("test prompt")
            assert "GROQ_API_KEY" in result or "unavailable" in result.lower()

    def test_no_groq_call_when_key_missing(self):
        """
        Groq client must never be instantiated when the API key is empty.
        """
        import src.insights.llm_client as llm_mod

        mock_groq_module = MagicMock()

        with (
            patch.object(llm_mod, "settings") as mock_settings,
            patch.dict("sys.modules", {"groq": mock_groq_module}),
        ):
            mock_settings.groq_api_key = ""
            llm_mod.chat_completion("test prompt")
            mock_groq_module.Groq.assert_not_called()

    def test_returns_graceful_error_on_api_error(self):
        """
        When groq.APIError is raised, chat_completion must catch it and
        return a graceful error string instead of propagating the exception.
        """
        import src.insights.llm_client as llm_mod

        # Create a real-ish exception class that is the same object as what
        # the module will catch (groq.APIError).
        class MockAPIError(Exception):
            pass

        mock_groq_module = MagicMock()
        mock_groq_module.APIError = MockAPIError
        mock_client_instance = MagicMock()
        mock_groq_module.Groq.return_value = mock_client_instance
        mock_client_instance.chat.completions.create.side_effect = MockAPIError(
            "Rate limit exceeded"
        )

        # Patch both settings AND the groq module reference inside llm_client.
        with (
            patch.object(llm_mod, "settings") as mock_settings,
            patch.dict("sys.modules", {"groq": mock_groq_module}),
        ):
            mock_settings.groq_api_key = "fake-api-key"
            # Temporarily replace the groq name inside the already-imported module
            # by monkeypatching via sys.modules — the `import groq` inside
            # chat_completion will pick it up from sys.modules at call time.
            result = llm_mod.chat_completion("test prompt")
            assert "unavailable" in result.lower()

    def test_returns_model_response_on_success(self):
        """
        When the API succeeds, the model's content is returned.
        """
        import src.insights.llm_client as llm_mod

        expected_content = "Sales are growing in Q3."

        class MockAPIError(Exception):
            pass

        mock_choice = MagicMock()
        mock_choice.message.content = f"  {expected_content}  "  # strip should be called

        mock_groq_module = MagicMock()
        mock_groq_module.APIError = MockAPIError
        mock_client_instance = MagicMock()
        mock_groq_module.Groq.return_value = mock_client_instance
        mock_completion = MagicMock()
        mock_completion.choices = [mock_choice]
        mock_client_instance.chat.completions.create.return_value = mock_completion

        with (
            patch.object(llm_mod, "settings") as mock_settings,
            patch.dict("sys.modules", {"groq": mock_groq_module}),
        ):
            mock_settings.groq_api_key = "fake-api-key"
            result = llm_mod.chat_completion("test prompt")
            assert result == expected_content
