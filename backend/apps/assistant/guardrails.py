"""Security Guardrails for BudgetBuddy AI Assistant.

Enforces strict boundaries:
1. Prevents disclosure of passwords, password hashes, JWT tokens, session IDs, and database primary keys.
2. Prevents access to other users' confidential data.
3. Sanitizes model outputs before returning them to the user.
"""

import re
from typing import Optional, Tuple

# Patterns that indicate an attempt to extract confidential credentials
CONFIDENTIAL_PROMPT_PATTERNS = [
    r"\b(password|passwd|pwd|passcode|secret\s*key)\b",
    r"\b(session\s*id|session_id|sessionkey|session\s*token)\b",
    r"\b(jwt|bearer\s*token|access\s*token|refresh\s*token|auth\s*token)\b",
    r"\b(database\s*id|user\s*id|my\s*id|system\s*id|account\s*id|raw\s*id)\b",
    r"\b(other\s*user|all\s*users|other\s*students|database\s*dump|sql\s*injection)\b",
    r"\b(env\s*file|\.env|django_secret|secret_key)\b",
]

# Regex patterns to sanitize from outgoing responses
SENSITIVE_OUTPUT_SCRUBBERS = [
    # JWT tokens
    (r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}", "[REDACTED_TOKEN]"),
    # Bearer tokens
    (r"Bearer\s+[a-zA-Z0-9_\-\.]{15,}", "Bearer [REDACTED]"),
    # PBKDF2 or bcrypt password hashes
    (r"pbkdf2_sha256\$[^\s]+", "[REDACTED_PASSWORD_HASH]"),
    (r"\$2[aby]\$[0-9]{2}\$[^\s]+", "[REDACTED_PASSWORD_HASH]"),
    # Raw IDs in key-value context (e.g. "id: 42", "user_id: 1")
    (r"\b(user_id|session_id|token_id|pk|raw_id)\s*[:=]\s*\d+\b", r"\1: [PROTECTED]"),
]

GUARDRAIL_REJECTION_MESSAGE = (
    "🔒 Security Guardrail Active: For your safety and data privacy, confidential credentials "
    "such as passwords, authentication tokens, session identifiers, and internal database IDs "
    "are strictly protected and can never be displayed or shared.\n\n"
    "I am fully available to help you with your budget limits, spending analysis, daily allowances, "
    "and expense logging!"
)


def evaluate_input_guardrail(query: str) -> Tuple[bool, Optional[str]]:
    """Checks if the user's input asks for confidential, protected information.

    Returns:
        (is_safe, refusal_message)
    """
    clean_query = query.strip().lower()

    # Allow harmless questions like "how do I change my password" by contextual checking
    if "change my password" in clean_query or "forgot password" in clean_query:
        return (
            False,
            "💡 You can change your password securely through your Account Settings or by contacting an administrator. "
            "For security reasons, passwords cannot be viewed or handled inside the chat assistant.",
        )

    for pattern in CONFIDENTIAL_PROMPT_PATTERNS:
        if re.search(pattern, clean_query, re.IGNORECASE):
            return (False, GUARDRAIL_REJECTION_MESSAGE)

    return (True, None)


def sanitize_output(text: str) -> str:
    """Scans and scrubs any sensitive strings (tokens, hashes, session keys) from AI response text."""
    sanitized = text
    for pattern, replacement in SENSITIVE_OUTPUT_SCRUBBERS:
        sanitized = re.sub(pattern, replacement, sanitized)
    return sanitized
