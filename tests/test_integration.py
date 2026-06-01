"""
tests/test_integration.py — Integration-level unit tests.

Tests cover:
  - Claude tool definition schema validity
  - AdherenceAnalyst._call_cortex_api() with mocked httpx
  - Sample data loader (CSV target, no Snowflake)
  - Config settings loading and defaults
"""

import json
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Tests: Claude Tool Definition
# ---------------------------------------------------------------------------

class TestClaudeToolDefinition:
    def test_tool_definition_exists(self):
        from claude.tool_definition import CORTEX_AGENT_TOOL
        assert CORTEX_AGENT_TOOL is not None

    def test_tool_definition_has_name(self):
        from claude.tool_definition import CORTEX_AGENT_TOOL
        assert "name" in CORTEX_AGENT_TOOL
        assert CORTEX_AGENT_TOOL["name"] == "query_medication_adherence"

    def test_tool_definition_has_description(self):
        from claude.tool_definition import CORTEX_AGENT_TOOL
        assert "description" in CORTEX_AGENT_TOOL
        assert len(CORTEX_AGENT_TOOL["description"]) > 20

    def test_tool_definition_has_input_schema(self):
        from claude.tool_definition import CORTEX_AGENT_TOOL
        assert "input_schema" in CORTEX_AGENT_TOOL
        schema = CORTEX_AGENT_TOOL["input_schema"]
        assert schema.get("type") == "object"

    def test_tool_schema_has_question_property(self):
        from claude.tool_definition import CORTEX_AGENT_TOOL
        schema = CORTEX_AGENT_TOOL["input_schema"]
        assert "properties" in schema
        assert "question" in schema["properties"]

    def test_tool_schema_question_is_required(self):
        from claude.tool_definition import CORTEX_AGENT_TOOL
        schema = CORTEX_AGENT_TOOL["input_schema"]
        assert "required" in schema
        assert "question" in schema["required"]

    def test_tool_schema_is_json_serializable(self):
        from claude.tool_definition import CORTEX_AGENT_TOOL
        serialized = json.dumps(CORTEX_AGENT_TOOL)
        parsed = json.loads(serialized)
        assert parsed["name"] == CORTEX_AGENT_TOOL["name"]

    def test_system_prompt_exists(self):
        from claude.tool_definition import SYSTEM_PROMPT
        assert isinstance(SYSTEM_PROMPT, str)
        assert len(SYSTEM_PROMPT) > 100

    def test_example_prompts_is_list(self):
        from claude.tool_definition import EXAMPLE_PROMPTS
        assert isinstance(EXAMPLE_PROMPTS, list)
        assert len(EXAMPLE_PROMPTS) > 0

    def test_example_prompts_are_dicts_with_prompt_key(self):
        from claude.tool_definition import EXAMPLE_PROMPTS
        for item in EXAMPLE_PROMPTS:
            assert isinstance(item, dict)
            assert "prompt" in item
            assert isinstance(item["prompt"], str)
            assert len(item["prompt"]) > 10

    def test_tool_list_exists(self):
        from claude.tool_definition import TOOL_LIST
        assert isinstance(TOOL_LIST, list)
        assert len(TOOL_LIST) > 0


# ---------------------------------------------------------------------------
# Tests: AdherenceAnalyst
# ---------------------------------------------------------------------------

class TestAdherenceAnalyst:
    def test_class_exists(self):
        from claude.integration import AdherenceAnalyst
        assert AdherenceAnalyst is not None

    def test_initialization(self):
        from claude.integration import AdherenceAnalyst
        analyst = AdherenceAnalyst(
            api_key="test-anthropic-key",
            cortex_api_url="http://test:8000",
        )
        assert analyst is not None
        assert analyst.cortex_api_url == "http://test:8000"

    def test_trailing_slash_stripped_from_url(self):
        from claude.integration import AdherenceAnalyst
        analyst = AdherenceAnalyst(
            api_key="key",
            cortex_api_url="http://test:8000/",
        )
        assert not analyst.cortex_api_url.endswith("/")

    def test_has_ask_method(self):
        from claude.integration import AdherenceAnalyst
        analyst = AdherenceAnalyst(api_key="key", cortex_api_url="http://test:8000")
        assert hasattr(analyst, "ask")
        assert callable(analyst.ask)

    def test_has_call_cortex_api_method(self):
        from claude.integration import AdherenceAnalyst
        analyst = AdherenceAnalyst(api_key="key", cortex_api_url="http://test:8000")
        assert hasattr(analyst, "_call_cortex_api")

    def test_call_cortex_api_with_mocked_httpx(self):
        """Test that _call_cortex_api sends the correct JSON payload."""
        import httpx
        from claude.integration import AdherenceAnalyst

        expected = {
            "answer": "72% adherence for statins.",
            "sql": "SELECT 1",
            "data": [{"therapeutic_class": "STATIN", "avg_pdc": 0.72}],
            "viz_hint": {"chart": "bar", "x": "therapeutic_class", "y": "avg_pdc"},
            "trace_id": "t-test-1",
            "session_id": "s-test-1",
            "latency_ms": 300,
            "row_count": 1,
            "truncated": False,
            "cached": False,
        }

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = expected

        analyst = AdherenceAnalyst(api_key="key", cortex_api_url="http://test:8000")

        with patch("httpx.Client") as mock_client_cls:
            mock_client_instance = MagicMock()
            mock_client_cls.return_value.__enter__ = MagicMock(return_value=mock_client_instance)
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)
            mock_client_instance.post.return_value = mock_response

            result = analyst._call_cortex_api(
                "What is the adherence rate for statins?",
                max_rows=50,
            )
            assert result["answer"] == "72% adherence for statins."
            assert result["row_count"] == 1

    def test_call_cortex_api_returns_error_dict_on_failure(self):
        """When httpx raises, _call_cortex_api should return a graceful error dict."""
        import httpx
        from claude.integration import AdherenceAnalyst

        analyst = AdherenceAnalyst(api_key="key", cortex_api_url="http://test:8000")

        with patch("httpx.Client") as mock_client_cls:
            mock_client_cls.return_value.__enter__ = MagicMock(
                side_effect=httpx.ConnectError("Connection refused")
            )
            mock_client_cls.return_value.__exit__ = MagicMock(return_value=False)

            result = analyst._call_cortex_api("Will fail")
            # Should not raise; should return a graceful error dict
            assert "answer" in result
            assert "error" in result["answer"].lower() or "API error" in result["answer"]


