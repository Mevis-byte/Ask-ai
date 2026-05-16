from __future__ import annotations

import re
from dataclasses import dataclass, field


TASK_PATTERNS: list[tuple[str, str, list[str]]] = [
    ("coding", "deepseek-coder:6.7b", [
        r"\bcode\b", r"\bfunction\b", r"\bclass\b", r"\bimplement\b",
        r"\brefactor\b", r"\bdebug\b", r"\breview\b", r"\bbug\b",
        r"\bfix\b", r"\boptimize\b", r"\brewrite\b", r"\bapi\b",
        r"\broute\b", r"\bendpoint\b", r"\bschema\b",
    ]),
    ("summary", "mistral", [
        r"\bsummarize\b", r"\bsummary\b", r"\boverview\b",
        r"\bexplain briefly\b", r"\b tl;dr\b", r"\btldr\b",
        r"\bconcisely\b",
    ]),
    ("analysis", "mistral", [
        r"\banalyze\b", r"\banalysis\b", r"\bwhat does this\b",
        r"\bexplain this\b", r"\bhow does\b",
    ]),
]


@dataclass
class ModelRouter:
    """Route prompts to models based on detected task type."""

    enabled: bool = False
    default_model: str = "llama3"
    coding_model: str = "deepseek-coder:6.7b"
    chat_model: str = "llama3"
    summary_model: str = "mistral"
    _fallback: str = "llama3"

    _patterns: list[tuple[str, str, list[re.Pattern]]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        compiled: list[tuple[str, str, list[re.Pattern]]] = []
        for task, model, raw_patterns in TASK_PATTERNS:
            patterns = [re.compile(p, re.IGNORECASE) for p in raw_patterns]
            compiled.append((task, model, patterns))

        self._patterns = [
            ("coding", self.coding_model, next(p for t, _, p in compiled if t == "coding")),
            ("summary", self.summary_model, next(p for t, _, p in compiled if t == "summary")),
            ("analysis", self.summary_model, next(p for t, _, p in compiled if t == "analysis")),
        ]
        self._fallback = self.chat_model

    def select_model(self, user_message: str, current_model: str | None = None) -> str:
        if not self.enabled:
            return current_model or self._fallback
        if not user_message.strip():
            return current_model or self._fallback
        for task, model, patterns in self._patterns:
            for pattern in patterns:
                if pattern.search(user_message):
                    return model
        return current_model or self._fallback

    def task_label(self, user_message: str) -> str:
        if not self.enabled:
            return "chat"
        for task, _, patterns in self._patterns:
            for pattern in patterns:
                if pattern.search(user_message):
                    return task
        return "chat"
