"""
test_config.py — Unit tests for configuration module
"""

import pytest

from python.config import (
    AGENT_CONFIGS,
    AGENT_MEASURE_INTERPRETATION,
    AGENT_GAP_DETECTION,
    AGENT_OUTREACH_RECOMMENDATION,
    AGENT_STARS_PERFORMANCE,
    AGENT_AUDIT_EXPLAINABILITY,
    ALL_MEASURE_DOMAINS,
    DATABASE,
    RISK_SCORE_HIGH,
    RISK_SCORE_MEDIUM,
    RISK_SCORE_LOW,
    SCHEMA_GOLD,
    SCHEMA_RAW,
    SCHEMA_CURATED,
    SnowflakeConnectionConfig,
)


class TestAgentConfigs:
    def test_all_agents_defined(self):
        expected_agents = [
            AGENT_MEASURE_INTERPRETATION,
            AGENT_GAP_DETECTION,
            AGENT_OUTREACH_RECOMMENDATION,
            AGENT_STARS_PERFORMANCE,
            AGENT_AUDIT_EXPLAINABILITY,
        ]
        for agent in expected_agents:
            assert agent in AGENT_CONFIGS, f"Missing agent config: {agent}"

    def test_each_agent_has_description(self):
        for name, config in AGENT_CONFIGS.items():
            assert config.description, f"Agent {name} missing description"

    def test_each_agent_has_model(self):
        for name, config in AGENT_CONFIGS.items():
            assert config.cortex_model, f"Agent {name} missing cortex_model"

    def test_measure_interpretation_has_search(self):
        config = AGENT_CONFIGS[AGENT_MEASURE_INTERPRETATION]
        assert len(config.search_services) > 0

    def test_gap_detection_has_tools(self):
        config = AGENT_CONFIGS[AGENT_GAP_DETECTION]
        assert len(config.custom_tools) > 0

    def test_stars_performance_has_semantic_models(self):
        config = AGENT_CONFIGS[AGENT_STARS_PERFORMANCE]
        assert len(config.semantic_models) > 0


class TestMeasureDomains:
    def test_all_domains_defined(self):
        assert "HRM" in ALL_MEASURE_DOMAINS
        assert "PDC" in ALL_MEASURE_DOMAINS
        assert "SUPD" in ALL_MEASURE_DOMAINS
        assert "MTM" in ALL_MEASURE_DOMAINS

    def test_at_least_five_domains(self):
        assert len(ALL_MEASURE_DOMAINS) >= 5


class TestRiskThresholds:
    def test_high_above_medium(self):
        assert RISK_SCORE_HIGH > RISK_SCORE_MEDIUM

    def test_medium_above_low(self):
        assert RISK_SCORE_MEDIUM > RISK_SCORE_LOW

    def test_thresholds_in_range(self):
        assert 0.0 <= RISK_SCORE_LOW <= 1.0
        assert 0.0 <= RISK_SCORE_MEDIUM <= 1.0
        assert 0.0 <= RISK_SCORE_HIGH <= 1.0


class TestSnowflakeConnectionConfig:
    def test_defaults(self):
        config = SnowflakeConnectionConfig(
            account="test", user="test_user", password="test_pass"
        )
        assert config.database == DATABASE

    def test_to_dict_excludes_none_authenticator(self):
        config = SnowflakeConnectionConfig(
            account="test", user="test_user", password="pass", authenticator=None
        )
        d = config.to_dict()
        assert "authenticator" not in d
        assert "password" in d

    def test_to_dict_uses_authenticator_when_set(self):
        config = SnowflakeConnectionConfig(
            account="test", user="test_user", authenticator="externalbrowser"
        )
        d = config.to_dict()
        assert d["authenticator"] == "externalbrowser"


class TestSchemaConstants:
    def test_schema_names_defined(self):
        assert SCHEMA_RAW == "SCHEMA_RAW"
        assert SCHEMA_CURATED == "SCHEMA_CURATED"
        assert SCHEMA_GOLD == "SCHEMA_GOLD"
