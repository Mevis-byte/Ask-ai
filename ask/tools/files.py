from __future__ import annotations

from pathlib import Path
from typing import Literal

from rich.console import Group, RenderableType
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from pygments.lexers import get_lexer_by_name
from pygments.util import ClassNotFound

from ask.files import FileReadResult

FileAnalysisMode = Literal["explain", "summarize", "review"]

_LANG_BY_SUFFIX = {
    ".bash": "bash",
    ".c": "c",
    ".cc": "cpp",
    ".cfg": "ini",
    ".cpp": "cpp",
    ".cs": "csharp",
    ".css": "css",
    ".csv": "csv",
    ".cxx": "cpp",
    ".dockerfile": "docker",
    ".go": "go",
    ".h": "c",
    ".hpp": "cpp",
    ".htm": "html",
    ".html": "html",
    ".ini": "ini",
    ".java": "java",
    ".js": "javascript",
    ".json": "json",
    ".jsx": "jsx",
    ".kt": "kotlin",
    ".lock": "text",
    ".lua": "lua",
    ".md": "markdown",
    ".php": "php",
    ".ps1": "powershell",
    ".py": "python",
    ".rb": "ruby",
    ".rs": "rust",
    ".sh": "bash",
    ".sql": "sql",
    ".toml": "toml",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".txt": "text",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
}

_LANG_BY_NAME = {
    ".gitignore": "gitignore",
    "dockerfile": "docker",
    "makefile": "make",
    "requirements.txt": "requirements",
}


def detect_language(path: Path) -> str:
    """Return a Rich/Pygments lexer alias from a file name or extension."""
    name = path.name.lower()
    if name in _LANG_BY_NAME:
        return _safe_language(_LANG_BY_NAME[name])
    suffixes = [suffix.lower() for suffix in path.suffixes]
    for suffix in reversed(suffixes):
        if suffix in _LANG_BY_SUFFIX:
            return _safe_language(_LANG_BY_SUFFIX[suffix])
    return "text"


def _safe_language(language: str) -> str:
    try:
        get_lexer_by_name(language)
    except ClassNotFound:
        return "text"
    return language


def build_file_read_panel(result: FileReadResult) -> RenderableType:
    """Rich renderable for /read; raw content stays in the Syntax block."""
    language = detect_language(result.path)
    status = "truncated" if result.truncated else "complete"
    header = Text.assemble(
        ("file ", "dim"),
        (result.display_path, "bold"),
        ("  |  language ", "dim"),
        (language, "green"),
        ("  |  bytes ", "dim"),
        (str(result.bytes_read), "cyan"),
        ("  |  ", "dim"),
        (status, "yellow" if result.truncated else "green"),
    )
    if result.content:
        body: RenderableType = Syntax(
            result.content,
            language,
            theme="ansi_dark",
            line_numbers=True,
            word_wrap=False,
        )
    else:
        body = Text("[empty file]", style="dim")
    return Panel(
        Group(header, Text(""), body),
        title="READ ONLY",
        border_style="yellow",
        padding=(1, 1),
    )


def build_file_analysis_prompt(result: FileReadResult, mode: FileAnalysisMode) -> str:
    language = detect_language(result.path)
    truncated_note = (
        "\nThe file was truncated because it exceeded the local read limit. "
        "Base your answer only on the visible content."
        if result.truncated
        else ""
    )
    task = _task_instruction(mode)
    return (
        "You are an offline AI developer assistant analyzing a local project file.\n"
        "Do not execute code. Do not modify files. Do not claim to have changed files.\n"
        f"File: {result.display_path}\n"
        f"Detected language: {language}\n"
        f"Bytes read: {result.bytes_read}{truncated_note}\n\n"
        f"{task}\n\n"
        f"```{language}\n{result.content}\n```"
    )


def _task_instruction(mode: FileAnalysisMode) -> str:
    if mode == "summarize":
        return (
            "Write a short, concise overview of this file. Focus on purpose, main responsibilities, "
            "and any important dependencies. Keep it brief."
        )
    if mode == "review":
        return (
            "Review this code. Prioritize concrete findings and include line or symbol references when possible. "
            "Look for bugs, bad practices, optimization opportunities, security concerns, and readability issues. "
            "Do not suggest automatic edits."
        )
    return (
        "Explain this file in a structured way. Cover what the file does, important functions/classes, "
        "architecture, logic flow, dependencies, and important patterns."
    )
