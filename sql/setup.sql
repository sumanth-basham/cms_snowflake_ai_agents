-- =============================================================================
-- setup.sql — CMS Snowflake AI Agents: Full Snowflake environment setup
--
-- Maps to: scripts/setup.sql in sfguide-agentic-ai-for-asset-management
-- Adapted for: Medicare Part D Patient Safety Stars use case
--
-- Execution order:
--   1. Database and warehouse
--   2. Schemas (raw / curated / gold / semantic)
--   3. Roles and grants
--   4. Stages
--   5. Bronze (raw) tables
--   6. Silver (curated) tables
--   7. Gold (analytics) tables
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Database, warehouse, and compute
-- ---------------------------------------------------------------------------

CREATE DATABASE IF NOT EXISTS CMS_STARS_DB
  COMMENT = 'CMS Medicare Part D Patient Safety Stars — Snowflake AI Agents';

CREATE WAREHOUSE IF NOT EXISTS CMS_STARS_WH
  WAREHOUSE_SIZE = 'SMALL'
  AUTO_SUSPEND = 120
  AUTO_RESUME = TRUE
  COMMENT = 'CMS Stars AI Agents warehouse';

USE DATABASE CMS_STARS_DB;

-- ---------------------------------------------------------------------------
-- 2. Schemas
-- ---------------------------------------------------------------------------

CREATE SCHEMA IF NOT EXISTS SCHEMA_RAW
  COMMENT = 'Bronze layer: raw ingested data, document chunks';

CREATE SCHEMA IF NOT EXISTS SCHEMA_CURATED
  COMMENT = 'Silver layer: cleansed and standardized clinical data';

CREATE SCHEMA IF NOT EXISTS SCHEMA_GOLD
  COMMENT = 'Gold layer: analytics marts, risk profiles, measure facts';

CREATE SCHEMA IF NOT EXISTS SCHEMA_SEMANTIC
  COMMENT = 'Semantic views for Cortex Analyst';

-- ---------------------------------------------------------------------------
-- 3. Roles and RBAC
-- (See governance/rbac_setup.sql for full grant matrix)
-- ---------------------------------------------------------------------------

CREATE ROLE IF NOT EXISTS CMS_STARS_ADMIN;
CREATE ROLE IF NOT EXISTS CMS_STARS_DATA_ENGINEER;
CREATE ROLE IF NOT EXISTS CMS_STARS_ANALYST;
CREATE ROLE IF NOT EXISTS CMS_STARS_CLINICAL;
CREATE ROLE IF NOT EXISTS CMS_STARS_AUDITOR;
CREATE ROLE IF NOT EXISTS CMS_STARS_APP_USER;

-- ---------------------------------------------------------------------------
-- 4. Stages for documents and semantic models
-- ---------------------------------------------------------------------------

USE SCHEMA SCHEMA_RAW;

CREATE STAGE IF NOT EXISTS CMS_DOCUMENT_STAGE
  COMMENT = 'CMS/PQA measure docs, policy docs, clinical guidance for Cortex Search';

CREATE STAGE IF NOT EXISTS CMS_SEMANTIC_MODELS_STAGE
  COMMENT = 'Cortex Analyst YAML semantic model files';

-- =============================================================================
-- BRONZE LAYER (SCHEMA_RAW) — Raw ingested tables
-- =============================================================================

