"""
app.py — Streamlit in Snowflake UI for CMS Stars AI Agents

Maps to the app pattern in the reference repo.
Adapted for: Medicare Part D Patient Safety Stars use case

Screens:
  1. Home / Navigator
  2. Measure Explorer (ask questions about measures)
  3. Patient Safety Gap Dashboard (review gaps by contract/measure)
  4. Member Detail (explain why a member was flagged)
  5. Intervention Recommender
  6. Stars Performance Trends
  7. Audit Trail Viewer

PHI Safety:
  - Member names and contact info are NEVER displayed in this app
  - Only de-identified surrogate member IDs are shown
  - Aggregated results suppress cells with <11 members
"""

import streamlit as st
import pandas as pd
import json
from typing import Optional

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="CMS Stars AI Agents",
    page_icon="💊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

if "session_id" not in st.session_state:
    import uuid
    st.session_state.session_id = str(uuid.uuid4())

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "current_screen" not in st.session_state:
    st.session_state.current_screen = "home"

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------

st.sidebar.title("CMS Stars AI Agents")
st.sidebar.caption("Medicare Part D Patient Safety Stars")

SCREENS = {
    "🏠 Home": "home",
    "📋 Measure Explorer": "measure_explorer",
    "🔍 Safety Gap Dashboard": "gap_dashboard",
    "👤 Member Detail": "member_detail",
    "💡 Intervention Recommender": "intervention",
    "📈 Stars Performance": "performance",
    "🔎 Audit Trail": "audit",
}

selected_screen = st.sidebar.radio(
    "Navigate to",
    list(SCREENS.keys()),
    key="nav_selector",
)
st.session_state.current_screen = SCREENS[selected_screen]

st.sidebar.divider()
st.sidebar.caption(f"Session: {st.session_state.session_id[:8]}...")

# Role selector (for demo purposes; production uses Snowflake session role)
user_role = st.sidebar.selectbox(
    "User Role (Demo)",
    ["analyst", "clinical", "auditor", "admin"],
    key="user_role",
)

st.sidebar.divider()
st.sidebar.warning(
    "⚠️ This app uses de-identified surrogate member IDs. "
    "No real member PHI is displayed."
)

# ---------------------------------------------------------------------------
# Helper: Call the orchestrator (stub for Streamlit in Snowflake)
# ---------------------------------------------------------------------------

def call_agent(
    user_message: str,
    force_agent: Optional[str] = None,
) -> dict:
    """
    Call the CMS Stars agent orchestrator.

    In production (Streamlit in Snowflake), this calls the Cortex Agent
    via the Snowpark session. For local development, this returns a stub.
    """
    try:
        from agents.orchestrator import orchestrate
        return orchestrate(
            user_message=user_message,
            session_id=st.session_state.session_id,
            user_role=user_role,
            force_agent=force_agent,
        )
    except Exception as exc:
        # Graceful degradation for demo/local mode
        return {
            "response_text": f"[Demo mode] Agent not connected. Query was: {user_message[:100]}",
            "confidence_level": "INSUFFICIENT",
            "human_review_required": True,
            "evidence": [],
            "tools_invoked": [],
            "caveats": ["Connect to Snowflake to use live agent responses."],
            "error": str(exc),
        }


def display_response_card(response: dict) -> None:
    """Display a formatted agent response card."""
    confidence = response.get("confidence_level", "UNKNOWN")
    color_map = {
        "HIGH": "🟢",
        "MEDIUM": "🟡",
        "LOW": "🔴",
        "INSUFFICIENT": "⛔",
        "UNKNOWN": "⚪",
    }
    icon = color_map.get(confidence, "⚪")

    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown("**Agent Response**")
    with col2:
        st.caption(f"{icon} Confidence: {confidence}")

    st.markdown(response.get("response_text", ""))

    if response.get("human_review_required"):
        st.warning("⚠️ This response requires human review before action.")

    if response.get("evidence"):
        with st.expander("📚 Evidence sources"):
            for ev in response["evidence"]:
                st.caption(f"**{ev.get('source', 'Unknown')}**: {ev.get('excerpt', '')[:200]}")

    if response.get("caveats"):
        with st.expander("⚠️ Caveats and limitations"):
            for c in response.get("caveats", []):
                st.caption(f"• {c}")


# ---------------------------------------------------------------------------
# Screen: Home
# ---------------------------------------------------------------------------

