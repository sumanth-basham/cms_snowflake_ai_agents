"""
api/routes/schemas.py — GET /schemas endpoint.

Returns metadata about available Snowflake schemas, views, and tables
that are accessible through the Cortex Agent API.
"""

import logging
from typing import List

from fastapi import APIRouter, HTTPException, status

from api.models import SchemaInfo, SchemasResponse

logger = logging.getLogger(__name__)

router = APIRouter()

# Static schema catalog — reflects the semantic layer for the Cortex Analyst.
# In production, this could be dynamically fetched from Snowflake INFORMATION_SCHEMA.
SEMANTIC_VIEWS: List[SchemaInfo] = [
    SchemaInfo(
        name="PATIENT_DEMOGRAPHICS",
        type="VIEW",
        description="Patient demographics: age group, region, LIS status, enrollment.",
        columns=[
            {"name": "member_id", "type": "VARCHAR", "description": "De-identified surrogate member ID"},
            {"name": "contract_id", "type": "VARCHAR", "description": "CMS contract (H-number)"},
            {"name": "region", "type": "VARCHAR", "description": "State code"},
            {"name": "age_years", "type": "INTEGER", "description": "Calculated age in years"},
            {"name": "age_group", "type": "VARCHAR", "description": "Under 65 / 65-74 / 75-84 / 85+"},
            {"name": "gender_code", "type": "VARCHAR", "description": "M / F / U"},
            {"name": "lis_status", "type": "VARCHAR", "description": "LIS_FULL / LIS_PARTIAL / NON_LIS"},
        ],
    ),
    SchemaInfo(
        name="MEDICATION_ADHERENCE_AGGREGATES",
        type="VIEW",
        description=(
            "Medication adherence metrics by therapeutic class, region, and age group. "
            "Includes PDC ratio, adherent rate (PDC >= 0.80), fill count, and gap days."
        ),
        columns=[
            {"name": "therapeutic_class", "type": "VARCHAR", "description": "Drug therapeutic class"},
            {"name": "region", "type": "VARCHAR", "description": "State code"},
            {"name": "age_group", "type": "VARCHAR", "description": "Age band"},
            {"name": "measurement_year", "type": "INTEGER", "description": "Measurement year"},
            {"name": "member_count", "type": "INTEGER", "description": "Distinct member count"},
            {"name": "avg_pdc_ratio", "type": "FLOAT", "description": "Average proportion of days covered"},
            {"name": "adherent_rate", "type": "FLOAT", "description": "Fraction of members with PDC >= 0.80"},
            {"name": "avg_fill_count", "type": "FLOAT", "description": "Average fills per member"},
            {"name": "avg_gap_days", "type": "FLOAT", "description": "Average gap days per member"},
        ],
    ),
    SchemaInfo(
        name="PRESCRIPTION_GAP_ANALYSIS",
        type="VIEW",
        description=(
            "Prescription gap analysis: identifies coverage gaps >= 30 days between fills "
            "by member and therapeutic class."
        ),
        columns=[
            {"name": "member_id", "type": "VARCHAR", "description": "Surrogate member ID"},
            {"name": "therapeutic_class", "type": "VARCHAR", "description": "Drug class"},
            {"name": "fill_date", "type": "DATE", "description": "Fill date"},
            {"name": "coverage_end_date", "type": "DATE", "description": "Date coverage runs out"},
            {"name": "next_fill_date", "type": "DATE", "description": "Date of next fill"},
            {"name": "gap_days", "type": "INTEGER", "description": "Days between coverage end and next fill"},
            {"name": "has_significant_gap", "type": "BOOLEAN", "description": "TRUE if gap >= 30 days"},
        ],
    ),
    SchemaInfo(
        name="OUTCOME_CORRELATION",
        type="VIEW",
        description="Correlates adherence gaps with patient risk scores from safety gap detection.",
        columns=[
            {"name": "member_id", "type": "VARCHAR", "description": "Surrogate member ID"},
            {"name": "therapeutic_class", "type": "VARCHAR", "description": "Drug class"},
            {"name": "total_gap_days", "type": "INTEGER", "description": "Total gap day exposure"},
            {"name": "gap_episodes", "type": "INTEGER", "description": "Count of significant gap episodes"},
            {"name": "risk_score", "type": "FLOAT", "description": "Member risk score (0.0-1.0)"},
            {"name": "measure_code", "type": "VARCHAR", "description": "Patient safety measure code"},
        ],
    ),
    SchemaInfo(
        name="MONTHLY_ADHERENCE_TREND",
        type="VIEW",
        description="Monthly time-series of adherence fill activity by drug class and region.",
        columns=[
            {"name": "fill_month", "type": "DATE", "description": "Month (truncated to first day)"},
            {"name": "therapeutic_class", "type": "VARCHAR", "description": "Drug class"},
            {"name": "region", "type": "VARCHAR", "description": "State code"},
            {"name": "age_group", "type": "VARCHAR", "description": "Age band"},
            {"name": "members_filling", "type": "INTEGER", "description": "Distinct members with fills that month"},
            {"name": "total_days_supplied", "type": "INTEGER", "description": "Total days supply dispensed"},
            {"name": "claim_count", "type": "INTEGER", "description": "Number of claim lines"},
        ],
    ),
]


@router.get(
    "/schemas",
    response_model=SchemasResponse,
    summary="Available data schemas and semantic views",
    tags=["Metadata"],
)
def get_schemas() -> SchemasResponse:
    """
    Return metadata about semantic views and tables available for querying.

    Use this to discover what data dimensions and measures are available
    before submitting questions to the /ask endpoint.
    """
    return SchemasResponse(
        schemas=SEMANTIC_VIEWS,
        semantic_model="@CMS_STARS_DB.SCHEMA_RAW.CMS_SEMANTIC_MODELS_STAGE/medication_adherence.yaml",
    )
