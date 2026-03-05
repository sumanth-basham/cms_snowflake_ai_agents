-- =============================================================================
-- masking_policies.sql — Dynamic Data Masking for PHI/PII fields
--
-- Governance tier: MANDATORY for production
-- PHI relevance: HIGH — masks member identifiers for non-clinical roles
-- =============================================================================

USE DATABASE CMS_STARS_DB;

-- ---------------------------------------------------------------------------
-- Masking policy: member_id
-- Clinical and admin roles see real surrogate IDs
-- Analyst and app user see partial masked ID
-- Auditor sees tokenized form
-- ---------------------------------------------------------------------------

CREATE OR REPLACE MASKING POLICY SCHEMA_CURATED.MASK_MEMBER_ID AS (val STRING)
RETURNS STRING ->
  CASE
    -- Clinical and admin see the actual surrogate ID
    WHEN CURRENT_ROLE() IN ('CMS_STARS_CLINICAL', 'CMS_STARS_ADMIN', 'CMS_STARS_DATA_ENGINEER')
      THEN val
    -- Analyst and app user see partial mask: MBR***1234 (last 4 chars)
    WHEN CURRENT_ROLE() IN ('CMS_STARS_ANALYST', 'CMS_STARS_APP_USER')
      THEN 'MBR***' || RIGHT(val, 4)
    -- Auditor sees fully masked
    WHEN CURRENT_ROLE() = 'CMS_STARS_AUDITOR'
      THEN 'MBR-REDACTED'
    -- Default: fully masked
    ELSE '***MASKED***'
  END;

-- Apply masking policy to MEMBERS table
ALTER TABLE SCHEMA_CURATED.MEMBERS
  MODIFY COLUMN member_id
  SET MASKING POLICY SCHEMA_CURATED.MASK_MEMBER_ID;

-- Apply masking policy to PHARMACY_CLAIMS
ALTER TABLE SCHEMA_CURATED.PHARMACY_CLAIMS
  MODIFY COLUMN member_id
  SET MASKING POLICY SCHEMA_CURATED.MASK_MEMBER_ID;

-- Apply masking policy to GOLD tables
ALTER TABLE SCHEMA_GOLD.STARS_MEASURE_FACT
  MODIFY COLUMN member_id
  SET MASKING POLICY SCHEMA_CURATED.MASK_MEMBER_ID;

ALTER TABLE SCHEMA_GOLD.MEMBER_RISK_PROFILE
  MODIFY COLUMN member_id
  SET MASKING POLICY SCHEMA_CURATED.MASK_MEMBER_ID;

ALTER TABLE SCHEMA_GOLD.INTERVENTION_RECOMMENDATIONS
  MODIFY COLUMN member_id
  SET MASKING POLICY SCHEMA_CURATED.MASK_MEMBER_ID;

-- ---------------------------------------------------------------------------
-- Masking policy: paid_amount (financial sensitivity)
-- Only admin and data engineer see actual amounts
-- ---------------------------------------------------------------------------

CREATE OR REPLACE MASKING POLICY SCHEMA_CURATED.MASK_FINANCIAL AS (val DECIMAL)
RETURNS DECIMAL ->
  CASE
    WHEN CURRENT_ROLE() IN ('CMS_STARS_ADMIN', 'CMS_STARS_DATA_ENGINEER')
      THEN val
    ELSE NULL
  END;

ALTER TABLE SCHEMA_CURATED.PHARMACY_CLAIMS
  MODIFY COLUMN paid_amount
  SET MASKING POLICY SCHEMA_CURATED.MASK_FINANCIAL;

-- ---------------------------------------------------------------------------
-- Row-level security policy: contract isolation
-- Users may only see data for contracts they are authorized for
-- Uses a mapping table: CONTRACT_USER_ACCESS_MAP
-- ---------------------------------------------------------------------------

-- Create access mapping table
CREATE TABLE IF NOT EXISTS SCHEMA_RAW.CONTRACT_USER_ACCESS_MAP (
    username          VARCHAR(100)  NOT NULL,
    contract_id       VARCHAR(10)   NOT NULL,
    granted_by        VARCHAR(100),
    granted_at        TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Row access policy
CREATE OR REPLACE ROW ACCESS POLICY SCHEMA_CURATED.CONTRACT_ROW_ACCESS
AS (contract_id VARCHAR)
RETURNS BOOLEAN ->
  CASE
    -- Admin and data engineer see all contracts
    WHEN CURRENT_ROLE() IN ('CMS_STARS_ADMIN', 'CMS_STARS_DATA_ENGINEER')
      THEN TRUE
    -- Others: check access mapping table
    ELSE EXISTS (
      SELECT 1
      FROM CMS_STARS_DB.SCHEMA_RAW.CONTRACT_USER_ACCESS_MAP
      WHERE username = CURRENT_USER()
        AND CMS_STARS_DB.SCHEMA_RAW.CONTRACT_USER_ACCESS_MAP.contract_id = contract_id
    )
  END;

-- Apply row access policy to key tables
ALTER TABLE SCHEMA_CURATED.MEMBERS
  ADD ROW ACCESS POLICY SCHEMA_CURATED.CONTRACT_ROW_ACCESS ON (contract_id);

ALTER TABLE SCHEMA_GOLD.STARS_MEASURE_FACT
  ADD ROW ACCESS POLICY SCHEMA_CURATED.CONTRACT_ROW_ACCESS ON (contract_id);

ALTER TABLE SCHEMA_GOLD.CONTRACT_PERFORMANCE_SUMMARY
  ADD ROW ACCESS POLICY SCHEMA_CURATED.CONTRACT_ROW_ACCESS ON (contract_id);
