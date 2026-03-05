#!/usr/bin/env bash
# =============================================================================
# deploy.sh — Deploy CMS Stars AI Agents to Snowflake
#
# Usage: ./deployment/deploy.sh [--step all|setup|load_data|build_search|build_semantic|deploy_agents]
# =============================================================================

set -euo pipefail

STEP="${1:---step all}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "=== CMS Snowflake AI Agents — Deploy ==="
echo "Project root: ${PROJECT_ROOT}"
echo "Step: ${STEP}"

# Load environment
if [ -f "${PROJECT_ROOT}/.env" ]; then
  set -a
  source "${PROJECT_ROOT}/.env"
  set +a
  echo "Loaded environment from .env"
else
  echo "WARNING: .env not found. Using environment variables."
fi

cd "${PROJECT_ROOT}"

# Run pipeline step
python -m python.main ${STEP}

echo "=== Deploy complete ==="
