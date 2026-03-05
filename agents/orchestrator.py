"""
orchestrator.py — Multi-agent orchestrator for CMS Stars queries.

Routes user queries to the appropriate specialized agent based on query intent.
Maps to the orchestration pattern in the reference repo.

Design: Single orchestrated agent with multiple specialized sub-agents.
This is the recommended MVP design for CMS Stars use case.
"""

import logging
from typing import Any, Dict, Optional

from python.config import SnowflakeConnectionConfig
from agents.routing import route_query  # noqa: F401 — re-exported for convenience
from agents.agent_runner import run_agent

logger = logging.getLogger(__name__)


def orchestrate(
    user_message: str,
    session_id: Optional[str] = None,
    user_role: str = "analyst",
    config: Optional[SnowflakeConnectionConfig] = None,
    force_agent: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Orchestrate a user query through the appropriate CMS Stars agent.

    Args:
        user_message: The user's natural language query
        session_id: Optional session ID for conversation context
        user_role: User's role (for audit and access control)
        config: Optional Snowflake connection config
        force_agent: Override routing and use a specific agent

    Returns:
        Agent response dict (see agent_runner.run_agent)
    """
    if force_agent:
        target_agent = force_agent
        logger.info("Agent override: %s", target_agent)
    else:
        target_agent = route_query(user_message)

    response = run_agent(
        agent_name=target_agent,
        user_message=user_message,
        session_id=session_id,
        user_role=user_role,
        config=config,
    )
    response["routed_to"] = target_agent
    return response
