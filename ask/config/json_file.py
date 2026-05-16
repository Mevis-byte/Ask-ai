from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_config_file(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("config.json root must be an object")
    return data


def write_config_file(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, indent=2)
    path.write_text(raw, encoding="utf-8")
