"""
main.py — CLI entry point for CMS Snowflake AI Agents setup pipeline.

Maps to: python/main.py in sfguide-agentic-ai-for-asset-management
Adapted for: Medicare Part D Patient Safety Stars use case

Usage:
    python -m python.main --step setup
    python -m python.main --step load_data
    python -m python.main --step build_search
    python -m python.main --step build_semantic
    python -m python.main --step deploy_agents
    python -m python.main --step all
"""

import argparse
import logging
import sys
from pathlib import Path

from python.logging_utils import setup_logging

logger = logging.getLogger(__name__)

SQL_DIR = Path(__file__).parent.parent / "sql"


def run_setup() -> None:
    """Execute Snowflake setup SQL: database, schemas, tables."""
    from python.db_helpers import execute_sql_file
    setup_sql = SQL_DIR / "setup.sql"
    logger.info("Running setup SQL: %s", setup_sql)
    execute_sql_file(str(setup_sql))
    logger.info("Setup complete")


def run_load_data() -> None:
    """Generate and load synthetic sample data into Snowflake."""
    import pandas as pd
    from python.generate_sample_data import (
        generate_drug_reference,
        generate_members,
        generate_mtm_interventions,
        generate_patient_safety_gaps,
        generate_pharmacy_claims,
    )
    from python.snowflake_io import upload_dataframe
    from python.config import DATABASE, SCHEMA_RAW

    logger.info("Generating synthetic sample data...")
    members = generate_members(n=200)
    claims = generate_pharmacy_claims(members)
    drug_ref = generate_drug_reference()
    mtm = generate_mtm_interventions(members)
    gaps = generate_patient_safety_gaps(members)

    logger.info("Uploading to Snowflake...")
    upload_dataframe(members, f"{DATABASE}.{SCHEMA_RAW}.RAW_MEMBERS")
    upload_dataframe(claims, f"{DATABASE}.{SCHEMA_RAW}.RAW_PHARMACY_CLAIMS")
    upload_dataframe(drug_ref, f"{DATABASE}.{SCHEMA_RAW}.RAW_DRUG_REFERENCE")
    upload_dataframe(mtm, f"{DATABASE}.{SCHEMA_RAW}.RAW_MTM_INTERVENTIONS")
    upload_dataframe(gaps, f"{DATABASE}.{SCHEMA_RAW}.RAW_PATIENT_SAFETY_GAPS")
    logger.info("Sample data loaded")


def run_build_search() -> None:
    """Create Cortex Search services."""
    from python.create_cortex_search import create_all_search_services
    create_all_search_services()


def run_build_semantic() -> None:
    """Upload semantic model YAML files and create stage."""
    from python.create_semantic_models import create_semantic_model_stage, upload_semantic_models
    create_semantic_model_stage()
    upload_semantic_models()


def run_deploy_agents() -> None:
    """Deploy all Cortex Agents."""
    from python.create_agents import create_all_agents
    create_all_agents()


def run_all() -> None:
    """Run the complete build pipeline."""
    run_setup()
    run_load_data()
    run_build_semantic()
    run_build_search()
    run_deploy_agents()


STEPS = {
    "setup": run_setup,
    "load_data": run_load_data,
    "build_search": run_build_search,
    "build_semantic": run_build_semantic,
    "deploy_agents": run_deploy_agents,
    "all": run_all,
}


def main() -> None:
    setup_logging()
    parser = argparse.ArgumentParser(
        description="CMS Snowflake AI Agents — Build Pipeline"
    )
    parser.add_argument(
        "--step",
        choices=list(STEPS.keys()),
        default="all",
        help="Pipeline step to execute (default: all)",
    )
    args = parser.parse_args()
    step_fn = STEPS[args.step]
    logger.info("Running step: %s", args.step)
    step_fn()


if __name__ == "__main__":
    main()
