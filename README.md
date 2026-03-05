# CMS Snowflake AI Agents — Medicare Part D Patient Safety Stars

> **Enterprise Snowflake Cortex Agent Solution for Medicare Part D Patient Safety Star Measures and Quality Operations**

---

## Executive Summary

This repository delivers a production-oriented **multi-agent AI solution** built on **Snowflake Cortex Agents** for Medicare Part D Patient Safety Star Measures. It is adapted from the [sfguide-agentic-ai-for-asset-management](https://github.com/sumanth-basham/sfguide-agentic-ai-for-asset-management) architecture pattern and redesigned for healthcare quality operations.

The system enables health plans, PBMs, pharmacy quality teams, and medication safety operations teams to:

1. **Interpret** CMS/PQA measure logic (denominator, numerator, exclusions, thresholds)
2. **Detect** medication safety gaps from real-world claims and member data
3. **Prioritize** high-risk members for outreach
4. **Explain** why a member or contract segment is at risk
5. **Recommend** evidence-based interventions
6. **Support** quality improvement operations and compliance
7. **Trace** every AI decision to supporting data evidence

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CMS SNOWFLAKE AI AGENTS                              │
│              Medicare Part D Patient Safety Stars Solution                   │
└─────────────────────────────────────────────────────────────────────────────┘

SOURCE SYSTEMS
─────────────────────────────────────────────────────
  Pharmacy Claims │ PDE Data │ Member Enrollment
  Prescriber Data │ Pharmacy Data │ NDC/RxNorm Refs
  MTM Logs │ CMS/PQA Docs │ Formulary Data

         │
         ▼

INGESTION LAYER (Snowpipe / External Stages)
─────────────────────────────────────────────────────
  Raw file landing zones (CSV, JSON, Parquet)
  Schema-on-read staging tables

         │
         ▼

BRONZE LAYER (RAW — SCHEMA_RAW)
─────────────────────────────────────────────────────
  RAW_PHARMACY_CLAIMS  │  RAW_PDE_EVENTS
  RAW_MEMBERS          │  RAW_ENROLLMENT
  RAW_PROVIDERS        │  RAW_PHARMACIES
  RAW_DRUG_REFERENCE   │  RAW_MTM_INTERVENTIONS
  RAW_DOCUMENT_CHUNKS  │  RAW_MEASURE_DEFINITIONS

         │
         ▼

SILVER LAYER (CURATED — SCHEMA_CURATED)
─────────────────────────────────────────────────────
  MEMBERS              │  ENROLLMENT
  PHARMACY_CLAIMS      │  DRUG_REFERENCE
  PROVIDERS            │  PHARMACIES
  MTM_INTERVENTIONS    │  PATIENT_SAFETY_GAPS
  MEASURE_DEFINITIONS  │  MEASURE_EXCLUSION_LOGIC

         │
         ▼

GOLD LAYER (ANALYTICS MARTS — SCHEMA_GOLD)
─────────────────────────────────────────────────────
  STARS_MEASURE_FACT          │  CONTRACT_PERFORMANCE_SUMMARY
  MEMBER_RISK_PROFILE         │  INTERVENTION_RECOMMENDATIONS
  ADHERENCE_HISTORY           │  PROVIDER_QUALITY_SCORECARD
  AGENT_AUDIT_LOG             │  EVALUATION_METRICS

         │
         ▼

RETRIEVAL LAYER (Cortex Search)
─────────────────────────────────────────────────────
  MEASURE_DOC_SEARCH   │  POLICY_DOC_SEARCH
  CLINICAL_GUIDANCE    │  SAFETY_BULLETIN_SEARCH

         │
         ▼

SEMANTIC / ANALYTICS LAYER (Cortex Analyst)
─────────────────────────────────────────────────────
  Stars Performance Semantic Model
  Member Risk Semantic Model
  Contract Performance Semantic Model

         │
         ▼

AGENT ORCHESTRATION LAYER (Snowflake Cortex Agents)
─────────────────────────────────────────────────────
  ┌──────────────────────────────────────────────┐
  │  ORCHESTRATOR AGENT (Router)                  │
  │  ┌───────────────┐  ┌────────────────────┐   │
  │  │  Measure       │  │  Patient Safety    │   │
  │  │  Interpretation│  │  Gap Detection     │   │
  │  │  Agent        │  │  Agent             │   │
  │  └───────────────┘  └────────────────────┘   │
  │  ┌───────────────┐  ┌────────────────────┐   │
  │  │  Outreach      │  │  Stars Performance │   │
  │  │  Recommendation│  │  Analytics Agent   │   │
  │  │  Agent        │  │                    │   │
  │  └───────────────┘  └────────────────────┘   │
  │  ┌───────────────┐                            │
  │  │  Audit /       │                            │
  │  │  Explainability│                            │
  │  │  Agent        │                            │
  │  └───────────────┘                            │
  └──────────────────────────────────────────────┘

         │
         ▼

APP LAYER (Streamlit in Snowflake)
─────────────────────────────────────────────────────
  Measure Explorer │ Gap Dashboard │ Member Detail
  Intervention Recommender │ Performance Trends
  Audit Trail Viewer │ Analyst Review Capture

         │
         ▼

SECURITY / GOVERNANCE / MONITORING
─────────────────────────────────────────────────────
  RBAC │ Column Masking │ Row-Level Security
  PHI Classification │ Prompt Redaction
  Agent Audit Log │ Evaluation Metrics
  Latency / Cost Tracking │ Drift Detection
```

---

## Multi-Agent Design

| Agent | Purpose | Primary Users |
|---|---|---|
| **Measure Interpretation Agent** | Explains CMS/PQA measure logic, denominator/numerator, exclusions, thresholds | Quality analysts, ops teams |
| **Patient Safety Gap Detection Agent** | Detects members at risk for measure failure or medication safety issues | Pharmacy quality, MTM teams |
| **Outreach Recommendation Agent** | Recommends pharmacist review, provider/member outreach, formulary alternatives | Care management, quality ops |
| **Stars Performance Analytics Agent** | Analyzes contract/plan/region/provider performance trends | Quality directors, leadership |
| **Audit/Explainability Agent** | Explains AI decisions with evidence: which data, rule, and confidence | Compliance, auditors, clinical leads |

---

## Repository Structure

```
cms_snowflake_ai_agents/
├── app/                        # Streamlit in Snowflake UI
├── agents/                     # Agent definitions and orchestration
├── prompts/                    # Production-grade prompt pack for all agents
├── tools/                      # Custom Snowpark/Python tools for agents
├── sql/                        # Snowflake SQL (setup, schemas, DDL, queries)
│   ├── bronze/                 # Raw layer DDL
│   ├── silver/                 # Curated layer DDL
│   ├── gold/                   # Analytics mart DDL
│   └── semantic/               # Semantic views for Cortex Analyst
├── data_contracts/             # Schema contracts and data dictionaries
├── semantic_models/            # Cortex Analyst YAML semantic models
├── content_library/            # CMS/PQA documents for Cortex Search
│   ├── measures/               # Measure specification documents
│   ├── policy/                 # Plan policy documents
│   ├── clinical_guidance/      # Clinical and safety guidance
│   ├── safety_bulletins/       # Safety bulletins
│   └── _rules/                 # Measure rule metadata YAML
├── python/                     # Core Python modules
├── notebooks/                  # Snowflake/Jupyter walkthrough notebooks
├── tests/                      # Unit and integration tests
├── docs/                       # Architecture and design documentation
├── deployment/                 # CI/CD and environment setup
├── monitoring/                 # Evaluation framework and metrics
└── governance/                 # Security, RBAC, masking policies
```

---

## Quick Start

### Prerequisites

- Snowflake account with Cortex enabled
- Python 3.10+
- Snowflake Python connector

### Setup

```bash
# Clone the repository
git clone https://github.com/sumanth-basham/cms_snowflake_ai_agents.git
cd cms_snowflake_ai_agents

# Install Python dependencies
pip install -r requirements.txt

# Copy and configure environment
cp deployment/.env.template .env
# Edit .env with your Snowflake credentials

# Run Snowflake setup (creates database, schemas, tables)
python python/main.py --step setup

# Load sample data
python python/main.py --step load_data

# Build Cortex Search indexes
python python/main.py --step build_search

# Create semantic models
python python/main.py --step build_semantic

# Deploy agents
python python/main.py --step deploy_agents
```

---

## Measure Coverage

This solution is designed to support **Medicare Part D Patient Safety Star Measures**, including but not limited to:

| Measure Domain | Examples (Verify with official CMS/PQA specs) |
|---|---|
| High-Risk Medication (HRM) | Older adults on potentially inappropriate medications |
| Drug-Drug Interaction (DDI) | Concurrent use of contraindicated drug combinations |
| Statin Use in Persons with Diabetes (SUPD) | Diabetes members on statin therapy |
| Medication Adherence (PDC) | Proportion of Days Covered for diabetes, RASA, statin |
| MTM Completion | Comprehensive Medication Review (CMR) completion rates |

> **⚠️ IMPORTANT**: Measure logic in this repository represents architectural design patterns and sample configurations only. All measure specifications must be validated against official CMS/PQA technical specifications and confirmed by qualified clinical/regulatory SMEs before use in production.

---

## Security and Governance

This solution implements a full healthcare data governance framework:

- **PHI/PII Classification**: All columns tagged with sensitivity level
- **Dynamic Data Masking**: Member identity masked by default for non-clinical roles
- **Row-Level Security**: Contract/plan segment isolation
- **Audit Logging**: All agent queries and responses logged with evidence
- **Prompt Redaction**: PHI stripped from LLM context before API calls
- **RBAC**: Roles for analyst, clinical, admin, and auditor personas

---

## Learning Path

This repository is organized for **beginner to architect** progression:

1. **Start here**: `docs/01_business_problem.md`
2. **Understand the data**: `docs/02_data_model.md`
3. **Learn the agents**: `docs/03_agent_design.md`
4. **Explore the prompts**: `prompts/`
5. **Run the notebooks**: `notebooks/`
6. **Production deployment**: `deployment/`

---

## License

See [LICENSE](LICENSE) for details.

> This solution is provided as an architectural reference and educational guide. It does not constitute medical, clinical, or regulatory advice. All CMS Stars measure logic must be validated against official CMS/PQA technical specifications.
