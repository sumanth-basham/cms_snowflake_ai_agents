#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Deploy CMS Stars AI Agents to Snowflake
#
# Usage:
#   ./deployment/deploy.sh                          # runs all steps
#   ./deployment/deploy.sh --step setup             # DDL only (runs setup.sql)
#   ./deployment/deploy.sh --step load_data         # load synthetic sample data
#   ./deployment/deploy.sh --step build_search      # build Cortex Search indexes
#   ./deployment/deploy.sh --step build_semantic    # upload semantic model YAMLs
#   ./deployment/deploy.sh --step deploy_agents     # deploy Cortex Agents
#   ./deployment/deploy.sh --step all               # run all steps in order
#
# Authentication (choose ONE — set in .env or as environment variables):
#
#   METHOD 1 — PAT (Programmatic Access Token)  [RECOMMENDED for CI/CD]
#     1. Snowflake UI → User Menu → My Profile → Security →
#        Programmatic Access Tokens → + New Token
#     2. Copy the token value.
#     3. Add to .env:  SNOWFLAKE_PAT=<token_value>
#     The Python connector will automatically use authenticator=oauth + token.
#
#   METHOD 2 — Key-pair (JWT)
#     Add to .env:  SNOWFLAKE_AUTHENTICATOR=snowflake_jwt
#                   SNOWFLAKE_PRIVATE_KEY_PATH=/path/to/rsa_key.p8
#
#   METHOD 3 — Password
#     Add to .env:  SNOWFLAKE_PASSWORD=<password>
#
# NOTE: Snowflake SQL (setup.sql) cannot call Python scripts directly.
# This script executes the Python pipeline steps that must follow the SQL setup.
# Steps run by python/main.py:
#   setup          -> executes sql/setup.sql via db_helpers.execute_sql_file()
#   load_data      -> python/generate_sample_data.py + python/snowflake_io.py
#   build_search   -> python/create_cortex_search.py
#   build_semantic -> python/create_semantic_models.py
#   deploy_agents  -> python/create_agents.py
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default to running all steps
STEP_ARGS="--step all"
if [ $# -gt 0 ]; then
  STEP_ARGS="$*"
fi

echo "=== CMS Snowflake AI Agents — Deploy ==="
echo "Project root: ${PROJECT_ROOT}"
echo "Step args:    ${STEP_ARGS}"

# Load environment variables from .env if present
if [ -f "${PROJECT_ROOT}/.env" ]; then
  set -a
  # shellcheck source=/dev/null
  source "${PROJECT_ROOT}/.env"
  set +a
  echo "Loaded environment from .env"
else
  echo "WARNING: .env not found. Relying on environment variables already set."
  echo "         Copy deployment/.env.template to .env and fill in credentials."
fi

# Validate required Snowflake credentials are present
: "${SNOWFLAKE_ACCOUNT:?SNOWFLAKE_ACCOUNT must be set}"
: "${SNOWFLAKE_USER:?SNOWFLAKE_USER must be set}"

# Report which auth method will be used (without printing secret values)
if [ -n "${SNOWFLAKE_PAT:-}" ]; then
  echo "Auth method:  PAT (Programmatic Access Token)"
elif [ "${SNOWFLAKE_AUTHENTICATOR:-}" = "externalbrowser" ]; then
  echo "Auth method:  externalbrowser (SSO)"
elif [ -n "${SNOWFLAKE_PRIVATE_KEY_PATH:-}" ] || [ "${SNOWFLAKE_AUTHENTICATOR:-}" = "snowflake_jwt" ]; then
  echo "Auth method:  key-pair (JWT)"
elif [ -n "${SNOWFLAKE_PASSWORD:-}" ]; then
  echo "Auth method:  password"
else
  echo "ERROR: No supported Snowflake authentication configured."
  echo "       Set one of: SNOWFLAKE_PAT, SNOWFLAKE_PRIVATE_KEY_PATH + SNOWFLAKE_AUTHENTICATOR=snowflake_jwt,"
  echo "       SNOWFLAKE_PASSWORD, or SNOWFLAKE_AUTHENTICATOR=externalbrowser."
  exit 1
fi

cd "${PROJECT_ROOT}"

# Run the requested pipeline step(s) via the Python CLI
python -m python.main ${STEP_ARGS}

echo "=== Deploy complete ==="
