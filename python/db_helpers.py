"""
db_helpers.py — Snowflake connection and query helpers.

Maps to: python/db_helpers.py in sfguide-agentic-ai-for-asset-management
Adapted for: Medicare Part D Patient Safety Stars use case
"""

import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, List, Optional

import snowflake.connector
from snowflake.connector import DictCursor

from python.config import SnowflakeConnectionConfig

logger = logging.getLogger(__name__)


def get_connection(config: Optional[SnowflakeConnectionConfig] = None) -> snowflake.connector.SnowflakeConnection:
    """Create and return a Snowflake connection using environment-based config."""
    if config is None:
        config = SnowflakeConnectionConfig()
    return snowflake.connector.connect(**config.to_dict())


@contextmanager
def snowflake_cursor(
    config: Optional[SnowflakeConnectionConfig] = None,
    dict_cursor: bool = True,
) -> Generator:
    """Context manager for Snowflake cursor lifecycle."""
    conn = get_connection(config)
    try:
        cursor_class = DictCursor if dict_cursor else None
        cursor = conn.cursor(cursor_class) if cursor_class else conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()
    finally:
        conn.close()


def execute_query(
    sql: str,
    params: Optional[tuple] = None,
    config: Optional[SnowflakeConnectionConfig] = None,
) -> List[Dict[str, Any]]:
    """Execute a SQL query and return results as a list of dicts."""
    with snowflake_cursor(config) as cursor:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        return cursor.fetchall()


def execute_statement(
    sql: str,
    params: Optional[tuple] = None,
    config: Optional[SnowflakeConnectionConfig] = None,
) -> None:
    """Execute a SQL DML/DDL statement (no result expected)."""
    with snowflake_cursor(config) as cursor:
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)


def execute_script(
    sql_script: str,
    config: Optional[SnowflakeConnectionConfig] = None,
) -> None:
    """Execute a multi-statement SQL script, splitting on semicolons."""
    statements = [s.strip() for s in sql_script.split(";") if s.strip()]
    with snowflake_cursor(config, dict_cursor=False) as cursor:
        for stmt in statements:
            logger.debug("Executing: %s", stmt[:120])
            cursor.execute(stmt)


def execute_sql_file(
    file_path: str,
    config: Optional[SnowflakeConnectionConfig] = None,
) -> None:
    """Read a .sql file and execute it as a script."""
    with open(file_path, "r", encoding="utf-8") as f:
        sql_script = f.read()
    execute_script(sql_script, config)
