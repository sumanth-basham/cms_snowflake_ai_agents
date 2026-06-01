"""
api/utils/validators.py — Input validation and sanitization for API requests.

Validates natural language questions before forwarding to Cortex Analyst.
Guards against overly long inputs, blocked patterns, and empty queries.
"""

import logging
import re
from typing import List

logger = logging.getLogger(__name__)

# Patterns that should not appear in questions forwarded to Cortex Analyst.
# These guard against prompt injection or attempts to exfiltrate credentials.
_BLOCKED_PATTERNS: List[str] = [
    r"(?i)(drop|delete|truncate|insert|update|alter|create|grant|revoke)\s+\w",
    r"(?i)SYSTEM\s*PROMPT",
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)(execute|exec|xp_cmdshell)",
    r"(?i)select\s+\*\s+from\s+information_schema",
    r"(?i)snowflake\.(account_usage|information_schema)",
]

_MAX_QUESTION_LENGTH = 2000


def validate_question(question: str) -> List[str]:
    """
    Validate a natural language question.

    Returns a list of issue strings (empty = valid).
    """
    issues: List[str] = []

    if not question or not question.strip():
        issues.append("Question must not be empty.")
        return issues

    if len(question) > _MAX_QUESTION_LENGTH:
        issues.append(
            f"Question exceeds maximum length of {_MAX_QUESTION_LENGTH} characters."
        )

    for pattern in _BLOCKED_PATTERNS:
        if re.search(pattern, question):
            issues.append(
                "Question contains a disallowed pattern and cannot be processed."
            )
            logger.warning("Blocked question pattern detected: %.80s", question)
            break

    return issues


def sanitize_string(value: str, max_length: int = 256) -> str:
    """Strip whitespace and truncate to max_length."""
    return value.strip()[:max_length]
