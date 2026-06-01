"""
frontend/streamlit_app.py — Interactive Streamlit dashboard for medication adherence analysis.

Features:
  - Chat interface for natural language queries via the FastAPI + Cortex Agent
  - Real-time chart and table rendering (Plotly)
  - Claude-powered insights and recommendations
  - Predefined analytics templates
  - Downloadable CSV reports
  - Schema browser

Usage (local):
    streamlit run frontend/streamlit_app.py

Usage (Streamlit in Snowflake): deploy app.py or point SiS at this file.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import httpx
import streamlit as st

from frontend.config import (
    API_BASE_URL,
    API_KEY,
    ANALYTICS_TEMPLATES,
    PAGE_ICON,
    PAGE_TITLE,
    REQUEST_TIMEOUT,
)
from frontend.components.chat import (
    render_chat_history,
    render_predefined_templates,
    render_question_input,
)
from frontend.components.charts import render_chart, render_download_buttons
from frontend.components.insights import render_insights_panel

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "last_response" not in st.session_state:
    st.session_state.last_response = None

# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------


def _api_headers() -> Dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if API_KEY:
        headers["X-API-Key"] = API_KEY
    return headers


def call_api(question: str, max_rows: int = 100) -> Optional[Dict[str, Any]]:
    """Call the FastAPI /ask endpoint and return the response dict."""
    payload = {
        "question": question,
        "max_rows": max_rows,
        "include_sql": True,
    }
    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                f"{API_BASE_URL}/ask",
                json=payload,
                headers=_api_headers(),
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        st.error(f"API error {exc.response.status_code}: {exc.response.text[:200]}")
        return None
    except Exception as exc:
        st.error(f"Connection error: {exc}")
        return None


def get_health() -> Dict[str, Any]:
    """Call GET /health and return the status dict."""
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{API_BASE_URL}/health", headers=_api_headers())
            r.raise_for_status()
            return r.json()
    except Exception:
        return {"status": "unreachable", "snowflake_connected": False, "version": "—"}


def get_schemas() -> List[Dict[str, Any]]:
    """Call GET /schemas and return the schemas list."""
    try:
        with httpx.Client(timeout=10) as client:
            r = client.get(f"{API_BASE_URL}/schemas", headers=_api_headers())
            r.raise_for_status()
            return r.json().get("schemas", [])
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
st.sidebar.title("💊 CMS Stars AI Agents")
st.sidebar.caption("Medicare Part D — Medication Adherence")
st.sidebar.divider()

health = get_health()
status_icon = "🟢" if health.get("status") == "ok" else "🔴"
sf_icon = "🟢" if health.get("snowflake_connected") else "🟡"
st.sidebar.markdown(f"**API** {status_icon} | **Snowflake** {sf_icon}")
st.sidebar.caption(f"API v{health.get('version', '—')} · {API_BASE_URL}")

st.sidebar.divider()
max_rows = st.sidebar.slider("Max result rows", 10, 500, 100, step=10)
show_sql = st.sidebar.toggle("Show SQL", value=True)
show_insights = st.sidebar.toggle("Claude Insights", value=False)

st.sidebar.divider()
st.sidebar.warning(
    "⚠️ Displays de-identified data only. No real PHI shown."
)

# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------
col_chat, col_viz = st.columns([2, 3], gap="medium")

with col_chat:
    st.subheader("💬 Ask a Question")

    # Templates panel
    with st.expander("📚 Analytics Templates", expanded=False):
        selected_template = render_predefined_templates(ANALYTICS_TEMPLATES)
        if selected_template:
            st.session_state.pending_question = selected_template

    # Chat history
    render_chat_history(st.session_state.chat_history)

    # Input
    user_question = render_question_input()

    # Handle template selection
    if "pending_question" in st.session_state:
        user_question = st.session_state.pop("pending_question")

    if user_question:
        st.session_state.chat_history.append({"role": "user", "content": user_question})
        with st.spinner("Querying Cortex Analyst..."):
            api_response = call_api(user_question, max_rows=max_rows)

        if api_response:
            st.session_state.last_response = api_response
            st.session_state.chat_history.append(
                {"role": "assistant", "content": api_response}
            )
            st.rerun()

with col_viz:
    resp = st.session_state.last_response
    if resp:
        st.subheader("📊 Results")
        tab_chart, tab_table, tab_schema = st.tabs(["Chart", "Table", "Schema"])

        with tab_chart:
            render_chart(
                data=resp.get("data", []),
                viz_hint=resp.get("viz_hint", {}),
                title=resp.get("viz_hint", {}).get("title"),
            )
            render_download_buttons(resp.get("data", []))

        with tab_table:
            if resp.get("data"):
                import pandas as pd
                df = pd.DataFrame(resp["data"])
                st.dataframe(df, use_container_width=True)
                render_download_buttons(resp["data"], filename_prefix="adherence_table")
            else:
                st.info("No tabular data returned.")

            if show_sql and resp.get("sql"):
                st.code(resp["sql"], language="sql")

        with tab_schema:
            schemas = get_schemas()
            if schemas:
                for schema in schemas:
                    with st.expander(f"📋 {schema['name']} ({schema['type']})"):
                        st.caption(schema.get("description", ""))
                        if schema.get("columns"):
                            col_df = pd.DataFrame(schema["columns"]) if schemas else None
                            if col_df is not None:
                                st.dataframe(col_df, use_container_width=True, hide_index=True)
            else:
                st.info("Schema metadata unavailable (API not connected).")

        if show_insights and resp:
            render_insights_panel(
                question=st.session_state.chat_history[-2]["content"] if len(st.session_state.chat_history) >= 2 else "",
                answer=resp.get("answer", ""),
                data=resp.get("data", []),
            )
    else:
        st.subheader("📊 Results")
        st.info("Ask a question to see results here.")
        st.markdown("""
**Example questions to try:**
- What is the average adherence rate by therapeutic class?
- Which states have the lowest statin adherence rates?
- Show monthly prescription gap trends for 2024
- Compare LIS vs non-LIS member adherence
""")
