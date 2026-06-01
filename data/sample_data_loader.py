"""
data/sample_data_loader.py — Load synthetic Medicare Part D medication adherence data.

Wraps python/generate_sample_data.py with an upload pipeline that can
target either a Snowflake instance or a local CSV dump (for offline dev).

Usage (upload to Snowflake):
    python -m data.sample_data_loader --target snowflake

Usage (dump to CSV for local testing):
    python -m data.sample_data_loader --target csv --output-dir /tmp/sample_data
"""

import argparse
import logging
import os
from pathlib import Path
from typing import Optional

import pandas as pd

logger = logging.getLogger(__name__)


def load_all_sample_data(
    n_members: int = 200,
    n_claims_per_member: int = 15,
    seed: int = 42,
    target: str = "csv",
    output_dir: Optional[str] = None,
) -> None:
    """
    Generate all synthetic datasets and load them to the target destination.

    Args:
        n_members: Number of synthetic member records to generate
        n_claims_per_member: Pharmacy claims per member
        seed: Random seed for reproducibility
        target: "csv" (write to local files) or "snowflake" (upload to Snowflake)
        output_dir: Output directory for CSV files (required when target="csv")
    """
    from python.generate_sample_data import (
        generate_drug_reference,
        generate_members,
        generate_mtm_interventions,
        generate_patient_safety_gaps,
        generate_pharmacy_claims,
    )

    logger.info("Generating synthetic sample data (n_members=%d, seed=%d)…", n_members, seed)

    members = generate_members(n=n_members, seed=seed)
    claims = generate_pharmacy_claims(members, n_per_member=n_claims_per_member, seed=seed)
    drug_ref = generate_drug_reference(seed=seed)
    mtm = generate_mtm_interventions(members, seed=seed)
    gaps = generate_patient_safety_gaps(members, seed=seed)

    datasets = {
        "RAW_MEMBERS": members,
        "RAW_PHARMACY_CLAIMS": claims,
        "RAW_DRUG_REFERENCE": drug_ref,
        "RAW_MTM_INTERVENTIONS": mtm,
        "RAW_PATIENT_SAFETY_GAPS": gaps,
    }

    logger.info("Generated %d members, %d claims", len(members), len(claims))

    if target == "csv":
        _dump_to_csv(datasets, output_dir or "data/samples")
    elif target == "snowflake":
        _upload_to_snowflake(datasets)
    else:
        raise ValueError(f"Unknown target: {target}. Use 'csv' or 'snowflake'.")


def _dump_to_csv(datasets: dict, output_dir: str) -> None:
    """Write datasets as CSV files to output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    for name, df in datasets.items():
        path = out / f"{name.lower()}.csv"
        df.to_csv(path, index=False)
        logger.info("Written: %s (%d rows)", path, len(df))
    logger.info("Sample data written to %s", output_dir)


def _upload_to_snowflake(datasets: dict) -> None:
    """Upload datasets to Snowflake RAW tables."""
    from python.snowflake_io import upload_dataframe
    from python.config import DATABASE, SCHEMA_RAW

    for name, df in datasets.items():
        table = f"{DATABASE}.{SCHEMA_RAW}.{name}"
        logger.info("Uploading %s (%d rows) to %s…", name, len(df), table)
        upload_dataframe(df, table)
    logger.info("All sample data uploaded to Snowflake")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(
        description="Load synthetic Medicare Part D sample data"
    )
    parser.add_argument(
        "--target",
        choices=["csv", "snowflake"],
        default="csv",
        help="Load destination: csv (local) or snowflake",
    )
    parser.add_argument(
        "--output-dir",
        default="data/samples",
        help="Output directory for CSV files (default: data/samples)",
    )
    parser.add_argument(
        "--n-members", type=int, default=200, help="Number of synthetic members"
    )
    parser.add_argument(
        "--n-claims", type=int, default=15, help="Pharmacy claims per member"
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed")
    args = parser.parse_args()

    load_all_sample_data(
        n_members=args.n_members,
        n_claims_per_member=args.n_claims,
        seed=args.seed,
        target=args.target,
        output_dir=args.output_dir,
    )
