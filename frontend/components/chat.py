"""
frontend/components/chat.py — Chat interface component for natural language queries.

Renders the chat history, handles question submission, and displays
structured API responses including answer, SQL, and evidence.
"""

from typing import Any, Dict, List, Optional
import streamlit as st


def render_chat_history(history: List[Dict[str, Any]]) -> None:
    """Render a scrollable chat history of user questions and agent answers."""
    for msg in history:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                _render_response(msg["content"])


def _render_response(response: Dict[str, Any]) -> None:
    """Render a structured API response inside a chat message."""
    if isinstance(response, str):
        st.write(response)
        return

    answer = response.get("answer", "")
    if answer:
        st.markdown(answer)

    confidence_icon = "✅" if not response.get("truncated") else "⚠️"
    cols = st.columns([3, 1])
    with cols[1]:
        st.caption(f"{confidence_icon} {response.get('row_count', 0)} rows · {response.get('latency_ms', 0)}ms")

    if response.get("sql"):
        with st.expander("🔍 Generated SQL"):
            st.code(response["sql"], language="sql")

    if response.get("truncated"):
        st.info(f"Results truncated. Showing first {response.get('row_count')} rows.")


def render_question_input(placeholder: str = "Ask about medication adherence data...") -> Optional[str]:
    """
    Render a chat input box.  Returns the submitted question or None.
    """
    return st.chat_input(placeholder)


def render_predefined_templates(templates: List[Dict[str, Any]]) -> Optional[str]:
    """
    Render predefined query template buttons grouped by category.

    Returns the selected template question or None.
    """
    categories = {}
    for t in templates:
        cat = t.get("category", "General")
        categories.setdefault(cat, []).append(t)

    selected = None
    for category, items in sorted(categories.items()):
        st.caption(f"**{category}**")
        cols = st.columns(min(len(items), 2))
        for i, item in enumerate(items):
            with cols[i % 2]:
                if st.button(item["label"], key=f"tpl_{item['label']}", use_container_width=True):
                    selected = item["question"]

    return selected
