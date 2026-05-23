from __future__ import annotations

import os
import re
from pathlib import Path


class InputValidationError(ValueError):
    """Raised when user input fails validation checks."""


_MAX_MODEL_NAME_LENGTH = 128
_MAX_FILE_PATH_LENGTH = 1024
_MAX_PATTERN_LENGTH = 512
_MAX_MESSAGE_LENGTH = 65536
_MAX_PATHSPEC_LENGTH = 512
_MAX_COMMAND_ARGS = 32

_PATH_TRAVERSAL_PATTERNS = re.compile(
    r"(?:^|[/\\])\.\.(?:[/\\]|$)|"
    r"(?:^|[/\\])\.\.\0|"
    r"\0"
)

_INVALID_PATH_CHARS = re.compile(r'[\x00-\x1f\x7f]')

_MODEL_NAME_PATTERN = re.compile(r'^[\w.+\-:/]{1,128}$')

_SANE_FILENAME_RE = re.compile(r'^[\w.\-/\@\[\\\]\^ `~!#$%&\'()+{}\[\] ]+$')


def sanitize_path(user_path: str) -> str:
    if not isinstance(user_path, str) or not user_path.strip():
        raise InputValidationError("Path must be a non-empty string")
    if len(user_path) > _MAX_FILE_PATH_LENGTH:
        raise InputValidationError(f"Path exceeds maximum length ({_MAX_FILE_PATH_LENGTH})")

    if _INVALID_PATH_CHARS.search(user_path):
        raise InputValidationError("Path contains invalid control characters")

    if _PATH_TRAVERSAL_PATTERNS.search(user_path):
        raise InputValidationError("Path traversal detected (../ or null bytes)")

    expanded = os.path.expanduser(user_path.strip())
    resolved = os.path.realpath(expanded)

    if not os.path.exists(resolved) and not user_path.startswith("~"):
        parent = os.path.dirname(resolved)
        if parent and not os.path.isdir(parent):
            raise InputValidationError(f"Parent directory does not exist: {parent}")

    return resolved


def validate_model_name(name: str) -> str:
    if not isinstance(name, str) or not name.strip():
        raise InputValidationError("Model name must be a non-empty string")
    name = name.strip()
    if len(name) > _MAX_MODEL_NAME_LENGTH:
        raise InputValidationError(f"Model name exceeds {_MAX_MODEL_NAME_LENGTH} characters")
    if not _MODEL_NAME_PATTERN.match(name):
        raise InputValidationError(
            "Model name contains invalid characters. Use letters, digits, dots, hyphens, colons, underscores."
        )
    if ".." in name or name.startswith("-"):
        raise InputValidationError("Invalid model name format")
    return name


def validate_pathspec(pathspec: str) -> str:
    if not isinstance(pathspec, str) or not pathspec.strip():
        raise InputValidationError("Pathspec must be a non-empty string")
    pathspec = pathspec.strip()
    if len(pathspec) > _MAX_PATHSPEC_LENGTH:
        raise InputValidationError(f"Pathspec exceeds {_MAX_PATHSPEC_LENGTH} characters")
    if _INVALID_PATH_CHARS.search(pathspec):
        raise InputValidationError("Pathspec contains invalid control characters")
    if _PATH_TRAVERSAL_PATTERNS.search(pathspec):
        raise InputValidationError("Path traversal detected in pathspec")
    if not _SANE_FILENAME_RE.match(pathspec):
        raise InputValidationError("Pathspec contains disallowed characters")
    return pathspec


def validate_search_pattern(pattern: str) -> str:
    if not isinstance(pattern, str) or not pattern.strip():
        raise InputValidationError("Search pattern must be a non-empty string")
    pattern = pattern.strip()
    if len(pattern) > _MAX_PATTERN_LENGTH:
        raise InputValidationError(f"Search pattern exceeds {_MAX_PATTERN_LENGTH} characters")
    if len(pattern) < 2:
        raise InputValidationError("Search pattern must be at least 2 characters")
    if _INVALID_PATH_CHARS.search(pattern):
        raise InputValidationError("Search pattern contains invalid characters")
    return pattern


def validate_user_message(message: str) -> str:
    if not isinstance(message, str):
        raise InputValidationError("Message must be a string")
    message = message.strip()
    if not message:
        raise InputValidationError("Message cannot be empty")
    if len(message) > _MAX_MESSAGE_LENGTH:
        raise InputValidationError(f"Message exceeds {_MAX_MESSAGE_LENGTH} characters")
    if _INVALID_PATH_CHARS.search(message):
        raise InputValidationError("Message contains invalid control characters")
    return message


def validate_command_arg(arg: str, max_len: int = 256) -> str:
    if not isinstance(arg, str):
        raise InputValidationError("Command argument must be a string")
    arg = arg.strip()
    if len(arg) > max_len:
        raise InputValidationError(f"Command argument exceeds {max_len} characters")
    if _INVALID_PATH_CHARS.search(arg):
        raise InputValidationError("Command argument contains invalid control characters")
    return arg