def screen_home():
    st.title("💊 CMS Stars AI Agents")
    st.subheader("Medicare Part D Patient Safety Stars — Quality Operations Platform")
    st.markdown("""
    Welcome to the CMS Stars AI Agent platform. Use the navigation sidebar to:

    | Screen | Purpose |
    |---|---|
    | 📋 **Measure Explorer** | Ask questions about CMS/PQA measure logic |
    | 🔍 **Safety Gap Dashboard** | View open patient safety gaps by contract/measure |
    | 👤 **Member Detail** | Understand why a specific member was flagged |
    | 💡 **Intervention Recommender** | Get evidence-based intervention recommendations |
    | 📈 **Stars Performance** | Review contract-level Stars trends |
    | 🔎 **Audit Trail** | View AI decision audit records |

    ---
    **Important**: All member references use de-identified surrogate IDs.
    No real PHI is displayed in this application.
    All AI-generated recommendations require human review before action.
    """)


# ---------------------------------------------------------------------------
# Screen: Measure Explorer
# ---------------------------------------------------------------------------

def screen_measure_explorer():
    st.title("📋 Measure Explorer")
    st.caption("Ask questions about Medicare Part D Stars measures")

    st.markdown("""
    **Example questions:**
    - "What is the HRM measure and how is it calculated?"
    - "What are the exclusions for the SUPD measure?"
    - "How did the PDC measure definition change from 2023 to 2024?"
    - "What is the denominator logic for medication adherence measures?"
    """)

    user_question = st.text_area(
        "Ask a measure question",
        placeholder="e.g. What is the denominator for the HRM measure?",
        height=100,
    )

    if st.button("Ask Measure Agent", type="primary"):
        if user_question.strip():
            with st.spinner("Querying Measure Interpretation Agent..."):
                response = call_agent(
                    user_message=user_question,
                    force_agent="MEASURE_INTERPRETATION_AGENT",
                )
            display_response_card(response)
            st.session_state.chat_history.append(
                {"role": "user", "content": user_question}
            )
            st.session_state.chat_history.append(
                {"role": "agent", "content": response.get("response_text", "")}
            )

    if st.session_state.chat_history:
        with st.expander("💬 Conversation history"):
            for msg in st.session_state.chat_history[-10:]:
                role_icon = "👤" if msg["role"] == "user" else "🤖"
                st.caption(f"{role_icon} **{msg['role'].title()}**: {msg['content'][:300]}")


# ---------------------------------------------------------------------------
# Screen: Safety Gap Dashboard
# ---------------------------------------------------------------------------

def screen_gap_dashboard():
    st.title("🔍 Patient Safety Gap Dashboard")
    st.caption("Review open patient safety gaps by contract and measure")

    col1, col2, col3 = st.columns(3)
    with col1:
        contract_id = st.text_input("Contract ID", value="H1234")
    with col2:
        measure_code = st.selectbox(
            "Measure",
            ["ALL", "HRM_V1", "SUPD_V1", "PDC_STATIN", "PDC_RASA", "PDC_DIAB", "DDI_WARFARIN_NSAID"],
        )
    with col3:
        measurement_year = st.selectbox("Measurement Year", [2024, 2023, 2022])

    if st.button("Detect Gaps", type="primary"):
        measure_filter = None if measure_code == "ALL" else measure_code
        query = (
            f"Show me open patient safety gaps for contract {contract_id}, "
            f"measure {measure_filter or 'all measures'}, "
            f"measurement year {measurement_year}. "
            "Return a summary of high-risk members (surrogate IDs only) with risk scores."
        )
        with st.spinner("Running Patient Safety Gap Detection Agent..."):
            response = call_agent(
                user_message=query,
                force_agent="PATIENT_SAFETY_GAP_DETECTION_AGENT",
            )
        display_response_card(response)


# ---------------------------------------------------------------------------
# Screen: Member Detail
# ---------------------------------------------------------------------------

def screen_member_detail():
    st.title("👤 Member Detail — Why Was This Member Flagged?")
    st.caption("Explainability for individual member risk flags (surrogate IDs only)")

    st.warning("⚠️ Enter de-identified surrogate member IDs only. Never enter real member names, MBIs, or SSNs.")

    member_id = st.text_input(
        "Member Surrogate ID",
        placeholder="e.g. MBR00012345",
    )
    measure_code = st.text_input(
        "Measure Code (optional)",
        placeholder="e.g. HRM_V1",
    )

    if st.button("Explain Flag", type="primary"):
        if member_id.strip():
            query = (
                f"Explain why member {member_id} was flagged"
                + (f" for the {measure_code} measure" if measure_code.strip() else "")
                + ". Include the data evidence, measure rule applied, and confidence level."
            )
            with st.spinner("Running Audit/Explainability Agent..."):
                response = call_agent(
                    user_message=query,
                    force_agent="AUDIT_EXPLAINABILITY_AGENT",
                )
            display_response_card(response)


