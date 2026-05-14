from __future__ import annotations


class Plugin:
    """Extension point for future features (auth, tools, telemetry hooks)."""

    def before_user_message(self, text: str) -> str:
        return text

    def after_assistant_message(self, text: str) -> None:
        return None
