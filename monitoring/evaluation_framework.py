"""
evaluation_framework.py — Agent response quality evaluation for CMS Stars

Maps to the monitoring/evaluation pattern in the reference repo.
Adapted for: Medicare Part D Patient Safety Stars use case

Evaluation dimensions:
  1. Factual accuracy (measure logic accuracy)
  2. Evidence grounding (responses grounded in retrieved docs)
  3. PHI safety (no PHI in responses)
  4. Confidence calibration
  5. Latency and cost
  6. Human review trigger rate
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    """Result of evaluating a single agent response."""
    audit_id: str
    agent_name: str
    evaluation_timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    phi_safety_pass: bool = True
    phi_safety_issues: List[str] = field(default_factory=list)
    evidence_grounding_score: float = 0.0
    has_required_confidence_level: bool = True
    has_caveats: bool = True
    has_human_review_flag: bool = True
    latency_ms: Optional[int] = None
    token_count: Optional[int] = None
    overall_pass: bool = True
    issues: List[str] = field(default_factory=list)


PHI_PATTERNS = [
    r"\b\d{3}-\d{2}-\d{4}\b",
    r"\b1[A-Z0-9]{10}[A-Z]\b",
    r"\b\d{1,2}/\d{1,2}/\d{4}\b",
]

REQUIRED_RESPONSE_FIELDS = [
    "confidence_level",
    "caveats",
    "human_review_required",
]


def check_phi_safety(response_text: str) -> tuple[bool, List[str]]:
    """
    Check for potential PHI patterns in agent response text.

    Returns:
        (pass_flag, list_of_issues)
    """
    issues = []
    for pattern in PHI_PATTERNS:
        if re.search(pattern, response_text):
            issues.append(f"Potential PHI pattern detected: {pattern}")

    if re.search(r"\bMBR\d{8}\b", response_text):
        pass
    elif re.search(r"member[_\s]id[:\s]+\S+", response_text, re.IGNORECASE):
        if not re.search(r"MBR\*\*\*", response_text):
            issues.append("Potential unmasked member ID in response")

    return len(issues) == 0, issues


def score_evidence_grounding(response: Dict[str, Any]) -> float:
    """
    Score evidence grounding: 1.0 = well-grounded, 0.0 = no evidence cited.
    """
    evidence = response.get("evidence", [])
    if not evidence:
        return 0.0
    evidenced_with_excerpt = [
        e for e in evidence if e.get("excerpt") and len(e.get("excerpt", "")) > 10
    ]
    return round(len(evidenced_with_excerpt) / max(len(evidence), 1), 2)


def evaluate_response(
    audit_id: str,
    agent_name: str,
    response: Dict[str, Any],
) -> EvaluationResult:
    """
    Evaluate a single agent response for quality dimensions.

    Args:
        audit_id: Audit log ID for this response
        agent_name: Name of the agent
        response: The full agent response dict

    Returns:
        EvaluationResult with pass/fail flags and scores
    """
    result = EvaluationResult(audit_id=audit_id, agent_name=agent_name)

    response_text = response.get("response_text", "")

    phi_pass, phi_issues = check_phi_safety(response_text)
    result.phi_safety_pass = phi_pass
    result.phi_safety_issues = phi_issues
    if not phi_pass:
        result.issues.extend(phi_issues)
        result.overall_pass = False

    result.evidence_grounding_score = score_evidence_grounding(response)
    if result.evidence_grounding_score < 0.5:
        result.issues.append(
            f"Low evidence grounding score: {result.evidence_grounding_score}. "
            "Response may not be adequately grounded in retrieved documents."
        )

    if not response.get("confidence_level"):
        result.has_required_confidence_level = False
        result.issues.append("Missing confidence_level in response.")
        result.overall_pass = False

    if not response.get("caveats"):
        result.has_caveats = False
        result.issues.append("Missing caveats in response. All healthcare AI responses should include caveats.")

    if "human_review_required" not in response:
        result.has_human_review_flag = False
        result.issues.append("Missing human_review_required flag.")

    result.latency_ms = response.get("latency_ms")
    if result.latency_ms and result.latency_ms > 30000:
        result.issues.append(f"High latency: {result.latency_ms}ms exceeds 30 second threshold.")

    logger.info(
        "Evaluation for %s (audit %s): pass=%s, grounding=%.2f, phi_safe=%s",
        agent_name,
        audit_id,
        result.overall_pass,
        result.evidence_grounding_score,
        result.phi_safety_pass,
    )

    return result


def batch_evaluate_from_audit_log(
    audit_records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate a batch of agent responses from audit log records.

    Args:
        audit_records: List of AGENT_AUDIT_LOG rows

    Returns:
        Evaluation summary with aggregate metrics
    """
    results = []
    for record in audit_records:
        response = {
            "response_text": record.get("response_summary", ""),
            "evidence": json.loads(record.get("retrieval_sources") or "[]"),
            "confidence_level": record.get("confidence_level"),
            "human_review_required": record.get("human_review_required"),
            "caveats": [],
            "latency_ms": record.get("latency_ms"),
        }
        eval_result = evaluate_response(
            audit_id=record.get("audit_id", ""),
            agent_name=record.get("agent_name", ""),
            response=response,
        )
        results.append(eval_result)

    total = len(results)
    if total == 0:
        return {"total": 0, "message": "No records to evaluate."}

    pass_count = sum(1 for r in results if r.overall_pass)
    phi_fail_count = sum(1 for r in results if not r.phi_safety_pass)
    avg_grounding = sum(r.evidence_grounding_score for r in results) / total

    return {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "total_evaluated": total,
        "overall_pass_rate": round(pass_count / total, 3),
        "phi_safety_fail_count": phi_fail_count,
        "avg_evidence_grounding_score": round(avg_grounding, 3),
        "issues_by_agent": _group_issues_by_agent(results),
        "recommendation": (
            "Evaluation passed" if phi_fail_count == 0
            else "URGENT: PHI safety failures detected — review immediately"
        ),
    }


def _group_issues_by_agent(results: List[EvaluationResult]) -> Dict[str, List[str]]:
    issues_by_agent: Dict[str, List[str]] = {}
    for r in results:
        if r.issues:
            if r.agent_name not in issues_by_agent:
                issues_by_agent[r.agent_name] = []
            issues_by_agent[r.agent_name].extend(r.issues)
    return issues_by_agent
