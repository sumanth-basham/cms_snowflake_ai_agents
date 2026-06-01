"""
frontend/components/insights.py — Claude-powered insights component.

Calls the Claude API to generate actionable insights and follow-up
recommendations from query results.
"""

import logging
from typing import Any, Dict, List, Optional

import streamlit as st

logger = logging.getLogger(__name__)


def render_insights_panel(
    question: str,
    answer: str,
    data: List[Dict[str, Any]],
    anthropic_api_key: Optional[str] = None,
) -> None:
    """
    Render an AI insights panel powered by Claude.

    Analyzes the query results and provides:
    - Key observations
    - Actionable recommendations
    - Suggested follow-up questions
    """
    if not anthropic_api_key:
        try:
            from config.settings import get_settings
            settings = get_settings()
            anthropic_api_key = settings.anthropic_api_key
        except Exception:
            pass

    if not anthropic_api_key:
        st.caption("_Connect Claude (ANTHROPIC_API_KEY) for AI-powered insights._")
        return

    with st.expander("🧠 Claude Insights", expanded=False):
        if st.button("Generate Insights", key="gen_insights"):
            with st.spinner("Claude is analyzing results..."):
                insights = _generate_insights(
                    question=question,
                    answer=answer,
                    data=data,
                    api_key=anthropic_api_key,
                )
            if insights:
                st.markdown(insights)


def _generate_insights(
    question: str,
    answer: str,
    data: List[Dict[str, Any]],
    api_key: str,
    model: str = "claude-3-5-sonnet-20241022",
) -> Optional[str]:
    """
    Call the Claude API to generate insights from query results.
    """
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)

        data_preview = _format_data_preview(data)
        prompt = f"""You are a Medicare Part D quality analytics expert. A health plan analyst asked this question:

**Question:** {question}

**System Answer:** {answer}

**Data Sample (first 10 rows):**
{data_preview}

Please provide:
1. **Key Observations** (2-3 bullet points on the most important findings)
2. **Actionable Recommendations** (1-2 specific actions the quality team should take)
3. **Suggested Follow-Up Questions** (2 follow-up questions to explore further)

Keep the response concise and focused on medication adherence and patient safety improvement.
Do NOT include member names, SSNs, or real PHI. Use aggregate-level insights only."""

        message = client.messages.create(
            model=model,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text if message.content else None

    except Exception as exc:
        logger.error("Claude insights generation failed: %s", exc)
        st.error(f"Claude insights unavailable: {exc}")
        return None


def _format_data_preview(data: List[Dict[str, Any]], max_rows: int = 10) -> str:
    """Format data rows as a simple text table for Claude context."""
    if not data:
        return "(no data)"
    try:
        import pandas as pd
        df = pd.DataFrame(data[:max_rows])
        return df.to_string(index=False, max_cols=8)
    except Exception:
        return str(data[:max_rows])
