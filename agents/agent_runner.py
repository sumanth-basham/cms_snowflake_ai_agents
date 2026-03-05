"""
agent_runner.py — Run a Snowflake Cortex Agent and capture the response.

Maps to the agent interaction pattern in the reference repo.
Adapted for: Medicare Part D Patient Safety Stars use case

This module provides the core interface for interacting with Cortex Agents
via the Snowflake REST API or Snowpark session.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from python.config import AGENT_CONFIGS, DATABASE, SCHEMA_RAW, SnowflakeConnectionConfig
from python.db_helpers import execute_statement, get_connection

logger = logging.getLogger(__name__)


def run_agent(
    agent_name: str,
    user_message: str,
    session_id: Optional[str] = None,
    user_role: str = "analyst",
    config: Optional[SnowflakeConnectionConfig] = None,
) -> Dict[str, Any]:
    """
    Run a Cortex Agent query and return the structured response.

    This function uses the Snowflake COMPLETE_AGENT_RESPONSE function
    (or REST endpoint) to invoke the agent and capture its output.

    Args:
        agent_name: Name of the Cortex Agent (must be deployed in Snowflake)
        user_message: The user's question or request
        session_id: Optional session identifier for multi-turn conversations
        user_role: The role of the requesting user (for audit logging)
        config: Optional Snowflake connection config

    Returns:
        dict with keys: response_text, tools_invoked, evidence, confidence_level,
                        human_review_required, audit_id
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    audit_id = str(uuid.uuid4())
    start_time = datetime.now(timezone.utc)

    agent_config = AGENT_CONFIGS.get(agent_name)
    if not agent_config:
        raise ValueError(f"Unknown agent: {agent_name}. Available: {list(AGENT_CONFIGS.keys())}")

    logger.info("Running agent %s for session %s", agent_name, session_id)

    sql = f"""
SELECT SNOWFLAKE.CORTEX.COMPLETE_AGENT_RESPONSE(
  agent => '{DATABASE}.{SCHEMA_RAW}.{agent_name}',
  messages => PARSE_JSON(%s),
  session_id => %s
) AS agent_response
""".strip()

    messages_payload = json.dumps([{"role": "user", "content": user_message}])

    try:
        conn = get_connection(config)
        cursor = conn.cursor()
        cursor.execute(sql, (messages_payload, session_id))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
    except Exception as exc:
        logger.error("Agent query failed: %s", exc)
        raise

    end_time = datetime.now(timezone.utc)
    latency_ms = int((end_time - start_time).total_seconds() * 1000)

    if row:
        raw_response = row[0] if isinstance(row, (list, tuple)) else row
        if isinstance(raw_response, str):
            try:
                response_data = json.loads(raw_response)
            except json.JSONDecodeError:
                response_data = {"response_text": raw_response}
    else:
        response_data = {"response_text": "No response received."}

    response_text = response_data.get("response_text", str(response_data))
    confidence_level = response_data.get("confidence_level", "UNKNOWN")
    human_review_required = response_data.get("human_review_required", True)
    tools_invoked = response_data.get("tools_invoked", [])
    evidence = response_data.get("evidence", [])

    _write_audit_log(
        audit_id=audit_id,
        session_id=session_id,
        agent_name=agent_name,
        user_role=user_role,
        query_summary=user_message[:500],
        response_summary=response_text[:1000],
        tools_invoked=tools_invoked,
        retrieval_sources=evidence,
        confidence_level=confidence_level,
        human_review_required=human_review_required,
        latency_ms=latency_ms,
        config=config,
    )

    return {
        "audit_id": audit_id,
        "session_id": session_id,
        "agent_name": agent_name,
        "response_text": response_text,
        "tools_invoked": tools_invoked,
        "evidence": evidence,
        "confidence_level": confidence_level,
        "human_review_required": human_review_required,
        "latency_ms": latency_ms,
    }


def _write_audit_log(
    audit_id: str,
    session_id: str,
    agent_name: str,
    user_role: str,
    query_summary: str,
    response_summary: str,
    tools_invoked: List,
    retrieval_sources: List,
    confidence_level: str,
    human_review_required: bool,
    latency_ms: int,
    config: Optional[SnowflakeConnectionConfig] = None,
) -> None:
    """Write an entry to the AGENT_AUDIT_LOG table."""
    sql = f"""
INSERT INTO {DATABASE}.SCHEMA_GOLD.AGENT_AUDIT_LOG (
    audit_id, session_id, agent_name, user_role,
    query_timestamp, query_summary, response_summary,
    tools_invoked, retrieval_sources,
    confidence_level, human_review_required, latency_ms
) VALUES (
    %s, %s, %s, %s,
    CURRENT_TIMESTAMP(), %s, %s,
    PARSE_JSON(%s), PARSE_JSON(%s),
    %s, %s, %s
)
""".strip()

    try:
        execute_statement(
            sql,
            params=(
                audit_id,
                session_id,
                agent_name,
                user_role,
                query_summary,
                response_summary,
                json.dumps(tools_invoked),
                json.dumps(retrieval_sources),
                confidence_level,
                human_review_required,
                latency_ms,
            ),
            config=config,
        )
    except Exception as exc:
        logger.warning("Failed to write audit log: %s", exc)
