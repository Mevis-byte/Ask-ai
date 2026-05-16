from __future__ import annotations

from typing import Any

from ollama import Client


def _format_size(n: int | None) -> str:
    if n is None or n <= 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024.0:
            return f"{n:.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"


class OllamaChatBackend:
    """Ollama-backed `ChatBackend` implementation."""

    def __init__(self, host: str | None = None) -> None:
        self._host = host
        self._client = Client(host=host) if host else Client()

    @property
    def host(self) -> str:
        return self._host or "default"

    def set_host(self, host: str) -> None:
        """Update the Ollama host URL. Handles raw IPs/hostnames by adding http/port."""
        target = host.strip()
        if not target:
            return
        
        # If it doesn't look like a URL, make it one
        if "://" not in target:
            # Check for port
            if ":" not in target:
                target = f"http://{target}:11434"
            else:
                target = f"http://{target}"
        
        self._host = target
        self._client = Client(host=target)

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        stream: bool = False,
    ) -> Any:
        return self._client.chat(model=model, messages=messages, stream=stream)

    def list_installed_models(self) -> list[tuple[str, str]]:
        """Return ``(name, size_label)`` for each local model (sorted by name)."""
        data = self._client.list()
        raw = data.get("models") if isinstance(data, dict) else getattr(data, "models", None)
        rows: list[tuple[str, str]] = []
        if not raw:
            return rows
        for item in raw:
            if isinstance(item, dict):
                name = item.get("name") or item.get("model") or ""
                size = item.get("size")
                if isinstance(size, int):
                    sz: int | None = size
                elif size is not None:
                    try:
                        sz = int(size)
                    except (TypeError, ValueError):
                        sz = None
                else:
                    sz = None
            else:
                name = getattr(item, "model", None) or getattr(item, "name", "") or ""
                sz = getattr(item, "size", None)
                if sz is not None and not isinstance(sz, int):
                    try:
                        sz = int(sz)
                    except (TypeError, ValueError):
                        sz = None
            name = str(name).strip()
            if name:
                rows.append((name, _format_size(sz)))
        rows.sort(key=lambda r: r[0].lower())
        return rows