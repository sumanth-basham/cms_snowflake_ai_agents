"""
cms_snowflake_ai_agents — Central configuration.

Maps to: python/config.py in sfguide-agentic-ai-for-asset-management
Adapted for: Medicare Part D Patient Safety Stars use case
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional

# ---------------------------------------------------------------------------
# Database / Schema constants
# ---------------------------------------------------------------------------

DATABASE = os.getenv("SNOWFLAKE_DATABASE", "CMS_STARS_DB")
SCHEMA_RAW = "SCHEMA_RAW"
SCHEMA_CURATED = "SCHEMA_CURATED"
SCHEMA_GOLD = "SCHEMA_GOLD"
SCHEMA_SEMANTIC = "SCHEMA_SEMANTIC"

WAREHOUSE = os.getenv("SNOWFLAKE_WAREHOUSE", "CMS_STARS_WH")
COMPUTE_POOL = os.getenv("SNOWFLAKE_COMPUTE_POOL", "CMS_STARS_POOL")

# Cortex model to use for agents
CORTEX_LLM_MODEL = os.getenv("CORTEX_LLM_MODEL", "mistral-large2")
CORTEX_EMBED_MODEL = os.getenv("CORTEX_EMBED_MODEL", "snowflake-arctic-embed-l-v2.0")

# ---------------------------------------------------------------------------
# Cortex Search service names
# ---------------------------------------------------------------------------

SEARCH_SERVICE_MEASURE_DOCS = "MEASURE_DOC_SEARCH"
SEARCH_SERVICE_POLICY_DOCS = "POLICY_DOC_SEARCH"
SEARCH_SERVICE_CLINICAL_GUIDANCE = "CLINICAL_GUIDANCE_SEARCH"
SEARCH_SERVICE_SAFETY_BULLETINS = "SAFETY_BULLETIN_SEARCH"

# ---------------------------------------------------------------------------
# Agent names (must match Snowflake Cortex Agent objects)
# ---------------------------------------------------------------------------

AGENT_MEASURE_INTERPRETATION = "MEASURE_INTERPRETATION_AGENT"
AGENT_GAP_DETECTION = "PATIENT_SAFETY_GAP_DETECTION_AGENT"
AGENT_OUTREACH_RECOMMENDATION = "OUTREACH_RECOMMENDATION_AGENT"
AGENT_STARS_PERFORMANCE = "STARS_PERFORMANCE_ANALYTICS_AGENT"
AGENT_AUDIT_EXPLAINABILITY = "AUDIT_EXPLAINABILITY_AGENT"
AGENT_ORCHESTRATOR = "CMS_STARS_ORCHESTRATOR"

# ---------------------------------------------------------------------------
# Semantic model paths (Cortex Analyst YAML files in Snowflake stage)
# ---------------------------------------------------------------------------

SEMANTIC_MODEL_STARS_PERFORMANCE = "stars_performance_model.yaml"
SEMANTIC_MODEL_MEMBER_RISK = "member_risk_model.yaml"
SEMANTIC_MODEL_CONTRACT_PERFORMANCE = "contract_performance_model.yaml"

# ---------------------------------------------------------------------------
# Stage names for documents and semantic models
# ---------------------------------------------------------------------------

STAGE_DOCUMENTS = "CMS_DOCUMENT_STAGE"
STAGE_SEMANTIC_MODELS = "CMS_SEMANTIC_MODELS_STAGE"

# ---------------------------------------------------------------------------
# Measurement year
# (Inferred architectural default — must be confirmed against CMS spec)
# ---------------------------------------------------------------------------

DEFAULT_MEASUREMENT_YEAR = int(os.getenv("MEASUREMENT_YEAR", "2024"))

# ---------------------------------------------------------------------------
# PHI risk levels (used in data contracts and governance)
# ---------------------------------------------------------------------------

PHI_LEVEL_HIGH = "PHI_HIGH"       # Direct identifiers: name, SSN, MBI, DOB
PHI_LEVEL_MEDIUM = "PHI_MEDIUM"   # Quasi-identifiers: zip, age, diagnosis
PHI_LEVEL_LOW = "PHI_LOW"         # De-identified / aggregated
PHI_LEVEL_NONE = "NONE"           # No PHI

# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLE_ADMIN = "CMS_STARS_ADMIN"
ROLE_ANALYST = "CMS_STARS_ANALYST"
ROLE_CLINICAL = "CMS_STARS_CLINICAL"
ROLE_AUDITOR = "CMS_STARS_AUDITOR"
ROLE_APP_USER = "CMS_STARS_APP_USER"
ROLE_DATA_ENGINEER = "CMS_STARS_DATA_ENGINEER"

# ---------------------------------------------------------------------------
# Measure domain codes
# (Inferred — must be validated against official CMS/PQA technical specs)
# ---------------------------------------------------------------------------

MEASURE_DOMAIN_HRM = "HRM"          # High-Risk Medication
MEASURE_DOMAIN_DDI = "DDI"          # Drug-Drug Interaction
MEASURE_DOMAIN_SUPD = "SUPD"        # Statin Use in Persons with Diabetes
MEASURE_DOMAIN_PDC = "PDC"          # Proportion of Days Covered (adherence)
MEASURE_DOMAIN_MTM = "MTM"          # Medication Therapy Management
MEASURE_DOMAIN_CMR = "CMR"          # Comprehensive Medication Review

ALL_MEASURE_DOMAINS = [
    MEASURE_DOMAIN_HRM,
    MEASURE_DOMAIN_DDI,
    MEASURE_DOMAIN_SUPD,
    MEASURE_DOMAIN_PDC,
    MEASURE_DOMAIN_MTM,
    MEASURE_DOMAIN_CMR,
]

# ---------------------------------------------------------------------------
# Risk thresholds
# (Inferred architectural defaults — must be validated with clinical SMEs)
# ---------------------------------------------------------------------------

RISK_SCORE_HIGH = 0.75
RISK_SCORE_MEDIUM = 0.50
RISK_SCORE_LOW = 0.25


@dataclass
class SnowflakeConnectionConfig:
    """Snowflake connection configuration loaded from environment variables."""
    account: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_ACCOUNT", ""))
    user: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_USER", ""))
    password: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_PASSWORD", ""))
    role: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_ROLE", ROLE_ANALYST))
    warehouse: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_WAREHOUSE", WAREHOUSE))
    database: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_DATABASE", DATABASE))
    schema: str = field(default_factory=lambda: os.getenv("SNOWFLAKE_SCHEMA", SCHEMA_GOLD))
    authenticator: Optional[str] = field(
        default_factory=lambda: os.getenv("SNOWFLAKE_AUTHENTICATOR", None)
    )

    def to_dict(self) -> dict:
        """Return connection parameters as a dict (excludes None values)."""
        params = {
            "account": self.account,
            "user": self.user,
            "role": self.role,
            "warehouse": self.warehouse,
            "database": self.database,
            "schema": self.schema,
        }
        if self.authenticator:
            params["authenticator"] = self.authenticator
        elif self.password:
            params["password"] = self.password
        return params


@dataclass
class AgentConfig:
    """Configuration for a single Cortex Agent."""
    agent_name: str
    description: str
    cortex_model: str = CORTEX_LLM_MODEL
    search_services: List[str] = field(default_factory=list)
    semantic_models: List[str] = field(default_factory=list)
    custom_tools: List[str] = field(default_factory=list)
    max_tokens: int = 4096
    temperature: float = 0.0


AGENT_CONFIGS = {
    AGENT_MEASURE_INTERPRETATION: AgentConfig(
        agent_name=AGENT_MEASURE_INTERPRETATION,
        description="Interprets CMS/PQA measure logic, denominator/numerator, exclusions, thresholds",
        search_services=[
            SEARCH_SERVICE_MEASURE_DOCS,
            SEARCH_SERVICE_CLINICAL_GUIDANCE,
        ],
        custom_tools=["get_measure_definition", "get_measure_versions"],
    ),
    AGENT_GAP_DETECTION: AgentConfig(
        agent_name=AGENT_GAP_DETECTION,
        description="Detects members at risk for measure failure or medication safety issues",
        search_services=[
            SEARCH_SERVICE_MEASURE_DOCS,
            SEARCH_SERVICE_SAFETY_BULLETINS,
        ],
        semantic_models=[SEMANTIC_MODEL_MEMBER_RISK],
        custom_tools=[
            "query_member_safety_gaps",
            "score_member_risk",
            "get_adherence_history",
        ],
    ),
    AGENT_OUTREACH_RECOMMENDATION: AgentConfig(
        agent_name=AGENT_OUTREACH_RECOMMENDATION,
        description="Recommends evidence-based interventions for at-risk members",
        search_services=[
            SEARCH_SERVICE_POLICY_DOCS,
            SEARCH_SERVICE_CLINICAL_GUIDANCE,
        ],
        custom_tools=[
            "get_member_intervention_history",
            "recommend_intervention",
            "check_formulary_alternatives",
        ],
    ),
    AGENT_STARS_PERFORMANCE: AgentConfig(
        agent_name=AGENT_STARS_PERFORMANCE,
        description="Analyzes contract/plan/region/provider Stars performance trends",
        semantic_models=[
            SEMANTIC_MODEL_STARS_PERFORMANCE,
            SEMANTIC_MODEL_CONTRACT_PERFORMANCE,
        ],
        custom_tools=[
            "query_contract_performance",
            "query_stars_trends",
        ],
    ),
    AGENT_AUDIT_EXPLAINABILITY: AgentConfig(
        agent_name=AGENT_AUDIT_EXPLAINABILITY,
        description="Provides evidence-based explanations for all AI decisions",
        search_services=[
            SEARCH_SERVICE_MEASURE_DOCS,
            SEARCH_SERVICE_POLICY_DOCS,
        ],
        custom_tools=[
            "get_agent_audit_log",
            "get_member_flag_evidence",
            "get_intervention_rationale",
        ],
    ),
}
