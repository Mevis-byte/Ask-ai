from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


@dataclass
class AnalyzedFile:
    path: str
    mode: str
    language: str
    summary: str | None = None


@dataclass
class ContextState:
    workspace_root: str | None = None
    project_languages: list[str] = field(default_factory=list)
    project_frameworks: list[str] = field(default_factory=list)
    analyzed_files: list[AnalyzedFile] = field(default_factory=list)
    discussed_topics: list[str] = field(default_factory=list)
    current_focus: str | None = None

    def track_analysis(self, path: str, mode: str, language: str) -> None:
        existing = {a.path for a in self.analyzed_files}
        if path not in existing:
            self.analyzed_files.append(AnalyzedFile(path=path, mode=mode, language=language))

    def track_topic(self, topic: str) -> None:
        topic_lower = topic.lower().strip()
        if topic_lower and (not self.discussed_topics or self.discussed_topics[-1].lower() != topic_lower):
            self.discussed_topics.append(topic)
            if len(self.discussed_topics) > 20:
                self.discussed_topics = self.discussed_topics[-20:]

    def get_context_for_prompt(self) -> str:
        parts: list[str] = []
        if self.workspace_root:
            parts.append(f"Active workspace: {self.workspace_root}")
            if self.project_languages:
                parts.append(f"Project languages: {', '.join(self.project_languages)}")
            if self.project_frameworks:
                parts.append(f"Frameworks: {', '.join(self.project_frameworks)}")
        if self.analyzed_files:
            analyzed = ", ".join(f.path for f in self.analyzed_files[-6:])
            parts.append(f"Previously analyzed files: {analyzed}")
        if self.discussed_topics:
            topics = ", ".join(self.discussed_topics[-4:])
            parts.append(f"Recent discussion topics: {topics}")
        return "\n".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_root": self.workspace_root,
            "project_languages": self.project_languages,
            "project_frameworks": self.project_frameworks,
            "analyzed_files": [asdict(f) for f in self.analyzed_files[-20:]],
            "discussed_topics": self.discussed_topics[-20:],
            "current_focus": self.current_focus,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ContextState:
        analyzed = [AnalyzedFile(**f) for f in data.get("analyzed_files", [])]
        return cls(
            workspace_root=data.get("workspace_root"),
            project_languages=data.get("project_languages", []),
            project_frameworks=data.get("project_frameworks", []),
            analyzed_files=analyzed,
            discussed_topics=data.get("discussed_topics", []),
            current_focus=data.get("current_focus"),
        )


class ContextTracker:
    """Maintains persistent context state across sessions and turns."""

    def __init__(self) -> None:
        self._state = ContextState()
        self._on_change: list[callable] = []

    @property
    def state(self) -> ContextState:
        return self._state

    def on_change(self, callback: callable) -> None:
        self._on_change.append(callback)

    def set_workspace(self, root: str | None, languages: list[str] | None = None,
                      frameworks: list[str] | None = None) -> None:
        self._state.workspace_root = root
        if languages is not None:
            self._state.project_languages = languages
        if frameworks is not None:
            self._state.project_frameworks = frameworks
        self._notify()

    def track_file_analysis(self, path: str, mode: str, language: str) -> None:
        self._state.track_analysis(path, mode, language)
        self._notify()

    def track_topic(self, topic: str) -> None:
        self._state.track_topic(topic)
        self._notify()

    def get_session_context(self) -> str:
        return self._state.get_context_for_prompt()

    def serialize(self) -> str:
        return json.dumps(self._state.to_dict())

    @classmethod
    def deserialize(cls, data: str) -> ContextTracker:
        tracker = cls()
        try:
            parsed = json.loads(data)
            tracker._state = ContextState.from_dict(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
        return tracker

    def _notify(self) -> None:
        for cb in self._on_change:
            try:
                cb()
            except Exception:
                pass
