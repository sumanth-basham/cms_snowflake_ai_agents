"""
routing.py — Query intent routing logic (no Snowflake dependency).

Pure routing logic extracted from orchestrator.py for testability.
"""

import logging
import re
from typing import Optional

from python.config import (
    AGENT_AUDIT_EXPLAINABILITY,
    AGENT_GAP_DETECTION,
    AGENT_MEASURE_INTERPRETATION,
    AGENT_OUTREACH_RECOMMENDATION,
    AGENT_STARS_PERFORMANCE,
)

logger = logging.getLogger(__name__)


ROUTING_RULES = [
    {
        "patterns": [
            r"(why was|explain why|audit|audit trail|compliance|explainability|transparency)",
            r"(how was .*(flagged|scored|recommended|calculated))",
            r"evidence (for|behind|supporting) .*(decision|flag|recommendation)",
        ],
        "agent": AGENT_AUDIT_EXPLAINABILITY,
        "reason": "Audit or explainability request",
    },
    {
        "patterns": [
            r"(performance|trend|measure rate|star rating|contract performance)",
            r"(how (is|are|did|does) .*(contract|plan|region|provider) (perform|doing|trend))",
            r"(compare|benchmark|target|improvement opportunity)",
            r"(year.over.year|yoy|prior year|historical)",
        ],
        "agent": AGENT_STARS_PERFORMANCE,
        "reason": "Performance analytics or trend question",
    },
    {
        "patterns": [
            r"what (is|does|are) .*(measure|numerator|denominator|exclusion|threshold)",
            r"explain .*(measure|hrm|ddi|supd|pdc|mtm|cmr)",
            r"how (is|does) .*(measure|star|rating) (calculated|work|defined)",
            r"(denominator|numerator|exclusion) logic",
            r"measure (definition|spec|specification|change|version)",
        ],
        "agent": AGENT_MEASURE_INTERPRETATION,
        "reason": "Measure interpretation or explanation question",
    },
    {
        "patterns": [
            r"(gap|at.risk|safety gap|medication safety)",
            r"(which|what|show) members? .*(risk|gap|open|flagged)",
            r"(hrm|ddi|pdc|supd|mtm) (gap|risk|fail|not meeting)",
            r"member(s)? (with|at|who) .*(risk|gap|flag)",
            r"(detect|identify|find) .*(gap|risk|safety issue)",
        ],
        "agent": AGENT_GAP_DETECTION,
        "reason": "Patient safety gap detection or member risk query",
    },
    {
        "patterns": [
            r"(recommend|intervention|outreach|action|what should)",
            r"(cmr|tmr|pharmacist|provider outreach|member outreach)",
            r"(formulary|alternative|switch|change) .*(medication|drug|therapy)",
            r"(next step|action plan|care plan|engagement)",
        ],
        "agent": AGENT_OUTREACH_RECOMMENDATION,
        "reason": "Intervention or outreach recommendation",
    },
]


def route_query(user_message: str) -> str:
    """
    Determine which agent should handle the query based on pattern matching.
    Falls back to Measure Interpretation Agent if no match.
    """
    message_lower = user_message.lower()
    for rule in ROUTING_RULES:
        for pattern in rule["patterns"]:
            if re.search(pattern, message_lower):
                logger.info("Routing to %s: %s", rule["agent"], rule["reason"])
                return rule["agent"]

    logger.info("No specific route matched — defaulting to %s", AGENT_MEASURE_INTERPRETATION)
    return AGENT_MEASURE_INTERPRETATION