# ---------------------------------------------------------------------------
# Tests: Sample Data Loader
# ---------------------------------------------------------------------------

class TestSampleDataLoader:
    def test_module_importable(self):
        import data.sample_data_loader as loader
        assert loader is not None

    def test_load_all_sample_data_function_exists(self):
        from data.sample_data_loader import load_all_sample_data
        assert callable(load_all_sample_data)

    def test_load_all_sample_data_csv_target(self, tmp_path):
        from data.sample_data_loader import load_all_sample_data
        load_all_sample_data(
            n_members=10,
            n_claims_per_member=5,
            seed=42,
            target="csv",
            output_dir=str(tmp_path),
        )
        csv_files = list(tmp_path.glob("*.csv"))
        assert len(csv_files) >= 2  # at least RAW_MEMBERS + RAW_PHARMACY_CLAIMS

    def test_csv_files_are_non_empty(self, tmp_path):
        from data.sample_data_loader import load_all_sample_data
        load_all_sample_data(n_members=5, n_claims_per_member=3, target="csv", output_dir=str(tmp_path))
        for f in tmp_path.glob("*.csv"):
            assert f.stat().st_size > 0, f"Empty file: {f}"

    def test_members_csv_has_expected_name(self, tmp_path):
        from data.sample_data_loader import load_all_sample_data
        load_all_sample_data(n_members=5, n_claims_per_member=3, target="csv", output_dir=str(tmp_path))
        csv_names = {f.name for f in tmp_path.glob("*.csv")}
        assert "raw_members.csv" in csv_names

    def test_invalid_target_raises(self):
        import tempfile
        from data.sample_data_loader import load_all_sample_data
        with pytest.raises(ValueError):
            load_all_sample_data(target="invalid", output_dir="/tmp")


# ---------------------------------------------------------------------------
# Tests: Config Settings
# ---------------------------------------------------------------------------

class TestConfigSettings:
    def test_settings_model_construct(self):
        from config.settings import Settings
        s = Settings.model_construct(
            snowflake_account="test.snowflakecomputing.com",
            snowflake_user="user",
            snowflake_role="ANALYST",
            snowflake_warehouse="WH",
            snowflake_database="DB",
            snowflake_schema="SCHEMA",
        )
        assert s.snowflake_account == "test.snowflakecomputing.com"

    def test_settings_has_max_result_rows(self):
        from config.settings import Settings
        s = Settings.model_construct(
            snowflake_account="x",
            snowflake_user="u",
            snowflake_role="r",
            snowflake_warehouse="w",
            snowflake_database="d",
            snowflake_schema="s",
        )
        assert hasattr(s, "max_result_rows")

    def test_settings_has_claude_model(self):
        from config.settings import Settings
        s = Settings.model_construct(
            snowflake_account="x",
            snowflake_user="u",
            snowflake_role="r",
            snowflake_warehouse="w",
            snowflake_database="d",
            snowflake_schema="s",
        )
        assert hasattr(s, "claude_model")

    def test_get_settings_is_cached(self):
        """get_settings() should return the same instance on repeated calls."""
        from config.settings import get_settings
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_has_cache_ttl(self):
        from config.settings import Settings
        s = Settings.model_construct(
            snowflake_account="x",
            snowflake_user="u",
            snowflake_role="r",
            snowflake_warehouse="w",
            snowflake_database="d",
            snowflake_schema="s",
        )
        assert hasattr(s, "cache_ttl_seconds")
