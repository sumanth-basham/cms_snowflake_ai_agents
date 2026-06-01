-- =============================================================================
-- medication_adherence.sql — Semantic views for medication adherence analysis.
--
-- These views form the semantic layer used by Cortex Analyst to answer
-- natural language questions about Medicare Part D medication adherence.
--
-- ⚠️  NOTE: All measure logic is illustrative. Validate against official
--           CMS/PQA technical specifications before production use.
-- =============================================================================

-- ---------------------------------------------------------------------------
-- 1. Patient Demographics View
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW CMS_STARS_DB.SCHEMA_SEMANTIC.PATIENT_DEMOGRAPHICS AS
SELECT
    m.member_id,
    m.contract_id,
    m.plan_id,
    m.state_code                                       AS region,
    YEAR(CURRENT_DATE()) - m.birth_year                AS age_years,
    CASE
        WHEN YEAR(CURRENT_DATE()) - m.birth_year < 65  THEN 'Under 65'
        WHEN YEAR(CURRENT_DATE()) - m.birth_year < 75  THEN '65-74'
        WHEN YEAR(CURRENT_DATE()) - m.birth_year < 85  THEN '75-84'
        ELSE '85+'
    END                                                AS age_group,
    m.gender_code,
    m.low_income_subsidy_code                          AS lis_status,
    m.enrollment_start_date,
    m.is_active
FROM CMS_STARS_DB.SCHEMA_CURATED.MEMBERS m
WHERE m.is_active = TRUE
  AND m.birth_year BETWEEN 1900 AND YEAR(CURRENT_DATE());


-- ---------------------------------------------------------------------------
-- 2. Medication Adherence Aggregates
--    Proportion of Days Covered (PDC) by therapeutic class, region, age group
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW CMS_STARS_DB.SCHEMA_SEMANTIC.MEDICATION_ADHERENCE_AGGREGATES AS
WITH
claims_windowed AS (
    SELECT
        pc.member_id,
        pc.contract_id,
        pc.drug_class                                 AS therapeutic_class,
        pc.fill_date,
        pc.days_supply,
        pc.measurement_year,
        -- Days between fills for gap analysis
        LAG(pc.fill_date) OVER (
            PARTITION BY pc.member_id, pc.drug_class, pc.measurement_year
            ORDER BY pc.fill_date
        )                                             AS prev_fill_date
    FROM CMS_STARS_DB.SCHEMA_CURATED.PHARMACY_CLAIMS pc
),
member_pdcs AS (
    SELECT
        cw.member_id,
        cw.contract_id,
        cw.therapeutic_class,
        cw.measurement_year,
        -- Proportion of Days Covered (simplified: days covered / 365)
        LEAST(
            SUM(cw.days_supply) / 365.0,
            1.0
        )                                             AS pdc_ratio,
        COUNT(*)                                      AS fill_count,
        -- Gap days: sum of positive gaps between consecutive fills
        SUM(
            CASE
                WHEN cw.prev_fill_date IS NOT NULL
                 AND DATEDIFF('day', cw.prev_fill_date, cw.fill_date)
                     > LAG(cw.days_supply) OVER (
                         PARTITION BY cw.member_id, cw.therapeutic_class, cw.measurement_year
                         ORDER BY cw.fill_date)
                THEN DATEDIFF('day', cw.prev_fill_date, cw.fill_date)
                     - LAG(cw.days_supply) OVER (
                         PARTITION BY cw.member_id, cw.therapeutic_class, cw.measurement_year
                         ORDER BY cw.fill_date)
                ELSE 0
            END
        )                                             AS total_gap_days
    FROM claims_windowed cw
    GROUP BY 1, 2, 3, 4
)
SELECT
    mp.therapeutic_class,
    pd.region,
    pd.age_group,
    mp.measurement_year,
    COUNT(DISTINCT mp.member_id)                      AS member_count,
    ROUND(AVG(mp.pdc_ratio), 4)                       AS avg_pdc_ratio,
    ROUND(
        SUM(CASE WHEN mp.pdc_ratio >= 0.80 THEN 1 ELSE 0 END)::FLOAT
        / NULLIF(COUNT(*), 0), 4
    )                                                  AS adherent_rate,
    ROUND(AVG(mp.fill_count), 2)                       AS avg_fill_count,
    ROUND(AVG(mp.total_gap_days), 2)                   AS avg_gap_days
