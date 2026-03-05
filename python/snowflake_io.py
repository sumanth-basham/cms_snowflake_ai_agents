"""
snowflake_io.py — Snowflake I/O utilities for uploading DataFrames.

Maps to: python/snowflake_io_utils.py in sfguide-agentic-ai-for-asset-management
"""

import logging
from typing import Optional

import pandas as pd

from python.config import SnowflakeConnectionConfig

logger = logging.getLogger(__name__)


def upload_dataframe(
    df: pd.DataFrame,
    target_table: str,
    config: Optional[SnowflakeConnectionConfig] = None,
    overwrite: bool = False,
) -> None:
    """
    Upload a pandas DataFrame to a Snowflake table using Snowpark.

    Args:
        df: pandas DataFrame to upload
        target_table: fully qualified table name (DB.SCHEMA.TABLE)
        config: optional Snowflake connection config
        overwrite: if True, recreate the table; if False, append
    """
    try:
        from snowflake.snowpark import Session
    except ImportError:
        logger.error("snowflake-snowpark-python is required for upload_dataframe")
        raise

    if config is None:
        config = SnowflakeConnectionConfig()

    session = Session.builder.configs(config.to_dict()).create()
    try:
        parts = target_table.split(".")
        if len(parts) == 3:
            db, schema, table = parts
        elif len(parts) == 2:
            schema, table = parts
            db = config.database
        else:
            table = parts[0]
            db = config.database
            schema = config.schema

        sp_df = session.create_dataframe(df)
        mode = "overwrite" if overwrite else "append"
        sp_df.write.save_as_table(
            [db, schema, table],
            mode=mode,
        )
        logger.info("Uploaded %d rows to %s", len(df), target_table)
    finally:
        session.close()
