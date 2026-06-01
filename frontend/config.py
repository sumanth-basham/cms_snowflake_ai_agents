"""
frontend/config.py — Frontend configuration and API client settings.
"""

import os

# API base URL (defaults to local FastAPI server)
API_BASE_URL = os.getenv("FRONTEND_API_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))

# Page appearance
PAGE_TITLE = "CMS Stars AI Agents"
PAGE_ICON = "💊"
LAYOUT = "wide"

# Predefined analytics templates for quick-start queries
ANALYTICS_TEMPLATES = [
    {
        "label": "Top Drug Classes by Adherence",
        "question": "What is the average medication adherence rate (PDC) by therapeutic class for all measurement years?",
        "category": "Adherence",
    },
    {
        "label": "Regional Adherence Comparison",
        "question": "Which regions (states) have the lowest average PDC ratio for cardiovascular medications (statins, ACE inhibitors, ARBs)?",
        "category": "Adherence",
    },
    {
        "label": "Non-Adherent Members by Age Group",
        "question": "How many members in each age group (65-74, 75-84, 85+) have a PDC ratio below 0.80 for any therapeutic class?",
        "category": "Risk",
    },
    {
        "label": "Prescription Gap Analysis",
        "question": "Show the average number of gap days per member by therapeutic class and measurement year.",
        "category": "Gaps",
    },
    {
        "label": "Monthly Adherence Trend (Statins)",
        "question": "Show the monthly trend of statin adherence fill activity for 2024, broken down by region.",
        "category": "Trends",
    },
    {
        "label": "High-Risk Medication Members",
        "question": "Which therapeutic classes have the highest proportion of members with significant prescription gaps (>= 30 days)?",
        "category": "Risk",
    },
    {
        "label": "Adherence vs. Risk Score Correlation",
        "question": "Show the correlation between total gap days and risk score for members with open patient safety gaps.",
        "category": "Outcomes",
    },
    {
        "label": "LIS vs Non-LIS Adherence",
        "question": "Compare the average PDC ratio between LIS (low income subsidy) and non-LIS members by therapeutic class.",
        "category": "Equity",
    },
]
