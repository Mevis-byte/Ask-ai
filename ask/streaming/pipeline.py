from __future__ import annotations

from collections.abc import Callable, Iterable


def iter_ollama_text_deltas(chunks: Iterable[dict]) -> Iterable[str]:
    for chunk in chunks:
        message = chunk.get("message") or {}
        part = message.get("content") or ""
        if part:
            yield part


def fold_ollama_stream(
    chunks: Iterable[dict],
    on_delta: Callable[[str], None] | None = None,
) -> str:
    """Accumulate streamed assistant text; optional per-token sink (e.g. live typing)."""
    buf: list[str] = []
    for delta in iter_ollama_text_deltas(chunks):
        buf.append(delta)
        if on_delta is not None:
            on_delta(delta)
    return "".join(buf)


def collect_stream_text(chunks: Iterable[dict]) -> str:
    return fold_ollama_stream(chunks, on_delta=None)
