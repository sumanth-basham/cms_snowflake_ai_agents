"""
gap_detection_tools.py — Custom tools for the Patient Safety Gap Detection Agent.

These tools query de-identified claims and member data to surface
medication safety gaps and risk scores. All outputs use surrogate member IDs.

IMPORTANT: PHI handling
- member_id in all outputs is a de-identified surrogate — not a real MBI
- Aggregated results with fewer than 11 members are suppressed
- These tools are only accessible to roles with CMS_STARS_CLINICAL or CMS_STARS_ANALYST
"""

import logging
from typing import Any, Dict, List, Optional

from python.config import DATABASE, SCHEMA_GOLD, SCHEMA_CURATED, RISK_SCORE_HIGH, RISK_SCORE_MEDIUM
from python.db_helpers import execute_query

logger = logging.getLogger(__name__)

SMALL_CELL_THRESHOLD = 11


def query_member_safety_gaps(
    contract_id: str,
    measure_code: Optional[str] = None,
    measurement_year: int = 2024,
    risk_threshold: float = 0.0,
    limit: int = 100,
) -> Dict[str, Any]:
    """
    Query open patient safety gaps for a contract, optionally filtered by measure.

    Args:
        contract_id: CMS contract ID
        measure_code: Optional measure code filter
        measurement_year: Stars measurement year
        risk_threshold: Minimum risk score to include (0.0 = all)
        limit: Maximum number of member records to return

    Returns:
        Dict with summary stats and list of at-risk member surrogate IDs
    """
    measure_filter = "AND measure_code = %s" if measure_code else ""
    params = [contract_id, measurement_year, risk_threshold]
    if measure_code:
        params.insert(2, measure_code)

    sql = f"""
SELECT
    member_id AS member_surrogate_id,
    measure_code,
    gap_status,
    risk_score,
    gap_detected_date,
    evidence_summary
FROM {DATABASE}.{SCHEMA_GOLD}.STARS_MEASURE_FACT
WHERE contract_id = %s
  AND measurement_year = %s
  {measure_filter}
  AND risk_score >= %s
  AND gap_status = 'OPEN'
ORDER BY risk_score DESC
LIMIT {limit}
"""
    rows = execute_query(sql, params=tuple(params))

    total_count = len(rows)
    if total_count < SMALL_CELL_THRESHOLD:
        return {
            "suppressed": True,
            "reason": f"Result set contains fewer than {SMALL_CELL_THRESHOLD} members. Suppressed per small-cell policy.",
            "contract_id": contract_id,
            "measure_code": measure_code,
            "measurement_year": measurement_year,
        }

    high_risk = [r for r in rows if r.get("RISK_SCORE", 0) >= RISK_SCORE_HIGH]
    medium_risk = [r for r in rows if RISK_SCORE_MEDIUM <= r.get("RISK_SCORE", 0) < RISK_SCORE_HIGH]

    return {
        "contract_id": contract_id,
        "measure_code": measure_code,
        "measurement_year": measurement_year,
        "total_open_gaps": total_count,
        "high_risk_count": len(high_risk),
        "medium_risk_count": len(medium_risk),
        "members": [
            {
                "member_surrogate_id": r.get("MEMBER_SURROGATE_ID"),
                "measure_code": r.get("MEASURE_CODE"),
                "gap_status": r.get("GAP_STATUS"),
                "risk_score": r.get("RISK_SCORE"),
                "gap_detected_date": str(r.get("GAP_DETECTED_DATE", "")),
            }
            for r in rows
        ],
        "data_quality_note": "Verify gap logic against MEASURE_DEFINITIONS.spec_confirmed before use in official reporting.",
    }


def score_member_risk(
    contract_id: str,
    measurement_year: int = 2024,
    priority_tier: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve member risk profiles with overall risk scores and gap flags.

    Args:
        contract_id: CMS contract ID
        measurement_year: Stars measurement year
        priority_tier: Optional filter: HIGH, MEDIUM, or LOW

    Returns:
        Dict with risk profile summary and member list (surrogate IDs only)
    """
    tier_filter = "AND priority_tier = %s" if priority_tier else ""
    params = [contract_id, measurement_year]
    if priority_tier:
        params.append(priority_tier)

    sql = f"""
SELECT
    member_id AS member_surrogate_id,
    overall_risk_score,
    hrm_risk_flag,
    ddi_risk_flag,
    pdc_risk_flag,
    supd_risk_flag,
    open_gap_count,
    intervention_count,
    priority_tier,
    last_intervention_date
FROM {DATABASE}.{SCHEMA_GOLD}.MEMBER_RISK_PROFILE
WHERE contract_id = %s
  AND measurement_year = %s
  {tier_filter}
ORDER BY overall_risk_score DESC
"""
    rows = execute_query(sql, params=tuple(params))

    if len(rows) < SMALL_CELL_THRESHOLD:
        return {
            "suppressed": True,
            "reason": f"Fewer than {SMALL_CELL_THRESHOLD} members in scope.",
        }

    return {
        "contract_id": contract_id,
        "measurement_year": measurement_year,
        "total_members": len(rows),
        "avg_risk_score": round(
            sum(r.get("OVERALL_RISK_SCORE", 0) for r in rows) / max(len(rows), 1), 3
        ),
        "members": [
            {
                "member_surrogate_id": r.get("MEMBER_SURROGATE_ID"),
                "overall_risk_score": r.get("OVERALL_RISK_SCORE"),
                "priority_tier": r.get("PRIORITY_TIER"),
                "open_gap_count": r.get("OPEN_GAP_COUNT"),
                "hrm_risk_flag": r.get("HRM_RISK_FLAG"),
                "ddi_risk_flag": r.get("DDI_RISK_FLAG"),
                "pdc_risk_flag": r.get("PDC_RISK_FLAG"),
                "supd_risk_flag": r.get("SUPD_RISK_FLAG"),
            }
            for r in rows
        ],
    }


def get_adherence_history(
    member_surrogate_id: str,
    measurement_year: int = 2024,
) -> Dict[str, Any]:
    """
    Retrieve medication adherence history for a single member.

    Args:
        member_surrogate_id: De-identified surrogate member ID
        measurement_year: Stars measurement year

    Returns:
        Dict with adherence measure results (PDC values)
    """
    sql = f"""
SELECT
    measure_code,
    pdc_value,
    in_denominator,
    in_numerator,
    gap_status,
    compliance_flag
FROM {DATABASE}.{SCHEMA_GOLD}.STARS_MEASURE_FACT
WHERE member_id = %s
  AND measurement_year = %s
  AND measure_code LIKE 'PDC_%'
ORDER BY measure_code
"""
    rows = execute_query(sql, params=(member_surrogate_id, measurement_year))
    return {
        "member_surrogate_id": member_surrogate_id,
        "measurement_year": measurement_year,
        "adherence_measures": [
            {
                "measure_code": r.get("MEASURE_CODE"),
                "pdc_value": r.get("PDC_VALUE"),
                "in_denominator": r.get("IN_DENOMINATOR"),
                "in_numerator": r.get("IN_NUMERATOR"),
                "compliance_flag": r.get("COMPLIANCE_FLAG"),
                "gap_status": r.get("GAP_STATUS"),
            }
            for r in rows
        ],
        "note": "PDC values are computed from synthetic sample data. Official PDC requires validated measure logic.",
    }
