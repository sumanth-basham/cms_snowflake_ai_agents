-- =============================================================================
-- rbac_setup.sql — Role-Based Access Control for CMS Stars AI Agents
--
-- Governance tier: MANDATORY for production
-- PHI relevance: HIGH — controls access to member-level data
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Role hierarchy
-- ---------------------------------------------------------------------------
-- CMS_STARS_ADMIN
--   └── CMS_STARS_DATA_ENGINEER
--   └── CMS_STARS_CLINICAL
--       └── CMS_STARS_ANALYST
--           └── CMS_STARS_APP_USER
--   └── CMS_STARS_AUDITOR

-- ---------------------------------------------------------------------------
-- Warehouse grants
-- ---------------------------------------------------------------------------

GRANT USAGE ON WAREHOUSE CMS_STARS_WH TO ROLE CMS_STARS_DATA_ENGINEER;
GRANT USAGE ON WAREHOUSE CMS_STARS_WH TO ROLE CMS_STARS_ANALYST;
GRANT USAGE ON WAREHOUSE CMS_STARS_WH TO ROLE CMS_STARS_CLINICAL;
GRANT USAGE ON WAREHOUSE CMS_STARS_WH TO ROLE CMS_STARS_AUDITOR;
GRANT USAGE ON WAREHOUSE CMS_STARS_WH TO ROLE CMS_STARS_APP_USER;

-- ---------------------------------------------------------------------------
-- Database grants
-- ---------------------------------------------------------------------------

GRANT USAGE ON DATABASE CMS_STARS_DB TO ROLE CMS_STARS_DATA_ENGINEER;
GRANT USAGE ON DATABASE CMS_STARS_DB TO ROLE CMS_STARS_ANALYST;
GRANT USAGE ON DATABASE CMS_STARS_DB TO ROLE CMS_STARS_CLINICAL;
GRANT USAGE ON DATABASE CMS_STARS_DB TO ROLE CMS_STARS_AUDITOR;
GRANT USAGE ON DATABASE CMS_STARS_DB TO ROLE CMS_STARS_APP_USER;

-- ---------------------------------------------------------------------------
-- Schema grants
-- ---------------------------------------------------------------------------

-- Data Engineer: full access to raw and curated
GRANT ALL ON SCHEMA CMS_STARS_DB.SCHEMA_RAW TO ROLE CMS_STARS_DATA_ENGINEER;
GRANT ALL ON SCHEMA CMS_STARS_DB.SCHEMA_CURATED TO ROLE CMS_STARS_DATA_ENGINEER;
GRANT ALL ON SCHEMA CMS_STARS_DB.SCHEMA_GOLD TO ROLE CMS_STARS_DATA_ENGINEER;

-- Analyst: read curated and gold only
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_CURATED TO ROLE CMS_STARS_ANALYST;
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_GOLD TO ROLE CMS_STARS_ANALYST;
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_SEMANTIC TO ROLE CMS_STARS_ANALYST;

-- Clinical: read all schemas (with masking)
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_CURATED TO ROLE CMS_STARS_CLINICAL;
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_GOLD TO ROLE CMS_STARS_CLINICAL;
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_SEMANTIC TO ROLE CMS_STARS_CLINICAL;

-- Auditor: read gold and audit log only
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_GOLD TO ROLE CMS_STARS_AUDITOR;

-- App User: access gold layer through app only
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_GOLD TO ROLE CMS_STARS_APP_USER;
GRANT USAGE ON SCHEMA CMS_STARS_DB.SCHEMA_SEMANTIC TO ROLE CMS_STARS_APP_USER;

-- ---------------------------------------------------------------------------
-- Table-level grants
-- ---------------------------------------------------------------------------

-- RAW tables: data engineer only (except document chunks for search)
GRANT SELECT ON TABLE CMS_STARS_DB.SCHEMA_RAW.RAW_DOCUMENT_CHUNKS TO ROLE CMS_STARS_ANALYST;
GRANT SELECT ON TABLE CMS_STARS_DB.SCHEMA_RAW.RAW_DOCUMENT_CHUNKS TO ROLE CMS_STARS_CLINICAL;

-- CURATED tables
GRANT SELECT ON ALL TABLES IN SCHEMA CMS_STARS_DB.SCHEMA_CURATED TO ROLE CMS_STARS_ANALYST;
GRANT SELECT ON ALL TABLES IN SCHEMA CMS_STARS_DB.SCHEMA_CURATED TO ROLE CMS_STARS_CLINICAL;

-- GOLD tables
GRANT SELECT ON ALL TABLES IN SCHEMA CMS_STARS_DB.SCHEMA_GOLD TO ROLE CMS_STARS_ANALYST;
GRANT SELECT ON ALL TABLES IN SCHEMA CMS_STARS_DB.SCHEMA_GOLD TO ROLE CMS_STARS_CLINICAL;
GRANT SELECT ON ALL TABLES IN SCHEMA CMS_STARS_DB.SCHEMA_GOLD TO ROLE CMS_STARS_AUDITOR;
GRANT SELECT ON TABLE CMS_STARS_DB.SCHEMA_GOLD.AGENT_AUDIT_LOG TO ROLE CMS_STARS_APP_USER;

-- Audit log insert: app user (for logging agent interactions)
GRANT INSERT ON TABLE CMS_STARS_DB.SCHEMA_GOLD.AGENT_AUDIT_LOG TO ROLE CMS_STARS_APP_USER;

-- ---------------------------------------------------------------------------
-- Cortex Agent grants
-- ---------------------------------------------------------------------------
-- Production: USAGE on agents granted per-role as Snowflake supports

-- ---------------------------------------------------------------------------
-- Cortex Search grants
-- ---------------------------------------------------------------------------
GRANT USAGE ON CORTEX SEARCH SERVICE CMS_STARS_DB.SCHEMA_RAW.MEASURE_DOC_SEARCH
  TO ROLE CMS_STARS_ANALYST;
GRANT USAGE ON CORTEX SEARCH SERVICE CMS_STARS_DB.SCHEMA_RAW.MEASURE_DOC_SEARCH
  TO ROLE CMS_STARS_CLINICAL;
GRANT USAGE ON CORTEX SEARCH SERVICE CMS_STARS_DB.SCHEMA_RAW.POLICY_DOC_SEARCH
  TO ROLE CMS_STARS_ANALYST;
GRANT USAGE ON CORTEX SEARCH SERVICE CMS_STARS_DB.SCHEMA_RAW.CLINICAL_GUIDANCE_SEARCH
  TO ROLE CMS_STARS_CLINICAL;
GRANT USAGE ON CORTEX SEARCH SERVICE CMS_STARS_DB.SCHEMA_RAW.SAFETY_BULLETIN_SEARCH
  TO ROLE CMS_STARS_CLINICAL;
GRANT USAGE ON CORTEX SEARCH SERVICE CMS_STARS_DB.SCHEMA_RAW.SAFETY_BULLETIN_SEARCH
  TO ROLE CMS_STARS_ANALYST;
