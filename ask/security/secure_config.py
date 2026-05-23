from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

_SECRET_PATTERN = re.compile(
    r'(?i)(?:api[_-]?key|secret|token|password|passwd|credential|'
    r'private[_-]?key|access[_-]?key|auth[_-]?token|'
    r'session[_-]?secret|db[_-]?url|database[_-]?url|'
    r'connection[_-]?string|jwt[_-]?secret|encryption[_-]?key)'
    r'\s*[:=]\s*["\']?[^"\'{}\[\],;\s]{8,}["\']?',
    re.IGNORECASE,
)


def detect_secrets_in_dict(data: dict[str, Any], path: str = "") -> list[str]:
    """Recursively scan a config dict for potential secrets."""
    findings: list[str] = []
    for key, value in data.items():
        current_path = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            findings.extend(detect_secrets_in_dict(value, current_path))
        elif isinstance(value, str):
            if _SECRET_PATTERN.search(f"{key}: {value}"):
                findings.append(f"Potential secret in config key: {current_path}")
            if _looks_like_secret(value):
                findings.append(f"Secret-like value in config key: {current_path}")
    return findings


def _looks_like_secret(value: str) -> bool:
    if len(value) < 16:
        return False
    high_entropy_patterns = [
        r'^[A-Za-z0-9+/]{40,}={0,2}$',
        r'^[A-Fa-f0-9]{32,}$',
        r'^[A-Za-z0-9\-_]{20,}$',
    ]
    for pattern in high_entropy_patterns:
        if re.match(pattern, value):
            return True
    return False


def validate_config_file_permissions(path: Path) -> list[str]:
    """Check that config files have appropriate permissions."""
    warnings: list[str] = []
    if not path.exists():
        return warnings
    try:
        mode = path.stat().st_mode
        if mode & 0o007:
            warnings.append(
                f"Config file {path} is world-readable "
                f"(permissions: {oct(mode & 0o777)}). "
                f"Run: chmod 600 {path}"
            )
        if mode & 0o077:
            warnings.append(
                f"Config file {path} is group-accessible "
                f"(permissions: {oct(mode & 0o777)}). "
                f"Run: chmod 600 {path}"
            )
    except OSError:
        pass
    return warnings


_SENSITIVE_ENV_KEYS = {
    "ASK_OLLAMA_HOST",
    "ASK_MEMORY_PERSIST_PATH",
    "ASK_RAG_PERSIST_DIR",
    "ASK_CHAT_MODEL",
    "ASK_ANALYZE_MODEL",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
}

_ENV_VALUE_PATTERNS = re.compile(
    r'(?i)(?:key|secret|token|password|credential)'
)


def validate_environment() -> list[str]:
    """Check environment variables for security issues."""
    warnings: list[str] = []
    for key in _SENSITIVE_ENV_KEYS:
        value = os.environ.get(key)
        if value and _ENV_VALUE_PATTERNS.search(key):
            if len(value) > 8 and not value.startswith("$("):
                pass
    return warnings
