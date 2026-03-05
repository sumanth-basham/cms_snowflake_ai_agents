"""
create_semantic_models.py — Uploads Cortex Analyst YAML semantic models to Snowflake stage.

Maps to: python/create_semantic_views.py in sfguide-agentic-ai-for-asset-management
Adapted for: Medicare Part D Patient Safety Stars use case
"""

import logging
from pathlib import Path

from python.config import DATABASE, SCHEMA_RAW, STAGE_SEMANTIC_MODELS
from python.db_helpers import execute_statement

logger = logging.getLogger(__name__)

SEMANTIC_MODELS_DIR = Path(__file__).parent.parent / "semantic_models"


def upload_semantic_models() -> None:
    """
    Upload all YAML semantic model files to the Snowflake stage
    for use with Cortex Analyst.
    """
    yaml_files = list(SEMANTIC_MODELS_DIR.glob("*.yaml"))
    if not yaml_files:
        logger.warning("No semantic model YAML files found in %s", SEMANTIC_MODELS_DIR)
        return

    for yaml_file in yaml_files:
        logger.info("Uploading semantic model: %s", yaml_file.name)
        sql = f"""
PUT file://{yaml_file} @{DATABASE}.{SCHEMA_RAW}.{STAGE_SEMANTIC_MODELS}
  OVERWRITE = TRUE
  AUTO_COMPRESS = FALSE
""".strip()
        execute_statement(sql)
        logger.info("Uploaded: %s", yaml_file.name)


def create_semantic_model_stage() -> None:
    """Ensure the Snowflake internal stage for semantic models exists."""
    sql = f"""
CREATE STAGE IF NOT EXISTS {DATABASE}.{SCHEMA_RAW}.{STAGE_SEMANTIC_MODELS}
  COMMENT = 'Cortex Analyst YAML semantic model files for CMS Stars'
""".strip()
    execute_statement(sql)
    logger.info("Stage ready: %s", STAGE_SEMANTIC_MODELS)
