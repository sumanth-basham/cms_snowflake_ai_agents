"""
measure_tools.py — Custom tools for the Measure Interpretation Agent.

These tools are registered as Snowpark UDFs or stored procedures
that Cortex Agents can call during tool use.

Maps to the custom tools pattern in the reference repo.
"""

import logging
from typing import Any, Dict, List, Optional

from python.config import DATABASE, SCHEMA_CURATED
from python.db_helpers import execute_query

logger = logging.getLogger(__name__)


def get_measure_definition(
    measure_code: str,
    measurement_year: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Retrieve measure definition metadata from MEASURE_DEFINITIONS table.

    Args:
        measure_code: Measure code (e.g. "HRM_V1", "SUPD_V1")
        measurement_year: Optional year filter (defaults to latest version)

    Returns:
        Measure definition dict with logic summary and spec status
    """
    if measurement_year:
        sql = f"""
SELECT
    measure_code, measure_version, measure_name, measure_domain,
    description, denominator_logic_summary, numerator_logic_summary,
    exclusion_logic_summary, measurement_year, pdc_threshold,
    star_rating_direction, spec_confirmed, spec_source, assumptions
FROM {DATABASE}.{SCHEMA_CURATED}.MEASURE_DEFINITIONS
WHERE measure_code = %s
  AND measurement_year = %s
ORDER BY effective_start_date DESC
LIMIT 1
"""
        rows = execute_query(sql, params=(measure_code, measurement_year))
    else:
        sql = f"""
SELECT
    measure_code, measure_version, measure_name, measure_domain,
    description, denominator_logic_summary, numerator_logic_summary,
    exclusion_logic_summary, measurement_year, pdc_threshold,
    star_rating_direction, spec_confirmed, spec_source, assumptions
FROM {DATABASE}.{SCHEMA_CURATED}.MEASURE_DEFINITIONS
WHERE measure_code = %s
ORDER BY measurement_year DESC, effective_start_date DESC
LIMIT 1
"""
        rows = execute_query(sql, params=(measure_code,))

    if not rows:
        return {
            "found": False,
            "measure_code": measure_code,
            "error": f"Measure definition not found for {measure_code}. "
                     "Please check the measure code and verify against official CMS/PQA specifications.",
        }

    row = rows[0]
    return {
        "found": True,
        "measure_code": row.get("MEASURE_CODE"),
        "measure_version": row.get("MEASURE_VERSION"),
        "measure_name": row.get("MEASURE_NAME"),
        "measure_domain": row.get("MEASURE_DOMAIN"),
        "description": row.get("DESCRIPTION"),
        "denominator_logic_summary": row.get("DENOMINATOR_LOGIC_SUMMARY"),
        "numerator_logic_summary": row.get("NUMERATOR_LOGIC_SUMMARY"),
        "exclusion_logic_summary": row.get("EXCLUSION_LOGIC_SUMMARY"),
        "measurement_year": row.get("MEASUREMENT_YEAR"),
        "pdc_threshold": row.get("PDC_THRESHOLD"),
        "star_rating_direction": row.get("STAR_RATING_DIRECTION"),
        "spec_confirmed": row.get("SPEC_CONFIRMED"),
        "spec_source": row.get("SPEC_SOURCE"),
        "assumptions": row.get("ASSUMPTIONS"),
    }


def get_measure_versions(measure_code: str) -> List[Dict[str, Any]]:
    """
    Retrieve all versions of a measure definition, showing year-over-year changes.

    Args:
        measure_code: Measure code to look up

    Returns:
        List of version records ordered by measurement year
    """
    sql = f"""
SELECT
    measure_code, measure_version, measure_name,
    measurement_year, effective_start_date, effective_end_date,
    spec_confirmed, spec_source, assumptions
FROM {DATABASE}.{SCHEMA_CURATED}.MEASURE_DEFINITIONS
WHERE measure_code = %s
ORDER BY measurement_year ASC, effective_start_date ASC
"""
    rows = execute_query(sql, params=(measure_code,))
    if not rows:
        return []
    return [
        {
            "measure_code": r.get("MEASURE_CODE"),
            "measure_version": r.get("MEASURE_VERSION"),
            "measure_name": r.get("MEASURE_NAME"),
            "measurement_year": r.get("MEASUREMENT_YEAR"),
            "effective_start_date": str(r.get("EFFECTIVE_START_DATE", "")),
            "effective_end_date": str(r.get("EFFECTIVE_END_DATE", "")),
            "spec_confirmed": r.get("SPEC_CONFIRMED"),
        }
        for r in rows
    ]
