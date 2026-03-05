"""
performance_tools.py — Custom tools for the Stars Performance Analytics Agent.

These tools query contract/plan level aggregated performance data.
All outputs are at contract or segment level — never individual member level.
"""

import logging
from typing import Any, Dict, List, Optional

from python.config import DATABASE, SCHEMA_GOLD
from python.db_helpers import execute_query

logger = logging.getLogger(__name__)

SMALL_CELL_THRESHOLD = 11


def query_contract_performance(
    contract_id: str,
    measurement_year: int = 2024,
    measure_code: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Retrieve contract-level Stars measure performance.

    Args:
        contract_id: CMS contract ID (or "ALL" for all contracts)
        measurement_year: Stars measurement year
        measure_code: Optional specific measure code

    Returns:
        Contract performance summary with measure rates
    """
    contract_filter = "AND contract_id = %s" if contract_id != "ALL" else ""
    measure_filter = "AND measure_code = %s" if measure_code else ""

    params: list = [measurement_year]
    if contract_id != "ALL":
        params.append(contract_id)
    if measure_code:
        params.append(measure_code)

    sql = f"""
SELECT
    contract_id,
    measure_code,
    measurement_year,
    denominator_count,
    numerator_count,
    excluded_count,
    measure_rate,
    estimated_star_rating
FROM {DATABASE}.{SCHEMA_GOLD}.CONTRACT_PERFORMANCE_SUMMARY
WHERE measurement_year = %s
  {contract_filter}
  {measure_filter}
ORDER BY contract_id, measure_code
"""
    rows = execute_query(sql, params=tuple(params))

    results = []
    for r in rows:
        denom = r.get("DENOMINATOR_COUNT", 0) or 0
        if denom < SMALL_CELL_THRESHOLD:
            continue
        results.append(
            {
                "contract_id": r.get("CONTRACT_ID"),
                "measure_code": r.get("MEASURE_CODE"),
                "measurement_year": r.get("MEASUREMENT_YEAR"),
                "denominator_count": denom,
                "numerator_count": r.get("NUMERATOR_COUNT"),
                "excluded_count": r.get("EXCLUDED_COUNT"),
                "measure_rate": r.get("MEASURE_RATE"),
                "estimated_star_rating": r.get("ESTIMATED_STAR_RATING"),
            }
        )

    return {
        "query_scope": {
            "contract_id": contract_id,
            "measure_code": measure_code,
            "measurement_year": measurement_year,
        },
        "result_count": len(results),
        "performance_data": results,
        "caveats": [
            "Estimated star ratings require validation against official CMS cut point tables.",
            "Contracts with fewer than 11 denominator members are suppressed.",
        ],
    }


def query_stars_trends(
    contract_id: str,
    measure_code: str,
    start_year: int = 2022,
    end_year: int = 2024,
) -> Dict[str, Any]:
    """
    Retrieve year-over-year Stars measure trend for a contract.

    Args:
        contract_id: CMS contract ID
        measure_code: Stars measure code
        start_year: Start of trend window
        end_year: End of trend window

    Returns:
        Trend data with rates by year
    """
    sql = f"""
SELECT
    measurement_year,
    denominator_count,
    numerator_count,
    measure_rate,
    estimated_star_rating
FROM {DATABASE}.{SCHEMA_GOLD}.CONTRACT_PERFORMANCE_SUMMARY
WHERE contract_id = %s
  AND measure_code = %s
  AND measurement_year BETWEEN %s AND %s
ORDER BY measurement_year ASC
"""
    rows = execute_query(sql, params=(contract_id, measure_code, start_year, end_year))

    trend = []
    prior_rate = None
    for r in rows:
        rate = r.get("MEASURE_RATE")
        yoy_change = round(rate - prior_rate, 4) if prior_rate is not None and rate is not None else None
        trend.append(
            {
                "year": r.get("MEASUREMENT_YEAR"),
                "denominator": r.get("DENOMINATOR_COUNT"),
                "numerator": r.get("NUMERATOR_COUNT"),
                "rate": rate,
                "yoy_change": yoy_change,
                "estimated_star_rating": r.get("ESTIMATED_STAR_RATING"),
            }
        )
        prior_rate = rate

    return {
        "contract_id": contract_id,
        "measure_code": measure_code,
        "trend_years": f"{start_year}-{end_year}",
        "trend_data": trend,
        "caveats": [
            "Year-over-year comparisons may not be valid if measure specifications changed between years.",
            "Estimated star ratings are NOT official CMS star ratings.",
        ],
    }
