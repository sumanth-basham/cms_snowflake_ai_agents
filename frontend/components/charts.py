"""
frontend/components/charts.py — Chart rendering component.

Renders Plotly charts from API response data and viz hints.
Supports: line, bar, scatter, histogram, metric (KPI card), table.
"""

from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st


def render_chart(
    data: List[Dict[str, Any]],
    viz_hint: Dict[str, Any],
    title: Optional[str] = None,
) -> None:
    """
    Render a chart or table from API response data.

    Args:
        data: List of row dicts from the API response
        viz_hint: Visualization hint dict with chart, x, y, title keys
        title: Optional title override
    """
    if not data:
        st.info("No data to display.")
        return

    try:
        import plotly.express as px
        import plotly.graph_objects as go
    except ImportError:
        st.warning("Plotly not installed. Displaying data as table.")
        st.dataframe(pd.DataFrame(data), use_container_width=True)
        return

    df = pd.DataFrame(data)
    chart_type = viz_hint.get("chart", "table")
    x_col = viz_hint.get("x")
    y_col = viz_hint.get("y")
    chart_title = title or viz_hint.get("title", "")

    # Validate column names exist
    if x_col and x_col not in df.columns:
        x_col = df.columns[0] if len(df.columns) > 0 else None
    if y_col and y_col not in df.columns:
        y_col = df.columns[-1] if len(df.columns) > 1 else None

    try:
        if chart_type == "line" and x_col and y_col:
            fig = px.line(df, x=x_col, y=y_col, title=chart_title)
        elif chart_type == "bar" and x_col and y_col:
            fig = px.bar(df, x=x_col, y=y_col, title=chart_title)
        elif chart_type == "scatter" and x_col and y_col:
            fig = px.scatter(df, x=x_col, y=y_col, title=chart_title)
        elif chart_type == "histogram" and x_col:
            fig = px.histogram(df, x=x_col, title=chart_title)
        elif chart_type == "metric" and len(df) == 1:
            col_name = y_col or df.columns[0]
            val = df.iloc[0][col_name]
            st.metric(label=col_name, value=_format_metric(val))
            return
        else:
            _render_table(df)
            return

        fig.update_layout(
            template="plotly_white",
            height=400,
            margin=dict(l=40, r=20, t=50, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)
    except Exception as exc:
        st.warning(f"Chart rendering failed: {exc}. Displaying table.")
        _render_table(df)


def _render_table(df: pd.DataFrame) -> None:
    """Render a styled dataframe table."""
    st.dataframe(df, use_container_width=True, height=min(400, 35 * len(df) + 38))


def _format_metric(value: Any) -> str:
    """Format a scalar metric value for display."""
    if isinstance(value, float):
        if 0.0 <= value <= 1.0:
            return f"{value:.1%}"
        return f"{value:,.2f}"
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def render_download_buttons(data: List[Dict[str, Any]], filename_prefix: str = "adherence") -> None:
    """Render CSV download button for query results."""
    if not data:
        return
    df = pd.DataFrame(data)
    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download CSV",
        data=csv,
        file_name=f"{filename_prefix}_results.csv",
        mime="text/csv",
    )