FROM member_pdcs mp
JOIN CMS_STARS_DB.SCHEMA_SEMANTIC.PATIENT_DEMOGRAPHICS pd
    ON mp.member_id = pd.member_id
GROUP BY 1, 2, 3, 4;


-- ---------------------------------------------------------------------------
-- 3. Prescription Gap Analysis
--    Identifies members with coverage gaps >= 30 days
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW CMS_STARS_DB.SCHEMA_SEMANTIC.PRESCRIPTION_GAP_ANALYSIS AS
WITH sequential_fills AS (
    SELECT
        member_id,
        contract_id,
        drug_class                                     AS therapeutic_class,
        fill_date,
        days_supply,
        DATEADD('day', days_supply, fill_date)         AS coverage_end_date,
        measurement_year,
        LEAD(fill_date) OVER (
            PARTITION BY member_id, drug_class, measurement_year
            ORDER BY fill_date
        )                                              AS next_fill_date
    FROM CMS_STARS_DB.SCHEMA_CURATED.PHARMACY_CLAIMS
)
SELECT
    member_id,
    contract_id,
    therapeutic_class,
    fill_date                                          AS fill_date,
    coverage_end_date,
    next_fill_date,
    measurement_year,
    CASE
        WHEN next_fill_date IS NULL THEN NULL
        ELSE DATEDIFF('day', coverage_end_date, next_fill_date)
    END                                                AS gap_days,
    CASE
        WHEN next_fill_date IS NOT NULL
         AND DATEDIFF('day', coverage_end_date, next_fill_date) >= 30
        THEN TRUE
        ELSE FALSE
    END                                                AS has_significant_gap
FROM sequential_fills;


-- ---------------------------------------------------------------------------
-- 4. Outcome Correlation Metrics
--    Correlates adherence gaps with readmission risk
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW CMS_STARS_DB.SCHEMA_SEMANTIC.OUTCOME_CORRELATION AS
SELECT
    g.member_id,
    g.contract_id,
    g.therapeutic_class,
    g.measurement_year,
    -- Gap exposure
    SUM(CASE WHEN g.has_significant_gap THEN g.gap_days ELSE 0 END) AS total_gap_days,
    COUNT(CASE WHEN g.has_significant_gap THEN 1 END)                AS gap_episodes,
    -- Risk profile from safety gaps
    sg.risk_score,
    sg.measure_code,
    sg.gap_status
FROM CMS_STARS_DB.SCHEMA_SEMANTIC.PRESCRIPTION_GAP_ANALYSIS g
LEFT JOIN CMS_STARS_DB.SCHEMA_CURATED.PATIENT_SAFETY_GAPS sg
    ON g.member_id = sg.member_id
   AND g.measurement_year = sg.measurement_year
GROUP BY 1, 2, 3, 4, 7, 8, 9;


-- ---------------------------------------------------------------------------
-- 5. Monthly Adherence Time-Series
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW CMS_STARS_DB.SCHEMA_SEMANTIC.MONTHLY_ADHERENCE_TREND AS
SELECT
    DATE_TRUNC('month', pc.fill_date)                  AS fill_month,
    pc.drug_class                                      AS therapeutic_class,
    pd.region,
    pd.age_group,
    pc.measurement_year,
    COUNT(DISTINCT pc.member_id)                       AS members_filling,
    SUM(pc.days_supply)                                AS total_days_supplied,
    COUNT(*)                                           AS claim_count
FROM CMS_STARS_DB.SCHEMA_CURATED.PHARMACY_CLAIMS pc
JOIN CMS_STARS_DB.SCHEMA_SEMANTIC.PATIENT_DEMOGRAPHICS pd
    ON pc.member_id = pd.member_id
GROUP BY 1, 2, 3, 4, 5;
