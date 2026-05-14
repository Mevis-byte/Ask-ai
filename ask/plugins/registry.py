from __future__ import annotations

from collections.abc import Sequence

from ask.plugins.base import Plugin


class PluginRegistry:
    def __init__(self, plugins: Sequence[Plugin] | None = None) -> None:
        self._plugins: list[Plugin] = list(plugins or ())

    def register(self, plugin: Plugin) -> None:
        self._plugins.append(plugin)

    def transform_user_message(self, text: str) -> str:
        for plugin in self._plugins:
            text = plugin.before_user_message(text)
        return text

    def notify_assistant(self, text: str) -> None:
        for plugin in self._plugins:
            plugin.after_assistant_message(text)
