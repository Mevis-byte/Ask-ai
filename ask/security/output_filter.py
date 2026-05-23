from __future__ import annotations

import re


_REMOVE_ANSI_ESCAPE = re.compile(r'\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
_KNOWN_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r'(?i)(?:api[_-]?key|secret|token|password|passwd|credential)\s*[:=]\s*\S+'),
    re.compile(r'(?:-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----)'),
    re.compile(r'(?:ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22,})'),
    re.compile(r'(?:sk-[a-zA-Z0-9]{32,})'),
    re.compile(r'(?:AKIA[0-9A-Z]{16})'),
    re.compile(r'(?:AIza[0-9A-Za-z\-_]{35})'),
]


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return _REMOVE_ANSI_ESCAPE.sub("", text)


def redact_secrets(text: str, replacement: str = "***REDACTED***") -> str:
    """Redact known secret patterns from text to prevent leakage."""
    result = text
    for pattern in _KNOWN_SECRET_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def safe_markdown(text: str) -> str:
    """Sanitize AI output for safe Markdown rendering.

    - Strips ANSI escapes
    - Redacts secrets
    - Limits total length
    - Removes potentially dangerous HTML
    """
    text = strip_ansi(text)
    text = redact_secrets(text)
    text = text[:100000]
    text = _strip_dangerous_html(text)
    return text


_DANGEROUS_HTML_TAGS = re.compile(
    r'<\s*(?:script|iframe|embed|object|applet|meta|link|style|form|input|button|'
    r'onerror|onload|onclick|onmouseover|onfocus|onblur|onchange|onsubmit)'
    r'[^>]*>',
    re.IGNORECASE,
)
_HTML_EVENT_HANDLERS = re.compile(
    r'\son\w+\s*=\s*["\'][^"\']*["\']',
    re.IGNORECASE,
)
_JAVASCRIPT_PROTOCOL = re.compile(r'javascript\s*:', re.IGNORECASE)


def _strip_dangerous_html(text: str) -> str:
    text = _DANGEROUS_HTML_TAGS.sub("", text)
    text = _HTML_EVENT_HANDLERS.sub("", text)
    text = _JAVASCRIPT_PROTOCOL.sub("", text)
    return text
