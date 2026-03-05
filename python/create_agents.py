"""
create_agents.py — Creates Snowflake Cortex Agents for CMS Stars.

Maps to: python/create_agents.py in sfguide-agentic-ai-for-asset-management
Adapted for: Medicare Part D Patient Safety Stars use case

Each agent is created as a Snowflake Cortex Agent object with:
  - System prompt (loaded from prompts/)
  - Tool definitions (Cortex Search services + custom tools)
  - Semantic model references for Cortex Analyst

IMPORTANT: Agent instructions must be reviewed by clinical and compliance SMEs
before production deployment.
"""

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from python.config import (
    AGENT_AUDIT_EXPLAINABILITY,
    AGENT_CONFIGS,
    AGENT_GAP_DETECTION,
    AGENT_MEASURE_INTERPRETATION,
    AGENT_ORCHESTRATOR,
    AGENT_OUTREACH_RECOMMENDATION,
    AGENT_STARS_PERFORMANCE,
    DATABASE,
    SCHEMA_RAW,
)
from python.db_helpers import execute_statement

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def _load_prompt(agent_name: str) -> str:
    """Load the system prompt for an agent from the prompts directory."""
    prompt_file = PROMPTS_DIR / f"{agent_name.lower()}.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    logger.warning("Prompt file not found for %s, using empty prompt", agent_name)
    return f"You are the {agent_name}."


def _build_tools_json(agent_name: str, config) -> str:
    """Build the TOOLS JSON block for a Cortex Agent."""
    tools = []

    for search_svc in config.search_services:
        tools.append(
            {
                "tool_type": "CORTEX_SEARCH",
                "name": search_svc,
                "spec": {
                    "service": f"{DATABASE}.{SCHEMA_RAW}.{search_svc}",
                    "max_results": 5,
                },
            }
        )

    for semantic_model in config.semantic_models:
        tools.append(
            {
                "tool_type": "CORTEX_ANALYST_TEXT_TO_SQL",
                "name": semantic_model.replace(".yaml", "").upper(),
                "spec": {
                    "semantic_model_file": f"@{DATABASE}.{SCHEMA_RAW}.CMS_SEMANTIC_MODELS_STAGE/{semantic_model}",
                },
            }
        )

    for tool_name in config.custom_tools:
        tools.append(
            {
                "tool_type": "SQL",
                "name": tool_name,
                "spec": {
                    "procedure": f"{DATABASE}.{SCHEMA_RAW}.{tool_name.upper()}",
                },
            }
        )

    import json
    return json.dumps(tools, indent=2)


def create_agent(agent_name: str) -> None:
    """Create a single Cortex Agent in Snowflake."""
    config = AGENT_CONFIGS.get(agent_name)
    if not config:
        raise ValueError(f"No config found for agent: {agent_name}")

    prompt = _load_prompt(agent_name)
    prompt_escaped = prompt.replace("'", "''")

    sql = f"""
CREATE OR REPLACE CORTEX AGENT {DATABASE}.{SCHEMA_RAW}.{agent_name}
  MODEL = '{config.cortex_model}'
  COMMENT = '{config.description}'
  AS
    SYSTEM_PROMPT = '{prompt_escaped}'
""".strip()

    logger.info("Creating agent: %s", agent_name)
    execute_statement(sql)
    logger.info("Created agent: %s", agent_name)


def create_all_agents() -> None:
    """Create all Cortex Agents defined in AGENT_CONFIGS."""
    for agent_name in AGENT_CONFIGS:
        create_agent(agent_name)


def get_agent_names() -> List[str]:
    """Return all defined agent names."""
    return list(AGENT_CONFIGS.keys())
