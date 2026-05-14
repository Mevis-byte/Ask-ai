from __future__ import annotations

import os
from pathlib import Path


def resolve_config_path() -> Path | None:
    """Pick config.json: ASK_CONFIG_PATH (required if set), then ./config.json, then ~/.config/ask/config.json."""
    explicit = os.getenv("ASK_CONFIG_PATH")
    if explicit:
        path = Path(explicit).expanduser()
        if not path.is_file():
            msg = f"ASK_CONFIG_PATH is set but file not found: {path}"
            raise FileNotFoundError(msg)
        return path

    cwd_file = Path.cwd() / "config.json"
    if cwd_file.is_file():
        return cwd_file

    xdg = Path.home() / ".config" / "ask" / "config.json"
    if xdg.is_file():
        return xdg

    return None
