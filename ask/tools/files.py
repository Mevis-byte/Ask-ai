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

_PYTHON_IMPORT_RE = __import__("re").compile(
    r'^from\s+([.\w]+)\s+import|\bimport\s+([.\w]+)'
)
_JS_IMPORT_RE = __import__("re").compile(
    r"(?:import\s+(?:\{[^}]*\}|[^;{]+)\s+from\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\))"
)


def detect_language(path: Path) -> str:
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


def extract_imports(text: str, language: str) -> list[str]:
    imports: list[str] = []
    if language == "python":
        for m in _PYTHON_IMPORT_RE.finditer(text):
            imp = m.group(1) or m.group(2)
            if imp:
                imports.append(imp)
    elif language in ("javascript", "typescript", "jsx", "tsx"):
        for m in _JS_IMPORT_RE.finditer(text):
            imp = m.group(1) or m.group(2)
            if imp:
                imports.append(imp)
    return list(dict.fromkeys(imports[:30]))


def format_import_summary(imports: list[str]) -> str:
    if not imports:
        return ""
    return "Imports: " + ", ".join(imports[:20])


def build_file_read_panel(result: FileReadResult) -> RenderableType:
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


def build_file_analysis_prompt(result: FileReadResult, mode: FileAnalysisMode,
                                imports: list[str] | None = None,
                                related_files: list[str] | None = None,
                                session_context: str | None = None) -> str:
    language = detect_language(result.path)
    truncated_note = (
        "\nThe file was truncated because it exceeded the local read limit. "
        "Base your answer only on the visible content."
        if result.truncated
        else ""
    )
    task = _task_instruction(mode)

    parts: list[str] = []
    parts.append(
        "You are ask.ai, an offline local AI developer workstation. "
        "You are analyzing a local project file."
    )
    parts.append("CRITICAL RULES:")
    parts.append("- Only reference code elements you can actually see in the file content above.")
    parts.append("- If you reference imports or dependencies, cite the actual import lines.")
    parts.append("- Do NOT invent file paths, function names, or class names not visible in the file content.")
    parts.append("- Be concise and structured. Use headings, bullet points, and code blocks.")
    parts.append("- Format your response for terminal display — short lines, no walls of text.\n")

    parts.append(f"File: {result.display_path}")
    parts.append(f"Detected language: {language}")
    parts.append(f"Bytes read: {result.bytes_read}{truncated_note}")

    if imports:
        parts.append(format_import_summary(imports))
    if related_files:
        parts.append(f"Related files in project: {', '.join(related_files[:8])}")
    if session_context:
        parts.append(f"\nSession context:\n{session_context}")

    if mode == "review":
        parts.append(
            "\nStructure your review like this:\n"
            "### KEY FINDINGS\n"
            "- list concrete issues with line/file references\n"
            "### RISKS\n"
            "- security, correctness, performance concerns\n"
            "### POSITIVES\n"
            "- what the code does well\n"
            "### FILES INVOLVED\n"
            "- list files related to the findings"
        )
    elif mode == "explain":
        parts.append(
            "\nStructure your explanation like this:\n"
            "### PURPOSE\n"
            "- what this file does\n"
            "### KEY COMPONENTS\n"
            "- classes, functions, important variables with line refs\n"
            "### FLOW\n"
            "- how the logic works\n"
            "### DEPENDENCIES\n"
            "- imports and relationships"
        )
    elif mode == "summarize":
        parts.append(
            "\nStructure your summary like this:\n"
            "### PURPOSE\n"
            "- one-line description\n"
            "### KEY ELEMENTS\n"
            "- main exports/classes/functions\n"
            "### DEPENDENCIES\n"
            "- key imports"
        )

    parts.append(f"{task}\n")
    parts.append(f"```{language}\n{result.content}\n```")

    return "\n".join(parts)


def build_workspace_analysis_prompt(workspace_root: str,
                                     project_summary: str,
                                     dependency_context: str,
                                     session_context: str) -> str:
    return (
        "You are ask.ai, an offline AI developer workstation. "
        "Analyze the project at the workspace root provided below.\n\n"
        "CRITICAL RULES:\n"
        "- Only reference files and code elements visible in the provided context.\n"
        "- If you cannot see a specific file's content, say so.\n"
        "- Be concise and structured. Use headings and bullet points.\n"
        "- Format for terminal display.\n\n"
        "Analyze the project holistically.\n"
        "Cover:\n"
        "### PROJECT OVERVIEW\n"
        "- what this project does, its purpose\n"
        "### TECH STACK\n"
        "- languages, frameworks, key libraries\n"
        "### ARCHITECTURE\n"
        "- how the code is organized, key modules\n"
        "### ENTRY POINTS\n"
        "- where execution starts\n"
        "### KEY COMPONENTS\n"
        "- important files and what they do\n\n"
        f"Workspace: {workspace_root}\n\n"
        f"{project_summary}\n\n"
        f"{dependency_context}\n\n"
        f"{session_context}"
    )


def build_git_review_prompt(diff_text: str, changed_files: list[str],
                             dependency_context: str, session_context: str) -> str:
    return (
        "You are ask.ai, an offline AI developer workstation. "
        "Review the following git diff for risks, bugs, and architectural concerns.\n\n"
        "CRITICAL RULES:\n"
        "- Only comment on code visible in the diff.\n"
        "- Do not assume changes outside what is shown.\n"
        "- Be concise and technical.\n\n"
        "Structure your review like this:\n"
        "### CHANGES OVERVIEW\n"
        "- summarize what changed\n"
        "### RISKS & CONCERNS\n"
        "- security issues, deleted validations, duplicated logic\n"
        "### ARCHITECTURAL IMPACT\n"
        "- large structural changes, API breaks\n"
        "### SUGGESTIONS\n"
        "- concrete improvements if any\n\n"
        f"Files changed: {', '.join(changed_files[:10])}\n\n"
        f"{dependency_context}\n\n"
        f"{session_context}\n\n"
        f"```diff\n{diff_text}\n```"
    )


def build_patch_prompt(diff_context: str, user_request: str) -> str:
    return (
        "You are ask.ai, an offline AI developer workstation. "
        "Generate a unified diff (patch) for the requested change.\n\n"
        "CRITICAL RULES:\n"
        "- Only generate patches for code visible in the provided context.\n"
        "- Format as a valid unified diff (diff -u format).\n"
        "- Include file paths relative to project root.\n"
        "- Explain each hunk briefly.\n"
        "- Do NOT dump full files unless the change affects the entire file.\n\n"
        f"Request: {user_request}\n\n"
        f"Context:\n{diff_context}\n\n"
        "Output the patch in a code block with diff language tag."
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
