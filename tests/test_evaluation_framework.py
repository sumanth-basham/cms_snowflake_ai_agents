"""
test_evaluation_framework.py — Unit tests for the agent evaluation framework
"""

import pytest

from monitoring.evaluation_framework import (
    check_phi_safety,
    evaluate_response,
    score_evidence_grounding,
)


class TestCheckPhiSafety:
    def test_clean_response_passes(self):
        text = "The HRM measure denominator includes members 65 and older."
        passed, issues = check_phi_safety(text)
        assert passed
        assert issues == []

    def test_ssn_detected(self):
        text = "Member SSN 123-45-6789 was flagged."
        passed, issues = check_phi_safety(text)
        assert not passed
        assert len(issues) > 0

    def test_date_like_detected(self):
        text = "Member DOB 01/15/1945 was found."
        passed, issues = check_phi_safety(text)
        assert not passed

    def test_masked_member_id_passes(self):
        text = "Member MBR***1234 has an open HRM gap."
        passed, issues = check_phi_safety(text)
        assert passed

    def test_clean_aggregate_passes(self):
        text = "Contract H1234 has 45 open gaps with average risk score 0.72."
        passed, issues = check_phi_safety(text)
        assert passed


class TestScoreEvidenceGrounding:
    def test_no_evidence_returns_zero(self):
        response = {"evidence": []}
        score = score_evidence_grounding(response)
        assert score == 0.0

    def test_missing_evidence_key_returns_zero(self):
        response = {}
        score = score_evidence_grounding(response)
        assert score == 0.0

    def test_full_evidence_returns_one(self):
        response = {
            "evidence": [
                {"source": "HRM Measure Spec", "excerpt": "The denominator includes members 65 and older enrolled continuously"},
                {"source": "PQA Technical Notes", "excerpt": "High-risk medications include benzodiazepines and anticholinergics"},
            ]
        }
        score = score_evidence_grounding(response)
        assert score == 1.0

    def test_partial_evidence_partial_score(self):
        response = {
            "evidence": [
                {"source": "HRM Measure Spec", "excerpt": "The denominator includes members 65 and older"},
                {"source": "Some Doc", "excerpt": ""},
            ]
        }
        score = score_evidence_grounding(response)
        assert 0.0 < score < 1.0


class TestEvaluateResponse:
    def _make_good_response(self):
        return {
            "response_text": "Contract H1234 has 45 open HRM gaps. The measure denominator includes members aged 65+.",
            "confidence_level": "HIGH",
            "caveats": ["Verify against official CMS specifications"],
            "human_review_required": True,
            "evidence": [
                {"source": "HRM Measure Spec 2024", "excerpt": "Denominator: members 65 years and older enrolled continuously."}
            ],
            "latency_ms": 1200,
        }

    def test_good_response_passes(self):
        result = evaluate_response("audit_001", "MEASURE_INTERPRETATION_AGENT", self._make_good_response())
        assert result.overall_pass
        assert result.phi_safety_pass
        assert result.evidence_grounding_score > 0.0

    def test_missing_confidence_level_fails(self):
        response = self._make_good_response()
        del response["confidence_level"]
        result = evaluate_response("audit_002", "TEST_AGENT", response)
        assert not result.overall_pass
        assert not result.has_required_confidence_level

    def test_phi_in_response_fails(self):
        response = self._make_good_response()
        response["response_text"] = "Member SSN 123-45-6789 was flagged for HRM gap."
        result = evaluate_response("audit_003", "TEST_AGENT", response)
        assert not result.phi_safety_pass
        assert not result.overall_pass

    def test_high_latency_flagged(self):
        response = self._make_good_response()
        response["latency_ms"] = 35000
        result = evaluate_response("audit_004", "TEST_AGENT", response)
        assert any("latency" in issue.lower() for issue in result.issues)

    def test_missing_caveats_flagged(self):
        response = self._make_good_response()
        response["caveats"] = []
        result = evaluate_response("audit_005", "TEST_AGENT", response)
        assert not result.has_caveats
        assert any("caveats" in issue.lower() for issue in result.issues)
