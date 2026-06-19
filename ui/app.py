"""
CPG Sales Analytics Dashboard — Streamlit UI
Connects to FastAPI backend at API_BASE_URL (default: http://localhost:8000)
"""

import os

import pandas as pd
import requests
import streamlit as st

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
DATABASE_PATH = os.getenv("DATABASE_PATH", "data/cpg_sales.duckdb")
MODEL_PATH = os.getenv("MODEL_PATH", "models/revenue_forecast.joblib")
DATA_DIR = os.getenv("DATA_DIR", "data/raw")

st.set_page_config(page_title="CPG Analytics", page_icon="📊", layout="wide")

# ---------------------------------------------------------------------------
# Helper — generic GET / POST wrappers with unified error handling
# ---------------------------------------------------------------------------

def api_get(path: str) -> dict | None:
    """GET from API, return parsed JSON or None on error."""
    try:
        resp = requests.get(f"{API_BASE_URL}{path}", timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        st.error("Could not connect to API. Is the backend running?")
        return None


def api_post(path: str, payload: dict) -> dict | None:
    """POST to API, return parsed JSON or None on error."""
    try:
        resp = requests.post(f"{API_BASE_URL}{path}", json=payload, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        st.error("Could not connect to API. Is the backend running?")
        return None


# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.title("CPG Analytics")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate to",
    ["Overview", "Revenue Forecast", "AI Insights", "Data Explorer"],
    index=0,
)
st.sidebar.markdown("---")
st.sidebar.caption(f"API: `{API_BASE_URL}`")

# ===========================================================================
# PAGE 1 — OVERVIEW
# ===========================================================================

if page == "Overview":
    st.title("CPG Sales Dashboard")

    metrics = api_get("/api/metrics")

    if metrics:
        # ---- KPI cards ----
        col1, col2, col3 = st.columns(3)
        col1.metric("Total Revenue ($)", f"${metrics.get('total_revenue', 0):,.2f}")
        col2.metric("Total Transactions", f"{metrics.get('total_transactions', 0):,}")
        col3.metric("Avg Order Value ($)", f"${metrics.get('avg_order_value', 0):,.2f}")

        st.markdown("---")

        # ---- Bar charts ----
        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:
            st.subheader("Revenue by Category")
            top_categories = metrics.get("top_categories", [])
            if top_categories:
                df_cat = pd.DataFrame(top_categories).rename(
                    columns={"category": "Category", "revenue": "Revenue ($)"}
                )
                df_cat = df_cat.set_index("Category")
                st.bar_chart(df_cat, horizontal=True)
            else:
                st.info("No category data available.")

        with chart_col2:
            st.subheader("Revenue by Region")
            top_regions = metrics.get("top_regions", [])
            if top_regions:
                df_reg = pd.DataFrame(top_regions).rename(
                    columns={"region": "Region", "revenue": "Revenue ($)"}
                )
                df_reg = df_reg.set_index("Region")
                st.bar_chart(df_reg, horizontal=True)
            else:
                st.info("No region data available.")

        st.markdown("---")

        # ---- Line chart ----
        st.subheader("Monthly Revenue Trend")
        revenue_by_month = metrics.get("revenue_by_month", [])
        if revenue_by_month:
            df_monthly = pd.DataFrame(revenue_by_month).rename(
                columns={"period": "Period", "revenue": "Revenue ($)"}
            )
            df_monthly = df_monthly.set_index("Period")
            st.line_chart(df_monthly)
        else:
            st.info("No monthly data available.")

# ===========================================================================
# PAGE 2 — REVENUE FORECAST
# ===========================================================================

elif page == "Revenue Forecast":
    st.title("Revenue Forecast")

    # ---- Load dropdowns ----
    categories = api_get("/api/categories") or []
    regions = api_get("/api/regions") or []

    col_a, col_b, col_c = st.columns(3)
    with col_a:
        selected_category = st.selectbox(
            "Category",
            options=categories if categories else ["(No categories loaded)"],
        )
    with col_b:
        selected_region = st.selectbox(
            "Region",
            options=regions if regions else ["(No regions loaded)"],
        )
    with col_c:
        months_ahead = st.slider("Months to Forecast", min_value=1, max_value=12, value=3)

    st.markdown("")
    generate_btn = st.button("Generate Forecast", type="primary")

    if generate_btn:
        if not categories or not regions:
            st.warning("Could not load categories or regions from the API.")
        else:
            with st.spinner("Generating forecast…"):
                result = api_post(
                    "/api/forecast",
                    {
                        "category": selected_category,
                        "region": selected_region,
                        "months_ahead": months_ahead,
                    },
                )

            if result:
                predictions = result.get("predictions", [])
                if predictions:
                    df_pred = pd.DataFrame(predictions).rename(
                        columns={
                            "period": "Period",
                            "predicted_revenue": "Predicted Revenue ($)",
                        }
                    )

                    st.subheader(
                        f"Forecast — {result.get('category', selected_category)} / "
                        f"{result.get('region', selected_region)}"
                    )

                    # Line chart
                    df_chart = df_pred.set_index("Period")
                    st.line_chart(df_chart)

                    # Raw table
                    st.subheader("Prediction Details")
                    df_pred_display = df_pred.copy()
                    df_pred_display["Predicted Revenue ($)"] = df_pred_display[
                        "Predicted Revenue ($)"
                    ].map(lambda x: f"${x:,.2f}")
                    st.dataframe(df_pred_display, use_container_width=True)

                    st.caption(
                        "Model: Linear Regression trained on 2022–2024 historical data"
                    )
                else:
                    st.warning("No predictions returned from the API.")

# ===========================================================================
# PAGE 3 — AI INSIGHTS
# ===========================================================================

elif page == "AI Insights":
    st.title("AI-Powered Insights")

    tab_summarize, tab_ask = st.tabs(["Summarize Data", "Ask a Question"])

    # ---- Tab 1: Summarize ----
    with tab_summarize:
        st.markdown("Generate an AI summary of your sales data, optionally filtered.")

        categories_raw = api_get("/api/categories") or []
        regions_raw = api_get("/api/regions") or []

        col1, col2 = st.columns(2)
        with col1:
            sum_category = st.selectbox(
                "Category (optional)",
                options=["All"] + categories_raw,
                key="sum_category",
            )
        with col2:
            sum_region = st.selectbox(
                "Region (optional)",
                options=["All"] + regions_raw,
                key="sum_region",
            )

        summarize_btn = st.button("Generate Summary", type="primary", key="btn_summarize")

        if summarize_btn:
            payload: dict = {}
            if sum_category != "All":
                payload["category"] = sum_category
            if sum_region != "All":
                payload["region"] = sum_region

            with st.spinner("Generating summary…"):
                result = api_post("/api/summarize", payload)

            if result:
                summary = result.get("summary", "No summary returned.")
                st.info(summary)

    # ---- Tab 2: Ask a Question ----
    with tab_ask:
        st.markdown("Ask any natural-language question about your CPG sales data.")

        question = st.text_input(
            "Ask a question about your sales data…",
            placeholder="Type your question here",
            key="ask_question",
        )
        st.caption(
            "e.g. Which region is performing best? What is the revenue trend?"
        )

        ask_btn = st.button("Get Answer", type="primary", key="btn_ask")

        if ask_btn:
            if not question.strip():
                st.warning("Please enter a question before clicking Get Answer.")
            else:
                with st.spinner("Thinking…"):
                    result = api_post("/api/ask", {"question": question})

                if result:
                    answer = result.get("answer", "No answer returned.")
                    st.success(answer)

# ===========================================================================
# PAGE 4 — DATA EXPLORER
# ===========================================================================

elif page == "Data Explorer":
    st.title("Data Explorer")

    # ---- Monthly revenue dataframe ----
    st.subheader("Monthly Revenue Data")
    metrics = api_get("/api/metrics")

    if metrics:
        revenue_by_month = metrics.get("revenue_by_month", [])
        if revenue_by_month:
            df_monthly = pd.DataFrame(revenue_by_month).rename(
                columns={"period": "Period", "revenue": "Revenue ($)"}
            )
            st.dataframe(df_monthly, use_container_width=True)
        else:
            st.info("No monthly revenue data available.")
    else:
        st.info("Could not load metrics data.")

    st.markdown("---")

    # ---- Environment info ----
    st.subheader("Environment Configuration")
    info_col1, info_col2, info_col3 = st.columns(3)
    info_col1.info(f"**Database**\n\n`{DATABASE_PATH}`")
    info_col2.info(f"**Model**\n\n`{MODEL_PATH}`")
    info_col3.info(f"**Data Directory**\n\n`{DATA_DIR}`")

    st.markdown("---")

    # ---- System info expander ----
    with st.expander("System Info"):
        health = api_get("/health")
        if health:
            api_status = health.get("status", "unknown")
            db_connected = health.get("db_connected", False)

            status_col1, status_col2 = st.columns(2)
            with status_col1:
                if api_status == "ok":
                    st.success(f"API Status: {api_status}")
                else:
                    st.error(f"API Status: {api_status}")
            with status_col2:
                if db_connected:
                    st.success("Database: Connected")
                else:
                    st.error("Database: Not connected")
        else:
            st.warning("Could not retrieve system health information.")
