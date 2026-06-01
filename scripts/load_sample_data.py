"""
scripts/load_sample_data.py — CLI entry point for loading synthetic Medicare Part D data.

Generates and loads synthetic (non-PHI) sample data for development and testing.

Usage:
    # Load to local CSV files (no Snowflake needed)
    python scripts/load_sample_data.py --target csv --output-dir data/samples

    # Upload directly to Snowflake
    python scripts/load_sample_data.py --target snowflake

    # Customize dataset size
    python scripts/load_sample_data.py --n-members 500 --n-claims 20 --seed 42
"""

import sys
from pathlib import Path

# Ensure repository root is on the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.sample_data_loader import load_all_sample_data  # noqa: E402
import argparse
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load synthetic Medicare Part D medication adherence sample data"
    )
    parser.add_argument(
        "--target",
        choices=["csv", "snowflake"],
        default="csv",
        help="Destination: 'csv' writes local CSV files; 'snowflake' uploads to Snowflake",
    )
    parser.add_argument(
        "--output-dir",
        default="data/samples",
        help="Output directory when --target csv (default: data/samples)",
    )
    parser.add_argument(
        "--n-members",
        type=int,
        default=200,
        help="Number of synthetic member records (default: 200)",
    )
    parser.add_argument(
        "--n-claims",
        type=int,
        default=15,
        help="Pharmacy claims per member (default: 15)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    args = parser.parse_args()

    load_all_sample_data(
        n_members=args.n_members,
        n_claims_per_member=args.n_claims,
        seed=args.seed,
        target=args.target,
        output_dir=args.output_dir,
    )
