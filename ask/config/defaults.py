from __future__ import annotations

from typing import Any

# Shape matches config.json sections; used when no file exists or keys are missing.
BUILTIN_DEFAULTS: dict[str, Any] = {
    "models": {
        "ollama_host": "http://127.0.0.1:11434",
        "chat_model": "llama3",
        "analyze_model": "deepseek-coder:6.7b",
    },
    "rag": {
        "enabled": False,
        "top_k": 4,
    },
    "streaming": {
        "live_markdown": True,
        "refresh_per_second": 20.0,
    },
    "memory": {
        "max_messages": 80,
        "persist_path": "~/.local/share/ask/chat.sqlite",
        "context_search_enabled": True,
        "context_search_top_k": 6,
        "context_exclude_recent_messages": 24,
    },
    "ui": {
        "banner_font": "slant",
        "banner_title": "ASK AI",
        "banner_subtitle": "Offline Developer AI Assistant",
        "show_banner_on_ai_command": True,
        "chat_header": "ASK AI Chat (type 'exit' to quit)",
        "exit_hint": "Commands: /model · /models · /help · Type 'exit' to quit",
        "show_response_label": True,
        "response_label": "AI Response:",
        "startup_animation": True,
        "typing_delay_ms": 8.0,
    },
}
