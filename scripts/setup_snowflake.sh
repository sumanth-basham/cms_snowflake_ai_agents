#!/usr/bin/env bash
# scripts/setup_snowflake.sh — Initialize the CMS Stars Snowflake environment.
#
# This script runs the full Snowflake setup pipeline:
#   1. Create database, schemas, roles, stages, and all tables (sql/setup.sql)
#   2. Load synthetic sample data
#   3. Build Cortex Search indexes
#   4. Upload semantic model YAML files
#   5. Deploy Cortex Agents
#
# Prerequisites:
#   - Python 3.10+ installed
#   - pip install -r requirements.txt
#   - .env file configured (copy from deployment/.env.template)
#
# Usage:
#   bash scripts/setup_snowflake.sh [--step <step>]
#
#   Steps: setup | load_data | build_search | build_semantic | deploy_agents | all
#
# Examples:
#   bash scripts/setup_snowflake.sh                  # Run all steps
#   bash scripts/setup_snowflake.sh --step setup     # Run SQL setup only
#   bash scripts/setup_snowflake.sh --step all       # Explicit full run

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

# ---------------------------------------------------------------------------
# Load .env if present
# ---------------------------------------------------------------------------
if [[ -f ".env" ]]; then
    echo "[setup_snowflake] Loading .env …"
    set -o allexport
    # shellcheck source=/dev/null
    source .env
    set +o allexport
else
    echo "[setup_snowflake] WARNING: .env not found. Ensure Snowflake env vars are set."
fi

# ---------------------------------------------------------------------------
# Validate required environment variables
# ---------------------------------------------------------------------------
REQUIRED_VARS=("SNOWFLAKE_ACCOUNT" "SNOWFLAKE_USER")
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        echo "[setup_snowflake] ERROR: Required environment variable $var is not set."
        echo "  Copy deployment/.env.template to .env and fill in your credentials."
        exit 1
    fi
done

STEP="${2:-all}"

# Parse --step argument
while [[ $# -gt 0 ]]; do
    case "$1" in
        --step)
            STEP="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

echo "[setup_snowflake] Running step: ${STEP}"
echo "[setup_snowflake] Snowflake account: ${SNOWFLAKE_ACCOUNT}"
echo "[setup_snowflake] Snowflake user:    ${SNOWFLAKE_USER}"

# ---------------------------------------------------------------------------
# Run the pipeline step
# ---------------------------------------------------------------------------
python -m python.main --step "${STEP}"

echo "[setup_snowflake] Step '${STEP}' completed successfully."
