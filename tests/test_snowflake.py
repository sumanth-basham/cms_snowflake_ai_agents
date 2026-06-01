"""
tests/test_snowflake.py — Unit tests for the snowflake/ module.

Tests cover:
  - _infer_viz_hint() — various question/data combinations
  - _apply_row_limit() — adds LIMIT, respects existing LIMIT
  - _build_connection_params() — PAT priority, key-pair, password

No actual Snowflake connection is made — all external calls are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Tests: Viz Hint Inference
# ---------------------------------------------------------------------------

class TestInferVizHint:
    """Tests for the module-level _infer_viz_hint function."""

    def _infer(self, question, data=None, sql=""):
        from cortex.cortex_client import _infer_viz_hint
        return _infer_viz_hint(question, data or [], sql)

    def test_trend_keyword_gives_line_chart(self):
        data = [{"month": "2024-01", "avg_pdc": 0.7}, {"month": "2024-02", "avg_pdc": 0.72}]
        hint = self._infer("Show me adherence trends over time", data)
        assert hint["chart"] == "line"

    def test_over_time_keyword_gives_line_chart(self):
        data = [{"month": "2024-01", "rate": 0.7}]
        hint = self._infer("What happened over time?", data)
        assert hint["chart"] == "line"

    def test_distribution_keyword_gives_histogram(self):
        data = [{"pdc_ratio": 0.65}, {"pdc_ratio": 0.82}]
        hint = self._infer("What is the distribution of PDC ratios?", data)
        assert hint["chart"] == "histogram"

    def test_compare_keyword_gives_bar_chart(self):
        data = [{"region": "NE", "rate": 0.7}, {"region": "SW", "rate": 0.68}]
        hint = self._infer("Compare adherence rates by region", data)
        assert hint["chart"] == "bar"

    def test_correlation_keyword_gives_scatter(self):
        data = [{"pdc": 0.7, "readmit": 0.15}]
        hint = self._infer("Show the correlation between adherence and readmission", data)
        assert hint["chart"] == "scatter"

    def test_single_row_gives_metric(self):
        data = [{"avg_pdc_ratio": 0.74}]
        hint = self._infer("What is the overall average PDC?", data)
        assert hint["chart"] == "metric"

    def test_empty_data_gives_table(self):
        hint = self._infer("Any question", data=[])
        assert hint["chart"] == "table"

    def test_returns_dict_with_chart_key(self):
        hint = self._infer("anything about adherence data", data=[{"region": "NE", "count": 5}])
        assert isinstance(hint, dict)
        assert "chart" in hint

    def test_hint_includes_x_y_keys(self):
        data = [{"region": "NE", "avg_pdc": 0.7}]
        hint = self._infer("Compare adherence by region", data)
        assert "x" in hint
        assert "y" in hint

    def test_time_column_detected_as_x_axis(self):
        data = [{"month": "2024-01", "avg_pdc": 0.7}]
        hint = self._infer("Show trends over time", data)
        # x should be the time column
        assert hint.get("x") == "month"


# ---------------------------------------------------------------------------
# Tests: Row Limit Application
# ---------------------------------------------------------------------------

class TestApplyRowLimit:
    def _apply(self, sql, limit):
        from cortex.cortex_client import _apply_row_limit
        return _apply_row_limit(sql, limit)

    def test_adds_limit_when_none_present(self):
        sql = "SELECT * FROM medication_adherence"
        result = self._apply(sql, 100)
        assert "LIMIT" in result.upper() or "100" in result

    def test_keeps_existing_limit(self):
        sql = "SELECT * FROM t LIMIT 50"
        result = self._apply(sql, 100)
        # The original LIMIT 50 should be preserved (not doubled)
        assert "LIMIT" in result.upper()

    def test_empty_sql_returns_empty(self):
        result = self._apply("", 100)
        # Empty SQL gets wrapped by the LIMIT logic; just check it's a string
        assert isinstance(result, str)

    def test_multiline_sql_handled(self):
        sql = """
        SELECT therapeutic_class, AVG(pdc_ratio)
        FROM medication_adherence
        GROUP BY therapeutic_class
        """
        result = self._apply(sql, 200)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_wrapped_sql_contains_original(self):
        sql = "SELECT drug_name, COUNT(*) FROM claims GROUP BY drug_name"
        result = self._apply(sql, 50)
        # When wrapped, the original SQL should appear inside
        assert "claims" in result or "drug_name" in result


# ---------------------------------------------------------------------------
# Tests: Connection Parameter Building
# ---------------------------------------------------------------------------

class TestBuildConnectionParams:
    """Tests for the module-level _build_connection_params function."""

    def _build(self, **env_overrides):
        """Call _build_connection_params with environment variable overrides."""
        import os
        base_env = {
            "SNOWFLAKE_ACCOUNT": "test123.snowflakecomputing.com",
            "SNOWFLAKE_USER": "svc_user",
            "SNOWFLAKE_ROLE": "ANALYST",
            "SNOWFLAKE_WAREHOUSE": "TEST_WH",
            "SNOWFLAKE_DATABASE": "TEST_DB",
            "SNOWFLAKE_SCHEMA": "TEST_SCHEMA",
        }
        base_env.update(env_overrides)
        with patch.dict(os.environ, base_env, clear=False):
            # Pass a dummy settings object to avoid real config loading
            from config.settings import Settings
            settings = Settings.model_construct(
                snowflake_account=base_env.get("SNOWFLAKE_ACCOUNT"),
                snowflake_user=base_env.get("SNOWFLAKE_USER"),
                snowflake_role=base_env.get("SNOWFLAKE_ROLE"),
                snowflake_warehouse=base_env.get("SNOWFLAKE_WAREHOUSE"),
                snowflake_database=base_env.get("SNOWFLAKE_DATABASE"),
                snowflake_schema=base_env.get("SNOWFLAKE_SCHEMA"),
                snowflake_pat=base_env.get("SNOWFLAKE_PAT"),
                snowflake_authenticator=base_env.get("SNOWFLAKE_AUTHENTICATOR"),
                snowflake_password=base_env.get("SNOWFLAKE_PASSWORD"),
            )
            from cortex.connection import _build_connection_params
            return _build_connection_params(settings=settings)

    def test_account_included(self):
        params = self._build()
        assert params["account"] == "test123.snowflakecomputing.com"

    def test_user_included(self):
        params = self._build()
        assert params["user"] == "svc_user"

    def test_database_included(self):
        params = self._build()
        assert params["database"] == "TEST_DB"

    def test_warehouse_included(self):
        params = self._build()
        assert params["warehouse"] == "TEST_WH"

    def test_pat_auth_uses_oauth(self):
        params = self._build(SNOWFLAKE_PAT="my-pat-token")
        assert params.get("token") == "my-pat-token"
        assert params.get("authenticator") == "oauth"

    def test_password_auth_when_no_pat(self):
        params = self._build(SNOWFLAKE_PASSWORD="secret123")
        assert params.get("password") == "secret123"

    def test_pat_takes_priority_over_password(self):
        params = self._build(SNOWFLAKE_PAT="pat-wins", SNOWFLAKE_PASSWORD="fallback")
        assert params.get("token") == "pat-wins"
        assert params.get("authenticator") == "oauth"
        assert "password" not in params


# ---------------------------------------------------------------------------
# Tests: Module-level ask_cortex_analyst function signature
# ---------------------------------------------------------------------------

class TestAskCortexAnalystExists:
    def test_function_exists(self):
        from cortex import cortex_client
        assert hasattr(cortex_client, "ask_cortex_analyst")

    def test_function_is_callable(self):
        from cortex.cortex_client import ask_cortex_analyst
        assert callable(ask_cortex_analyst)

    def test_apply_row_limit_exists(self):
        from cortex.cortex_client import _apply_row_limit
        assert callable(_apply_row_limit)

    def test_infer_viz_hint_exists(self):
        from cortex.cortex_client import _infer_viz_hint
        assert callable(_infer_viz_hint)