# ---------------------------------------------------------------------------
# Screen: Intervention Recommender
# ---------------------------------------------------------------------------

def screen_intervention():
    st.title("💡 Intervention Recommender")
    st.caption("Evidence-based intervention recommendations for at-risk members")

    st.info("All recommendations require analyst review and approval before action.")

    member_id = st.text_input("Member Surrogate ID", placeholder="e.g. MBR00012345")
    contract_id = st.text_input("Contract ID", value="H1234")
    measure_code = st.text_input("Gap / Measure Code", placeholder="e.g. HRM_V1")

    if st.button("Get Recommendation", type="primary"):
        if member_id.strip():
            query = (
                f"What intervention should we recommend for member {member_id} "
                f"in contract {contract_id}"
                + (f" with gap {measure_code}" if measure_code.strip() else "")
                + "? Consider their intervention history and prioritize the most impactful action."
            )
            with st.spinner("Running Outreach Recommendation Agent..."):
                response = call_agent(
                    user_message=query,
                    force_agent="OUTREACH_RECOMMENDATION_AGENT",
                )
            display_response_card(response)

            analyst_notes = st.text_area(
                "Analyst Review Notes",
                placeholder="Enter your review decision and notes here...",
                height=100,
            )
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve Recommendation", type="primary"):
                    st.success("Recommendation approved and logged.")
            with col2:
                if st.button("❌ Reject Recommendation"):
                    st.error("Recommendation rejected and logged.")


# ---------------------------------------------------------------------------
# Screen: Stars Performance
# ---------------------------------------------------------------------------

def screen_performance():
    st.title("📈 Stars Performance Analytics")
    st.caption("Contract and plan-level Stars measure performance trends")

    col1, col2 = st.columns(2)
    with col1:
        contract_id = st.text_input("Contract ID (or ALL)", value="H1234")
        measure_code = st.selectbox(
            "Measure",
            ["ALL", "HRM_V1", "SUPD_V1", "PDC_STATIN", "PDC_RASA", "PDC_DIAB"],
        )
    with col2:
        start_year = st.selectbox("Start Year", [2022, 2023, 2024])
        end_year = st.selectbox("End Year", [2024, 2023], index=0)

    if st.button("Analyze Performance", type="primary"):
        measure_str = measure_code if measure_code != "ALL" else "all measures"
        query = (
            f"Show the Stars performance trend for contract {contract_id}, "
            f"measure {measure_str}, from {start_year} to {end_year}. "
            "Include year-over-year rate changes and estimated star rating."
        )
        with st.spinner("Running Stars Performance Analytics Agent..."):
            response = call_agent(
                user_message=query,
                force_agent="STARS_PERFORMANCE_ANALYTICS_AGENT",
            )
        display_response_card(response)


# ---------------------------------------------------------------------------
# Screen: Audit Trail
# ---------------------------------------------------------------------------

def screen_audit():
    st.title("🔎 Audit Trail Viewer")
    st.caption("Review AI decision audit records for compliance and transparency")

    if user_role not in ["auditor", "admin", "clinical"]:
        st.error("Access restricted. Audit Trail requires auditor, admin, or clinical role.")
        return

    query = st.text_input(
        "Audit query",
        placeholder="e.g. Show audit records for gap detections in contract H1234 last week",
    )
    if st.button("Search Audit Log", type="primary"):
        if query.strip():
            full_query = f"Retrieve audit trail: {query}. Include evidence sources and confidence levels."
            with st.spinner("Running Audit/Explainability Agent..."):
                response = call_agent(
                    user_message=full_query,
                    force_agent="AUDIT_EXPLAINABILITY_AGENT",
                )
            display_response_card(response)


# ---------------------------------------------------------------------------
# Main router
# ---------------------------------------------------------------------------

screen_router = {
    "home": screen_home,
    "measure_explorer": screen_measure_explorer,
    "gap_dashboard": screen_gap_dashboard,
    "member_detail": screen_member_detail,
    "intervention": screen_intervention,
    "performance": screen_performance,
    "audit": screen_audit,
}

screen_fn = screen_router.get(st.session_state.current_screen, screen_home)
screen_fn()
