from __future__ import annotations

import copy
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ask.config.defaults import BUILTIN_DEFAULTS
from ask.config.json_file import read_config_file
from ask.config.merge import deep_merge
from ask.config.paths import resolve_config_path


def _env_str(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def _env_bool(name: str) -> bool | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _env_opt_int(name: str) -> int | None:
    """Return None if unset; raise if invalid when set."""
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return int(raw.strip())


def _env_float(name: str) -> float | None:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return None
    return float(raw.strip())


def _apply_env_overrides(cfg: dict[str, Any]) -> None:
    """Environment variables override config.json (12-factor style)."""
    v = _env_str("ASK_OLLAMA_HOST")
    if v is not None:
        cfg["models"]["ollama_host"] = v
    v = _env_str("ASK_CHAT_MODEL")
    if v is not None:
        cfg["models"]["chat_model"] = v
    v = _env_str("ASK_ANALYZE_MODEL")
    if v is not None:
        cfg["models"]["analyze_model"] = v

    b = _env_bool("ASK_RAG_ENABLED")
    if b is not None:
        cfg["rag"]["enabled"] = b
    vi = _env_opt_int("ASK_RAG_TOP_K")
    if vi is not None:
        cfg["rag"]["top_k"] = vi

    b = _env_bool("ASK_CHAT_STREAM")
    if b is not None:
        cfg["streaming"]["live_markdown"] = b
    vf = _env_float("ASK_STREAM_REFRESH_PER_SECOND")
    if vf is not None:
        cfg["streaming"]["refresh_per_second"] = vf

    vi = _env_opt_int("ASK_MEMORY_MAX_MESSAGES")
    if vi is not None:
        cfg["memory"]["max_messages"] = vi
    v = _env_str("ASK_MEMORY_PERSIST_PATH")
    if v is not None:
        cfg["memory"]["persist_path"] = v
    b = _env_bool("ASK_MEMORY_CONTEXT_ENABLED")
    if b is not None:
        cfg["memory"]["context_search_enabled"] = b
    vi = _env_opt_int("ASK_MEMORY_CONTEXT_TOP_K")
    if vi is not None:
        cfg["memory"]["context_search_top_k"] = vi
    vi = _env_opt_int("ASK_MEMORY_CONTEXT_EXCLUDE_RECENT")
    if vi is not None:
        cfg["memory"]["context_exclude_recent_messages"] = vi

    v = _env_str("ASK_UI_BANNER_FONT")
    if v is not None:
        cfg["ui"]["banner_font"] = v
    v = _env_str("ASK_UI_BANNER_TITLE")
    if v is not None:
        cfg["ui"]["banner_title"] = v
    v = _env_str("ASK_UI_BANNER_SUBTITLE")
    if v is not None:
        cfg["ui"]["banner_subtitle"] = v
    b = _env_bool("ASK_UI_SHOW_BANNER_ON_AI")
    if b is not None:
        cfg["ui"]["show_banner_on_ai_command"] = b
    v = _env_str("ASK_UI_CHAT_HEADER")
    if v is not None:
        cfg["ui"]["chat_header"] = v
    v = _env_str("ASK_UI_EXIT_HINT")
    if v is not None:
        cfg["ui"]["exit_hint"] = v
    b = _env_bool("ASK_UI_SHOW_RESPONSE_LABEL")
    if b is not None:
        cfg["ui"]["show_response_label"] = b
    v = _env_str("ASK_UI_RESPONSE_LABEL")
    if v is not None:
        cfg["ui"]["response_label"] = v
    b = _env_bool("ASK_UI_STARTUP_ANIMATION")
    if b is not None:
        cfg["ui"]["startup_animation"] = b
    vf = _env_float("ASK_UI_TYPING_DELAY_MS")
    if vf is not None:
        cfg["ui"]["typing_delay_ms"] = vf


@dataclass(frozen=True)
class Settings:
    """Effective configuration (defaults + config.json + environment)."""

    ollama_host: str
    chat_model: str
    analyze_model: str
    rag_enabled: bool
    rag_top_k: int
    chat_live_stream: bool
    stream_refresh_per_second: float
    memory_max_messages: int | None
    memory_persist_path: str | None
    memory_context_search_enabled: bool
    memory_context_search_top_k: int
    memory_context_exclude_recent: int
    ui_banner_font: str
    ui_banner_title: str
    ui_banner_subtitle: str | None
    show_banner_on_ai_command: bool
    ui_chat_header: str
    ui_exit_hint: str
    ui_show_response_label: bool
    ui_response_label: str
    ui_startup_animation: bool
    ui_typing_delay_ms: float


def _coerce_settings(cfg: dict[str, Any]) -> Settings:
    models = cfg["models"]
    rag = cfg["rag"]
    streaming = cfg["streaming"]
    memory = cfg["memory"]
    ui = cfg["ui"]

    max_msg = memory.get("max_messages")
    if max_msg is not None:
        max_msg = int(max_msg)
        if max_msg <= 0:
            max_msg = None

    subtitle = ui.get("banner_subtitle")
    if subtitle == "":
        subtitle = None

    persist = memory.get("persist_path")
    if persist == "":
        persist = None
    elif persist is not None:
        persist = str(Path(persist).expanduser())

    ctx_top = int(memory.get("context_search_top_k", 6))
    if ctx_top < 1:
        ctx_top = 1

    ctx_exclude = int(memory.get("context_exclude_recent_messages", 24))
    if ctx_exclude < 0:
        ctx_exclude = 0

    ctx_enabled = bool(memory.get("context_search_enabled", True))
    if persist is None:
        ctx_enabled = False

    rps = float(streaming["refresh_per_second"])
    if rps <= 0:
        rps = 20.0

    rag_top = int(rag["top_k"])
    if rag_top < 1:
        rag_top = 1

    typing_ms = float(ui.get("typing_delay_ms", 8.0))
    if typing_ms < 0:
        typing_ms = 0.0
    if typing_ms > 80:
        typing_ms = 80.0

    return Settings(
        ollama_host=str(models["ollama_host"]),
        chat_model=str(models["chat_model"]),
        analyze_model=str(models["analyze_model"]),
        rag_enabled=bool(rag["enabled"]),
        rag_top_k=rag_top,
        chat_live_stream=bool(streaming["live_markdown"]),
        stream_refresh_per_second=rps,
        memory_max_messages=max_msg,
        memory_persist_path=persist,
        memory_context_search_enabled=ctx_enabled,
        memory_context_search_top_k=ctx_top,
        memory_context_exclude_recent=ctx_exclude,
        ui_banner_font=str(ui["banner_font"]),
        ui_banner_title=str(ui["banner_title"]),
        ui_banner_subtitle=str(subtitle) if subtitle is not None else None,
        show_banner_on_ai_command=bool(ui["show_banner_on_ai_command"]),
        ui_chat_header=str(ui["chat_header"]),
        ui_exit_hint=str(ui["exit_hint"]),
        ui_show_response_label=bool(ui["show_response_label"]),
        ui_response_label=str(ui["response_label"]),
        ui_startup_animation=bool(ui.get("startup_animation", True)),
        ui_typing_delay_ms=typing_ms,
    )


def load_settings() -> Settings:
    merged: dict[str, Any] = copy.deepcopy(BUILTIN_DEFAULTS)
    path = resolve_config_path()
    if path is not None:
        deep_merge(merged, read_config_file(path))
    _apply_env_overrides(merged)
    return _coerce_settings(merged)
