"""
build_ai.py — High-level orchestration: build all AI components for CMS Stars.

Maps to: python/build_ai.py in sfguide-agentic-ai-for-asset-management
Adapted for: Medicare Part D Patient Safety Stars use case
"""

import logging

from python.create_agents import create_all_agents
from python.create_cortex_search import create_all_search_services
from python.create_semantic_models import create_semantic_model_stage, upload_semantic_models
from python.logging_utils import setup_logging

logger = logging.getLogger(__name__)


def build_all() -> None:
    """
    Build all AI components:
    1. Create semantic model stage and upload YAML files
    2. Create Cortex Search services
    3. Create Cortex Agents
    """
    logger.info("=== CMS Snowflake AI Agents — Build All ===")

    logger.info("Step 1: Preparing semantic model stage")
    create_semantic_model_stage()
    upload_semantic_models()

    logger.info("Step 2: Creating Cortex Search services")
    create_all_search_services()

    logger.info("Step 3: Creating Cortex Agents")
    create_all_agents()

    logger.info("=== Build complete ===")


if __name__ == "__main__":
    setup_logging()
    build_all()
