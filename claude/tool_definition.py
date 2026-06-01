"""
claude/tool_definition.py — Claude tool schema for the Cortex Agent API.

Defines the tool specification that allows Claude to call the
/ask endpoint as a native tool during conversations.

Usage:
    from claude.tool_definition import CORTEX_AGENT_TOOL, TOOL_LIST
    client.messages.create(
        model="claude-3-5-sonnet-20241022",
        tools=TOOL_LIST,
        messages=[...],
    )
"""

from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Tool definition for the POST /ask endpoint
# ---------------------------------------------------------------------------

CORTEX_AGENT_TOOL: Dict[str, Any] = {
    "name": "query_medication_adherence",
    "description": (
        "Query the Medicare Part D medication adherence database using natural language. "
        "Returns structured data including PDC (Proportion of Days Covered) ratios, "
        "prescription gap analysis, adherence trends by therapeutic class, region, and "
        "age group, and patient safety gap metrics. "
        "Use this tool when the user asks about medication adherence rates, prescription gaps, "
        "drug class performance, regional adherence comparisons, or Stars measure analytics."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "question": {
                "type": "string",
                "description": (
                    "Natural language question about Medicare Part D medication adherence. "
                    "Examples: "
                    "'What is the average PDC ratio for statins by region?', "
                    "'Which therapeutic classes have the lowest adherence rates?', "
                    "'Show monthly adherence trends for 2024', "
                    "'How many members have significant prescription gaps (>= 30 days)?'"
                ),
            },
            "max_rows": {
                "type": "integer",
                "description": "Maximum number of result rows to return (default: 100, max: 1000).",
                "default": 100,
            },
        },
        "required": ["question"],
    },
}

# ---------------------------------------------------------------------------
# Tool list (add additional tools here as needed)
# ---------------------------------------------------------------------------

TOOL_LIST: List[Dict[str, Any]] = [CORTEX_AGENT_TOOL]

# ---------------------------------------------------------------------------
# System prompt for Claude when using the Cortex Agent tool
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert Medicare Part D quality analytics assistant. You help health plan \
analysts, pharmacists, and quality teams understand medication adherence patterns and patient safety \
gaps using real claims data.

You have access to a Snowflake Cortex Agent tool (`query_medication_adherence`) that can answer \
questions about:
- Medication adherence rates (PDC ratios) by therapeutic class, region, and age group
- Prescription gap analysis (coverage gaps between refills)
- Patient safety measure performance (HRM, SUPD, PDC Stars measures)
- Monthly and quarterly adherence trends
- LIS vs. non-LIS member adherence comparisons

**Guidelines:**
1. Always call `query_medication_adherence` when the user asks for specific data or metrics.
2. After receiving data, provide a concise interpretation: key findings, trend direction, and 
   actionable implications for quality improvement.
3. Recommend appropriate visualizations (line for trends, bar for comparisons, etc.).
4. Suggest 2-3 follow-up analyses the user might find valuable.
5. Never include real member PHI — all data uses de-identified surrogate IDs.
6. Add a note that all measure logic must be validated against official CMS/PQA specifications.
"""

# ---------------------------------------------------------------------------
# Example prompts for documentation and testing
# ---------------------------------------------------------------------------

EXAMPLE_PROMPTS: List[Dict[str, str]] = [
    {
        "prompt": "What is the average medication adherence rate by therapeutic class for patients over 65?",
        "expected_tool": "query_medication_adherence",
        "expected_viz": "bar",
    },
    {
        "prompt": "Which regions have the lowest adherence rates for cardiovascular medications?",
        "expected_tool": "query_medication_adherence",
        "expected_viz": "bar",
    },
    {
        "prompt": "Show me the monthly trend of statin adherence for 2024.",
        "expected_tool": "query_medication_adherence",
        "expected_viz": "line",
    },
    {
        "prompt": "How many members have prescription gaps of 30 days or more for diabetes medications?",
        "expected_tool": "query_medication_adherence",
        "expected_viz": "table",
    },
    {
        "prompt": "Compare adherence rates between LIS and non-LIS members for ACE inhibitors.",
        "expected_tool": "query_medication_adherence",
        "expected_viz": "bar",
    },
]
