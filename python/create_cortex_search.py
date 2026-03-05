"""
create_cortex_search.py — Creates Snowflake Cortex Search services for CMS Stars.

Maps to: python/create_cortex_search.py in sfguide-agentic-ai-for-asset-management
Adapted for: Medicare Part D Patient Safety Stars use case

Cortex Search indexes power the retrieval-augmented generation (RAG) component
of each agent, allowing agents to ground responses in actual CMS/PQA documents,
clinical guidance, and policy materials.
"""

import logging
from typing import Dict, List

from python.config import (
    DATABASE,
    SCHEMA_RAW,
    SEARCH_SERVICE_CLINICAL_GUIDANCE,
    SEARCH_SERVICE_MEASURE_DOCS,
    SEARCH_SERVICE_POLICY_DOCS,
    SEARCH_SERVICE_SAFETY_BULLETINS,
    STAGE_DOCUMENTS,
    WAREHOUSE,
)
from python.db_helpers import execute_statement

logger = logging.getLogger(__name__)


CORTEX_SEARCH_SERVICES: Dict[str, Dict] = {
    SEARCH_SERVICE_MEASURE_DOCS: {
        "description": "CMS/PQA measure specification documents",
        "source_table": f"{DATABASE}.{SCHEMA_RAW}.RAW_DOCUMENT_CHUNKS",
        "search_column": "chunk_text",
        "attribute_columns": ["doc_id", "doc_title", "doc_type", "measure_code", "effective_year"],
        "source_filter": "doc_type = 'MEASURE_SPEC'",
        "target_lag": "1 day",
    },
    SEARCH_SERVICE_POLICY_DOCS: {
        "description": "Plan policy and operational policy documents",
        "source_table": f"{DATABASE}.{SCHEMA_RAW}.RAW_DOCUMENT_CHUNKS",
        "search_column": "chunk_text",
        "attribute_columns": ["doc_id", "doc_title", "doc_type", "contract_id", "effective_year"],
        "source_filter": "doc_type = 'POLICY'",
        "target_lag": "1 day",
    },
    SEARCH_SERVICE_CLINICAL_GUIDANCE: {
        "description": "Clinical guidance, treatment guidelines, and pharmacy protocols",
        "source_table": f"{DATABASE}.{SCHEMA_RAW}.RAW_DOCUMENT_CHUNKS",
        "search_column": "chunk_text",
        "attribute_columns": ["doc_id", "doc_title", "doc_type", "therapeutic_class"],
        "source_filter": "doc_type = 'CLINICAL_GUIDANCE'",
        "target_lag": "1 day",
    },
    SEARCH_SERVICE_SAFETY_BULLETINS: {
        "description": "Medication safety bulletins and alerts",
        "source_table": f"{DATABASE}.{SCHEMA_RAW}.RAW_DOCUMENT_CHUNKS",
        "search_column": "chunk_text",
        "attribute_columns": ["doc_id", "doc_title", "doc_type", "severity_level"],
        "source_filter": "doc_type = 'SAFETY_BULLETIN'",
        "target_lag": "1 day",
    },
}


def build_create_search_sql(service_name: str, config: Dict) -> str:
    """
    Generate the CREATE CORTEX SEARCH SERVICE SQL statement.
    """
    attributes = ", ".join(config["attribute_columns"])
    filter_clause = f"\n    WHERE {config['source_filter']}" if config.get("source_filter") else ""
    return f"""
CREATE OR REPLACE CORTEX SEARCH SERVICE {DATABASE}.{SCHEMA_RAW}.{service_name}
  ON {config['search_column']}
  ATTRIBUTES {attributes}
  WAREHOUSE = {WAREHOUSE}
  TARGET_LAG = '{config['target_lag']}'
  COMMENT = '{config['description']}'
  AS (
    SELECT *
    FROM {config['source_table']}{filter_clause}
  )
""".strip()


def create_all_search_services() -> None:
    """Create all Cortex Search services defined in CORTEX_SEARCH_SERVICES."""
    for service_name, config in CORTEX_SEARCH_SERVICES.items():
        logger.info("Creating Cortex Search service: %s", service_name)
        sql = build_create_search_sql(service_name, config)
        try:
            execute_statement(sql)
            logger.info("Created: %s", service_name)
        except Exception as exc:
            logger.error("Failed to create %s: %s", service_name, exc)
            raise


def get_search_service_names() -> List[str]:
    """Return all defined search service names."""
    return list(CORTEX_SEARCH_SERVICES.keys())
