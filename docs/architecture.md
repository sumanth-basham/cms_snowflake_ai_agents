# Architecture: CMS Snowflake AI Agents

## Medicare Part D Patient Safety Stars — Full Solution Architecture

---

## 1. Business Problem

Medicare health plans and PBMs must measure and improve performance on CMS Medicare Part D Star Ratings. The **Patient Safety** category includes measures like:

- High-Risk Medication (HRM) usage in older adults
- Drug-Drug Interactions (DDI)
- Statin Use in Persons with Diabetes (SUPD)
- Medication Adherence (PDC) measures

Poor performance on these measures impacts plan star ratings, which determine:
- CMS quality bonus payments
- Member enrollment eligibility
- Competitive positioning

**The challenge**: Quality teams have massive claims datasets but lack tools to:
1. Interpret complex measure logic quickly
2. Identify at-risk members proactively
3. Generate evidence-based intervention recommendations
4. Explain AI-generated decisions to auditors and regulators

---

## 2. Solution Architecture

### Architecture Principles

| Principle | Application |
|---|---|
| PHI minimization | Surrogate IDs, masking, no PHI in LLM prompts |
| Evidence grounding | All responses cite retrieved documents |
| Human-in-the-loop | All clinical decisions require analyst review |
| Auditability | Every agent query logged with evidence |
| Metadata-driven measures | Measure logic in config tables, not hardcoded |

### Data Flow

```
Source Systems
    │
    ▼
Bronze (SCHEMA_RAW) ────────────────────────┐
Raw claims, members,                         │
document chunks                              │
    │                                        │
    ▼                                        │
Silver (SCHEMA_CURATED)                      │
Cleansed, standardized,                      │
deduplicated                                 │
    │                                        ▼
    ▼                              Cortex Search Services
Gold (SCHEMA_GOLD)                 ┌─ MEASURE_DOC_SEARCH
Analytics marts,                    ├─ POLICY_DOC_SEARCH
risk profiles,                      ├─ CLINICAL_GUIDANCE_SEARCH
audit log                           └─ SAFETY_BULLETIN_SEARCH
    │                                        │
    ▼                                        │
Semantic Layer                               │
(SCHEMA_SEMANTIC)                            │
Cortex Analyst YAML                          │
    │                                        │
    ▼                                        ▼
         Cortex Agent Orchestrator
         ┌────────────────────────────────────┐
         │  Route → Specialized Agent         │
         │  ├─ Measure Interpretation         │
         │  ├─ Patient Safety Gap Detection   │
         │  ├─ Outreach Recommendation        │
         │  ├─ Stars Performance Analytics    │
         │  └─ Audit / Explainability         │
         └────────────────────────────────────┘
                          │
                          ▼
                 Streamlit in Snowflake App
                 ├─ Measure Explorer
                 ├─ Gap Dashboard
                 ├─ Member Detail
                 ├─ Intervention Recommender
                 ├─ Stars Performance
                 └─ Audit Trail
```

---

## 3. Reference Repo Mapping

| Reference Component | CMS Stars Component |
|---|---|
| `python/config.py` | `python/config.py` — Agent, schema, role, measure domain configs |
| `python/generate_structured.py` | `python/generate_sample_data.py` — Synthetic healthcare data |
| `python/create_cortex_search.py` | `python/create_cortex_search.py` — 4 Cortex Search services |
| `python/create_semantic_views.py` | `python/create_semantic_models.py` — Cortex Analyst YAML |
| `python/create_agents.py` | `python/create_agents.py` — 5 specialized Cortex Agents |
| `python/build_ai.py` | `python/build_ai.py` — Build orchestration |
| `python/main.py` | `python/main.py` — CLI pipeline |
| `scripts/setup.sql` | `sql/setup.sql` — Full Snowflake DDL |
| `scripts/teardown.sql` | `sql/teardown.sql` — Cleanup |
| `content_library/regulatory/` | `content_library/measures/` — CMS/PQA measure docs |
| `content_library/_rules/` | `content_library/_rules/` — Measure rule YAML |

**New components** (healthcare-specific, not in reference):
- `governance/` — PHI classification, RBAC, masking policies
- `monitoring/evaluation_framework.py` — Agent quality evaluation
- `data_contracts/` — Schema contracts with PHI flags
- `agents/routing.py` — Intent-based query routing

---

## 4. Multi-Agent Design

### Design decision: Orchestrated multi-agent with specialized sub-agents

**Why not a single agent?**
- Different agents need different tools and retrieval sources
- Clinical safety requires isolation between gap detection and recommendation
- Audit requirements demand separate explainability capability
- Performance queries require different semantic models

**Why not fully autonomous sub-agents?**
- Healthcare requires predictable, traceable behavior
- Human review checkpoints must be enforced
- Simpler for MVP — routing logic is explicit and testable

### Agent Responsibilities

| Agent | Inputs | Outputs | Key Tools |
|---|---|---|---|
| Measure Interpretation | User question | Measure explanation + evidence | Cortex Search (measure docs) |
| Patient Safety Gap Detection | Contract/measure/year | Risk member list + scores | SQL gap query tools |
| Outreach Recommendation | Member surrogate ID + gap | Ranked interventions | Policy docs + intervention history |
| Stars Performance Analytics | Contract/measure/year | Performance metrics + trends | Cortex Analyst (semantic model) |
| Audit/Explainability | Audit ID / member ID | Evidence chain + rule references | Audit log + measure docs |

---

## 5. Governance Summary

| Control | Implementation | Mandatory? |
|---|---|---|
| PHI masking | Dynamic masking policies on member_id, paid_amount | YES |
| Row-level security | Contract-based access policy | YES |
| Audit logging | AGENT_AUDIT_LOG table, every query | YES |
| Prompt PHI redaction | Surrogate IDs only in LLM context | YES |
| Small-cell suppression | < 11 members = suppressed | YES |
| Human review flag | All gap/recommendation outputs | YES |
| Measure spec validation | spec_confirmed flag in MEASURE_DEFINITIONS | YES |

---

## 6. Measure Logic Framework

All measure logic uses a **metadata-driven design**:

1. `MEASURE_DEFINITIONS` table stores denominator/numerator descriptions
2. `spec_confirmed` flag distinguishes validated vs assumed logic
3. Version-controlled by `measure_version` and `measurement_year`
4. Yearly CMS changes → new row inserted, not existing row modified
5. Agent prompts always check `spec_confirmed` and include caveats

### Key principle
> Never hardcode measure thresholds or drug lists in application code.
> Always load from the MEASURE_DEFINITIONS table and validate against
> official CMS/PQA technical specifications.

---

## 7. Reusability

This architecture can be reused for:

| Use Case | Reused | Changed |
|---|---|---|
| Medication Adherence | All infrastructure, agents, app | Measure rules only |
| MTM Optimization | All infrastructure | Intervention tools, MTM docs |
| HEDIS Quality | All infrastructure | HEDIS measure definitions |
| Provider Scorecards | Performance agent, analytics | Provider data model |
| Care Management | Gap detection, outreach agents | Diagnosis-based gap logic |
