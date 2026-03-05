"""
test_orchestrator.py — Unit tests for agent routing logic
"""

import pytest

from agents.routing import route_query
from python.config import (
    AGENT_AUDIT_EXPLAINABILITY,
    AGENT_GAP_DETECTION,
    AGENT_MEASURE_INTERPRETATION,
    AGENT_OUTREACH_RECOMMENDATION,
    AGENT_STARS_PERFORMANCE,
)


class TestRouteQuery:
    """Tests for query intent routing to the correct agent."""

    def test_measure_interpretation_what_is(self):
        result = route_query("What is the HRM measure?")
        assert result == AGENT_MEASURE_INTERPRETATION

    def test_measure_interpretation_denominator(self):
        result = route_query("What is the denominator logic for the PDC measure?")
        assert result == AGENT_MEASURE_INTERPRETATION

    def test_measure_interpretation_exclusion(self):
        result = route_query("What are the exclusions for the SUPD measure?")
        assert result == AGENT_MEASURE_INTERPRETATION

    def test_measure_interpretation_explain(self):
        result = route_query("Can you explain the HRM measure specification?")
        assert result == AGENT_MEASURE_INTERPRETATION

    def test_gap_detection_risk(self):
        result = route_query("Which members are at risk for HRM gaps?")
        assert result == AGENT_GAP_DETECTION

    def test_gap_detection_safety_gap(self):
        result = route_query("Show me all open safety gaps for contract H1234")
        assert result == AGENT_GAP_DETECTION

    def test_gap_detection_detect(self):
        result = route_query("Detect medication safety gaps in the statin adherence measure")
        assert result == AGENT_GAP_DETECTION

    def test_outreach_recommendation_recommend(self):
        result = route_query("Recommend an intervention for this member")
        assert result == AGENT_OUTREACH_RECOMMENDATION

    def test_outreach_recommendation_cmr(self):
        result = route_query("Should we schedule a CMR for this member?")
        assert result == AGENT_OUTREACH_RECOMMENDATION

    def test_outreach_recommendation_formulary(self):
        result = route_query("Are there formulary alternatives for this medication?")
        assert result == AGENT_OUTREACH_RECOMMENDATION

    def test_stars_performance_rate(self):
        result = route_query("What is the measure rate for contract H1234?")
        assert result == AGENT_STARS_PERFORMANCE

    def test_stars_performance_trend(self):
        result = route_query("Show me the year-over-year trend for the HRM measure")
        assert result == AGENT_STARS_PERFORMANCE

    def test_stars_performance_compare(self):
        result = route_query("Compare performance across contracts")
        assert result == AGENT_STARS_PERFORMANCE

    def test_audit_why_flagged(self):
        result = route_query("Why was this member flagged?")
        assert result == AGENT_AUDIT_EXPLAINABILITY

    def test_audit_audit_trail(self):
        result = route_query("Show me the audit trail for this decision")
        assert result == AGENT_AUDIT_EXPLAINABILITY

    def test_audit_explain_decision(self):
        result = route_query("Explain why member MBR00001234 was scored HIGH risk")
        assert result == AGENT_AUDIT_EXPLAINABILITY

    def test_default_fallback(self):
        result = route_query("Hello, who are you?")
        assert result == AGENT_MEASURE_INTERPRETATION

    def test_case_insensitive(self):
        result = route_query("WHAT IS THE DENOMINATOR FOR HRM?")
        assert result == AGENT_MEASURE_INTERPRETATION