-- ---------------------------------------------------------------------------
-- RAW_MEMBERS
-- Grain: one row per member per source system load
-- PHI: HIGH — member_id is a de-identified surrogate in this design
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_RAW.RAW_MEMBERS (
    member_id             VARCHAR(20)    NOT NULL  COMMENT 'Surrogate member ID (de-identified)',
    contract_id           VARCHAR(10)    NOT NULL  COMMENT 'CMS contract ID (H-number)',
    plan_id               VARCHAR(10)              COMMENT 'PBP plan ID',
    state_code            VARCHAR(2)               COMMENT 'Member state of residence',
    birth_year            INTEGER                  COMMENT 'Year of birth (not full DOB)',
    gender_code           VARCHAR(1)               COMMENT 'M / F / U',
    low_income_subsidy_code VARCHAR(20)            COMMENT 'LIS level: LIS_FULL, LIS_PARTIAL, NON_LIS',
    enrollment_start_date DATE                     COMMENT 'Effective enrollment start date',
    enrollment_end_date   DATE                     COMMENT 'Effective enrollment end date (NULL if active)',
    is_active             BOOLEAN                  COMMENT 'TRUE if currently enrolled',
    _source_system        VARCHAR(50)              COMMENT 'Source system identifier',
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- RAW_PHARMACY_CLAIMS
-- Grain: one row per dispensing event (claim line)
-- PHI: HIGH — member_id links to member record
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_RAW.RAW_PHARMACY_CLAIMS (
    claim_id              VARCHAR(50)    NOT NULL  COMMENT 'Unique claim identifier',
    member_id             VARCHAR(20)    NOT NULL  COMMENT 'De-identified member surrogate',
    contract_id           VARCHAR(10)    NOT NULL  COMMENT 'CMS contract ID',
    plan_id               VARCHAR(10)              COMMENT 'PBP plan ID',
    ndc                   VARCHAR(11)              COMMENT 'National Drug Code (11-digit)',
    drug_class            VARCHAR(50)              COMMENT 'Therapeutic drug class (synthetic label)',
    days_supply           INTEGER                  COMMENT 'Days supply dispensed',
    fill_date             DATE                     COMMENT 'Date prescription was filled',
    quantity_dispensed    DECIMAL(10,2)            COMMENT 'Quantity dispensed',
    pharmacy_npi          VARCHAR(10)              COMMENT 'Dispensing pharmacy NPI',
    prescriber_npi        VARCHAR(10)              COMMENT 'Prescribing provider NPI',
    paid_amount           DECIMAL(12,2)            COMMENT 'Paid amount (plan cost share)',
    measurement_year      INTEGER                  COMMENT 'Stars measurement year',
    _source_system        VARCHAR(50),
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- RAW_DRUG_REFERENCE
-- Grain: one row per NDC
-- PHI: NONE
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_RAW.RAW_DRUG_REFERENCE (
    ndc                   VARCHAR(11)    NOT NULL  COMMENT '11-digit NDC',
    drug_name             VARCHAR(200)             COMMENT 'Generic drug name',
    rxnorm_cui            VARCHAR(20)              COMMENT 'RxNorm concept unique identifier',
    therapeutic_class     VARCHAR(100)             COMMENT 'Therapeutic drug class',
    generic_indicator     VARCHAR(1)               COMMENT 'Y = generic, N = brand',
    is_high_risk_elderly  BOOLEAN                  COMMENT 'Flagged in high-risk elderly lists (verify with spec)',
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- RAW_MTM_INTERVENTIONS
-- Grain: one row per intervention event
-- PHI: HIGH — member_id
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_RAW.RAW_MTM_INTERVENTIONS (
    intervention_id       VARCHAR(50)    NOT NULL  COMMENT 'Unique intervention ID',
    member_id             VARCHAR(20)    NOT NULL  COMMENT 'De-identified member surrogate',
    contract_id           VARCHAR(10)    NOT NULL  COMMENT 'CMS contract ID',
    intervention_type     VARCHAR(50)              COMMENT 'CMR, TMR, PHARMACIST_CONSULT, etc.',
    intervention_date     DATE                     COMMENT 'Date of intervention',
    outcome               VARCHAR(50)              COMMENT 'COMPLETED, REFUSED, NO_RESPONSE, etc.',
    pharmacist_npi        VARCHAR(10)              COMMENT 'Pharmacist NPI',
    notes_available       BOOLEAN                  COMMENT 'TRUE if structured notes exist',
    measurement_year      INTEGER,
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- RAW_PATIENT_SAFETY_GAPS
-- Grain: one row per member per measure gap
-- PHI: HIGH — member_id
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_RAW.RAW_PATIENT_SAFETY_GAPS (
    gap_id                VARCHAR(50)    NOT NULL  COMMENT 'Unique gap identifier',
    member_id             VARCHAR(20)    NOT NULL,
    contract_id           VARCHAR(10)    NOT NULL,
    measure_code          VARCHAR(50)              COMMENT 'Measure code (e.g. HRM_V1, SUPD_V1)',
    gap_detected_date     DATE,
    gap_status            VARCHAR(20)              COMMENT 'OPEN, CLOSED, IN_PROGRESS, ESCALATED',
    risk_score            DECIMAL(5,3)             COMMENT 'Computed risk score 0.0 to 1.0',
    evidence_summary      VARCHAR(2000)            COMMENT 'Brief evidence description (no PHI in text)',
    measurement_year      INTEGER,
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- RAW_DOCUMENT_CHUNKS
-- Grain: one row per text chunk from CMS/PQA documents
-- PHI: NONE (document content only, no member data)
-- Used by: Cortex Search services
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_RAW.RAW_DOCUMENT_CHUNKS (
    chunk_id              VARCHAR(50)    NOT NULL  COMMENT 'Unique chunk identifier',
    doc_id                VARCHAR(100)   NOT NULL  COMMENT 'Source document ID',
    doc_title             VARCHAR(500)             COMMENT 'Document title',
    doc_type              VARCHAR(50)              COMMENT 'MEASURE_SPEC, POLICY, CLINICAL_GUIDANCE, SAFETY_BULLETIN',
    measure_code          VARCHAR(50)              COMMENT 'Associated measure code (if applicable)',
    therapeutic_class     VARCHAR(100)             COMMENT 'Therapeutic class (if applicable)',
    contract_id           VARCHAR(10)              COMMENT 'Plan contract ID (if policy-specific)',
    effective_year        INTEGER                  COMMENT 'Year the document is effective',
    severity_level        VARCHAR(20)              COMMENT 'For safety bulletins: HIGH, MEDIUM, LOW',
    chunk_sequence        INTEGER                  COMMENT 'Chunk order within document',
    chunk_text            VARCHAR(8192)            COMMENT 'Text content of chunk — no PHI allowed',
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- =============================================================================
-- SILVER LAYER (SCHEMA_CURATED) — Cleansed and standardized data
-- =============================================================================

USE SCHEMA SCHEMA_CURATED;

-- ---------------------------------------------------------------------------
-- MEMBERS
-- Grain: one row per member (current record)
-- PHI: HIGH
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_CURATED.MEMBERS (
    member_id             VARCHAR(20)    NOT NULL PRIMARY KEY,
    contract_id           VARCHAR(10)    NOT NULL,
    plan_id               VARCHAR(10),
    state_code            VARCHAR(2),
    birth_year            INTEGER,
    age_band              VARCHAR(20)              COMMENT 'Derived: e.g. 65-69, 70-74',
    gender_code           VARCHAR(1),
    low_income_subsidy_code VARCHAR(20),
    enrollment_start_date DATE,
    enrollment_end_date   DATE,
    is_active             BOOLEAN,
    continuous_enrollment_days INTEGER             COMMENT 'Days continuously enrolled in measurement year',
    _curated_timestamp    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- PHARMACY_CLAIMS
-- Grain: one row per claim line (curated, deduplicated)
-- PHI: HIGH
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_CURATED.PHARMACY_CLAIMS (
    claim_id              VARCHAR(50)    NOT NULL PRIMARY KEY,
    member_id             VARCHAR(20)    NOT NULL,
    contract_id           VARCHAR(10)    NOT NULL,
    plan_id               VARCHAR(10),
    ndc                   VARCHAR(11),
    rxnorm_cui            VARCHAR(20)              COMMENT 'Resolved from drug reference',
    drug_name             VARCHAR(200),
    therapeutic_class     VARCHAR(100),
    is_high_risk_elderly  BOOLEAN,
    days_supply           INTEGER,
    fill_date             DATE,
    quantity_dispensed    DECIMAL(10,2),
    pharmacy_npi          VARCHAR(10),
    prescriber_npi        VARCHAR(10),
    paid_amount           DECIMAL(12,2),
    measurement_year      INTEGER,
    _curated_timestamp    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- MEASURE_DEFINITIONS
-- Grain: one row per measure per version
-- PHI: NONE
-- Source: Loaded from content_library/_rules/
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_CURATED.MEASURE_DEFINITIONS (
    measure_code          VARCHAR(50)    NOT NULL  COMMENT 'Unique measure identifier',
    measure_version       VARCHAR(20)    NOT NULL  COMMENT 'Version (e.g. 2024.1)',
    measure_name          VARCHAR(200),
    measure_domain        VARCHAR(50)              COMMENT 'HRM, DDI, SUPD, PDC, MTM, CMR',
    description           VARCHAR(2000),
    denominator_logic_summary VARCHAR(2000)        COMMENT 'Plain-language denominator description',
    numerator_logic_summary   VARCHAR(2000)        COMMENT 'Plain-language numerator description',
    exclusion_logic_summary   VARCHAR(2000),
    measurement_year      INTEGER,
    effective_start_date  DATE,
    effective_end_date    DATE,
    pdc_threshold         DECIMAL(5,3)             COMMENT 'PDC threshold if applicable (e.g. 0.80)',
    star_rating_direction VARCHAR(10)              COMMENT 'HIGHER_IS_BETTER or LOWER_IS_BETTER',
    spec_confirmed        BOOLEAN  DEFAULT FALSE   COMMENT 'TRUE = validated against official spec',
    spec_source           VARCHAR(500)             COMMENT 'Source document reference',
    assumptions           VARCHAR(2000)            COMMENT 'Explicit assumptions (if spec_confirmed=FALSE)',
    _load_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    PRIMARY KEY (measure_code, measure_version)
);

-- =============================================================================
-- GOLD LAYER (SCHEMA_GOLD) — Analytics marts
-- =============================================================================

USE SCHEMA SCHEMA_GOLD;

-- ---------------------------------------------------------------------------
-- STARS_MEASURE_FACT
-- Grain: one row per member per measure per measurement year
-- PHI: HIGH
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_GOLD.STARS_MEASURE_FACT (
    fact_id               VARCHAR(50)    NOT NULL PRIMARY KEY,
    member_id             VARCHAR(20)    NOT NULL,
    contract_id           VARCHAR(10)    NOT NULL,
    plan_id               VARCHAR(10),
    measure_code          VARCHAR(50)    NOT NULL,
    measure_version       VARCHAR(20),
    measurement_year      INTEGER        NOT NULL,
    in_denominator        BOOLEAN,
    in_numerator          BOOLEAN,
    excluded              BOOLEAN        DEFAULT FALSE,
    exclusion_reason      VARCHAR(200),
    pdc_value             DECIMAL(5,3)             COMMENT 'Proportion of days covered (if PDC measure)',
    compliance_flag       BOOLEAN                  COMMENT 'TRUE = meets measure threshold',
    risk_score            DECIMAL(5,3),
    gap_status            VARCHAR(20),
    _computed_timestamp   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- CONTRACT_PERFORMANCE_SUMMARY
-- Grain: one row per contract per measure per measurement year
-- PHI: LOW (aggregated)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_GOLD.CONTRACT_PERFORMANCE_SUMMARY (
    summary_id            VARCHAR(50)    NOT NULL PRIMARY KEY,
    contract_id           VARCHAR(10)    NOT NULL,
    measure_code          VARCHAR(50)    NOT NULL,
    measurement_year      INTEGER        NOT NULL,
    denominator_count     INTEGER,
    numerator_count       INTEGER,
    excluded_count        INTEGER,
    measure_rate          DECIMAL(7,4)             COMMENT 'numerator / denominator',
    stars_cut_point_2     DECIMAL(7,4)             COMMENT 'Estimated 2-star threshold (inferred, verify)',
    stars_cut_point_3     DECIMAL(7,4)             COMMENT 'Estimated 3-star threshold (inferred, verify)',
    stars_cut_point_4     DECIMAL(7,4)             COMMENT 'Estimated 4-star threshold (inferred, verify)',
    stars_cut_point_5     DECIMAL(7,4)             COMMENT 'Estimated 5-star threshold (inferred, verify)',
    estimated_star_rating DECIMAL(3,1)             COMMENT 'Estimated star rating (REQUIRES OFFICIAL CUT POINTS)',
    _computed_timestamp   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- MEMBER_RISK_PROFILE
-- Grain: one row per member per measurement year
-- PHI: HIGH
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_GOLD.MEMBER_RISK_PROFILE (
    profile_id            VARCHAR(50)    NOT NULL PRIMARY KEY,
    member_id             VARCHAR(20)    NOT NULL,
    contract_id           VARCHAR(10)    NOT NULL,
    measurement_year      INTEGER        NOT NULL,
    overall_risk_score    DECIMAL(5,3),
    hrm_risk_flag         BOOLEAN,
    ddi_risk_flag         BOOLEAN,
    pdc_risk_flag         BOOLEAN,
    supd_risk_flag        BOOLEAN,
    open_gap_count        INTEGER,
    last_intervention_date DATE,
    intervention_count    INTEGER,
    priority_tier         VARCHAR(20)              COMMENT 'HIGH, MEDIUM, LOW based on risk score',
    _computed_timestamp   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- ---------------------------------------------------------------------------
-- AGENT_AUDIT_LOG
-- Grain: one row per agent query / response
-- PHI: Minimal — no member identifiers in prompt/response text
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_GOLD.AGENT_AUDIT_LOG (
    audit_id              VARCHAR(50)    NOT NULL PRIMARY KEY,
    session_id            VARCHAR(50),
    agent_name            VARCHAR(100)   NOT NULL,
    user_role             VARCHAR(50),
    query_timestamp       TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    query_summary         VARCHAR(500)             COMMENT 'Sanitized query description (no PHI)',
    response_summary      VARCHAR(1000)            COMMENT 'Sanitized response description',
    tools_invoked         VARIANT                  COMMENT 'JSON: list of tools called',
    retrieval_sources     VARIANT                  COMMENT 'JSON: document chunks retrieved',
    member_count_in_scope INTEGER                  COMMENT 'Number of members in scope (count, not IDs)',
    confidence_level      VARCHAR(20)              COMMENT 'HIGH, MEDIUM, LOW, INSUFFICIENT',
    human_review_required BOOLEAN        DEFAULT FALSE,
    human_review_status   VARCHAR(20)              COMMENT 'PENDING, APPROVED, REJECTED',
    latency_ms            INTEGER,
    token_count           INTEGER
);

-- ---------------------------------------------------------------------------
-- INTERVENTION_RECOMMENDATIONS
-- Grain: one row per member per recommendation event
-- PHI: HIGH
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS SCHEMA_GOLD.INTERVENTION_RECOMMENDATIONS (
    recommendation_id     VARCHAR(50)    NOT NULL PRIMARY KEY,
    member_id             VARCHAR(20)    NOT NULL,
    contract_id           VARCHAR(10)    NOT NULL,
    measure_code          VARCHAR(50),
    recommendation_type   VARCHAR(100)             COMMENT 'PHARMACIST_REVIEW, PROVIDER_OUTREACH, etc.',
    recommendation_text   VARCHAR(2000)            COMMENT 'Agent-generated recommendation',
    evidence_doc_ids      VARIANT                  COMMENT 'JSON: doc IDs supporting recommendation',
    confidence_level      VARCHAR(20),
    generated_timestamp   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP(),
    analyst_review_status VARCHAR(20)              COMMENT 'PENDING, APPROVED, REJECTED, MODIFIED',
    analyst_notes         VARCHAR(2000),
    actioned_date         DATE
);

-- =============================================================================
-- NEXT STEPS: Run Python scripts from your local machine or CI/CD pipeline
-- =============================================================================
--
-- NOTE: Snowflake SQL cannot directly invoke external Python scripts.
-- After this SQL setup completes, run the following Python steps from the
-- command line (or let GitHub Actions handle them automatically — see
-- .github/workflows/deploy.yml).
--
-- Prerequisites:
--   pip install -r requirements.txt
--   cp deployment/.env.template .env   # then fill in your credentials
--
-- Step 1 — SQL setup (this file — already done when you reach this point):
--   python -m python.main --step setup
--
-- Step 2 — Generate and load synthetic sample data into Snowflake:
--   python -m python.main --step load_data
--
-- Step 3 — Build Cortex Search indexes (RAG retrieval layer):
--   python -m python.main --step build_search
--
-- Step 4 — Upload semantic model YAML files for Cortex Analyst:
--   python -m python.main --step build_semantic
--
-- Step 5 — Deploy all Cortex Agents:
--   python -m python.main --step deploy_agents
--
-- Or run all steps in sequence:
--   python -m python.main --step all
--
-- Alternatively, use the deploy script:
--   ./deployment/deploy.sh --step all
--
-- For CI/CD deployment via GitHub Actions, see:
--   .github/workflows/deploy.yml
-- =============================================================================
