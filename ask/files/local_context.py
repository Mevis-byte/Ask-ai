from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ask.rag import Document

IGNORED_DIR_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".nox",
    ".pytest_cache",
    ".ruff_cache",
    ".svn",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "dist",
    "env",
    "node_modules",
    "site-packages",
    "venv",
}

SENSITIVE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".netrc",
    ".npmrc",
    ".pypirc",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa",
    "known_hosts",
}

SENSITIVE_SUFFIXES = {
    ".crt",
    ".db",
    ".key",
    ".pem",
    ".pfx",
    ".p12",
    ".sqlite",
    ".sqlite3",
}

DEFAULT_MAX_FILE_BYTES = 256 * 1024
DEFAULT_MAX_FIND_FILE_BYTES = 512 * 1024
DEFAULT_MAX_PROMPT_CHARS = 36_000
DEFAULT_MAX_ATTACHMENTS = 8
DEFAULT_MAX_FIND_RESULTS = 60


class LocalFileAccessError(Exception):
    """Raised when a requested local file operation is outside the safe boundary."""


@dataclass(frozen=True)
class ContextSummary:
    root: Path
    root_label: str
    file_count: int
    ignored_dir_count: int
    sample_paths: list[str]


@dataclass(frozen=True)
class FileReadResult:
    path: Path
    display_path: str
    content: str
    bytes_read: int
    truncated: bool


@dataclass(frozen=True)
class FileFindMatch:
    path: str
    line_number: int
    line: str


@dataclass(frozen=True)
class FileFindResult:
    pattern: str
    root_label: str
    scanned_files: int
    skipped_files: int
    truncated: bool
    matches: list[FileFindMatch]


@dataclass(frozen=True)
class _ContextAttachment:
    source: str
    text: str


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _is_ignored_dir_name(name: str) -> bool:
    lowered = name.lower()
    return lowered in IGNORED_DIR_NAMES or "cache" in lowered


def _is_sensitive_file(path: Path) -> bool:
    return path.name.lower() in SENSITIVE_FILE_NAMES or path.suffix.lower() in SENSITIVE_SUFFIXES


def _one_line(text: str, *, limit: int = 120) -> str:
    clean = " ".join(text.split())
    if len(clean) <= limit:
        return clean
    return clean[: max(0, limit - 3)] + "..."


class LocalFileContext:
    """Read-only, project-bounded file context for chat and future retrieval."""

    def __init__(
        self,
        *,
        project_root: Path | None = None,
        max_file_bytes: int = DEFAULT_MAX_FILE_BYTES,
        max_find_file_bytes: int = DEFAULT_MAX_FIND_FILE_BYTES,
        max_prompt_chars: int = DEFAULT_MAX_PROMPT_CHARS,
        max_attachments: int = DEFAULT_MAX_ATTACHMENTS,
        max_find_results: int = DEFAULT_MAX_FIND_RESULTS,
    ) -> None:
        self._project_root = (project_root or Path.cwd()).expanduser().resolve()
        if not self._project_root.is_dir():
            raise LocalFileAccessError(f"project root is not a directory: {self._project_root}")
        self._active_root = self._project_root
        self._max_file_bytes = max_file_bytes
        self._max_find_file_bytes = max_find_file_bytes
        self._max_prompt_chars = max_prompt_chars
        self._max_attachments = max_attachments
        self._max_find_results = max_find_results
        self._attachments: list[_ContextAttachment] = []

    @property
    def project_root(self) -> Path:
        return self._project_root

    @property
    def active_root(self) -> Path:
        return self._active_root

    @property
    def active_root_label(self) -> str:
        return self._display_path(self._active_root)

    @property
    def attachment_count(self) -> int:
        return len(self._attachments)

    def status_label(self) -> str:
        label = self.active_root_label
        suffix = f"{len(self._attachments)} ctx" if self._attachments else "no ctx"
        return f"{label} ({suffix})"

    def set_context(self, folder: str) -> ContextSummary:
        root = self._resolve_context_folder(folder)
        self._active_root = root
        self._attachments.clear()
        summary = self.summarize()
        self._add_attachment(
            source=f"context:{summary.root_label}",
            text=self._context_summary_text(summary),
        )
        return summary

    def summarize(self) -> ContextSummary:
        file_count = 0
        ignored_dir_count = 0
        samples: list[str] = []
        for current, dirs, files in self._walk(self._active_root):
            ignored_dir_count += self._filter_dirs(current, dirs)
            for name in sorted(files):
                path = current / name
                if self._should_skip_file(path):
                    continue
                file_count += 1
                if len(samples) < 14:
                    samples.append(self._display_path(path))
        return ContextSummary(
            root=self._active_root,
            root_label=self.active_root_label,
            file_count=file_count,
            ignored_dir_count=ignored_dir_count,
            sample_paths=samples,
        )

    def read_file(self, file_name: str) -> FileReadResult:
        path = self._resolve_file(file_name)
        if self._should_skip_file(path):
            raise LocalFileAccessError(f"file is blocked or ignored: {self._display_path(path)}")
        result = self._read_text_file(path, max_bytes=self._max_file_bytes)
        self._add_attachment(
            source=f"file:{result.display_path}",
            text=self._file_attachment_text(result),
        )
        return result

    def find(self, pattern: str) -> FileFindResult:
        query = pattern.strip()
        if len(query) < 2:
            raise LocalFileAccessError("find pattern must be at least 2 characters")

        needle = query.lower()
        matches: list[FileFindMatch] = []
        scanned = 0
        skipped = 0
        truncated = False

        for current, dirs, files in self._walk(self._active_root):
            self._filter_dirs(current, dirs)
            for name in sorted(files):
                path = current / name
                if self._should_skip_file(path):
                    skipped += 1
                    continue
                try:
                    result = self._read_text_file(path, max_bytes=self._max_find_file_bytes)
                except LocalFileAccessError:
                    skipped += 1
                    continue
                scanned += 1
                per_file = 0
                for number, line in enumerate(result.content.splitlines(), start=1):
                    if needle not in line.lower():
                        continue
                    matches.append(
                        FileFindMatch(
                            path=result.display_path,
                            line_number=number,
                            line=_one_line(line, limit=160),
                        )
                    )
                    per_file += 1
                    if len(matches) >= self._max_find_results:
                        truncated = True
                        break
                    if per_file >= 5:
                        break
                if truncated:
                    break
            if truncated:
                break

        result = FileFindResult(
            pattern=query,
            root_label=self.active_root_label,
            scanned_files=scanned,
            skipped_files=skipped,
            truncated=truncated,
            matches=matches,
        )
        self._add_attachment(
            source=f"search:{query}",
            text=self._find_attachment_text(result),
        )
        return result

    def prompt_context(self) -> str | None:
        if not self._attachments:
            return None
        parts = [
            "Local project context (read-only).",
            "Use this context for analysis. Do not claim to modify files.",
            f"Project root: {self._display_path(self._project_root)}",
            f"Active context: {self.active_root_label}",
            "",
        ]
        used = 0
        for item in self._attachments:
            remaining = self._max_prompt_chars - used
            if remaining <= 0:
                parts.append("[local context truncated]")
                break
            text = item.text
            if len(text) > remaining:
                text = text[:remaining] + "\n[attachment truncated]"
            parts.append(f"--- {item.source} ---\n{text}")
            used += len(text)
        return "\n".join(parts)

    def to_documents(self) -> list[Document]:
        """Expose selected local context in the same shape expected by RAG retrievers."""
        return [Document(text=item.text, source=item.source) for item in self._attachments]

    def clear(self) -> None:
        self._attachments.clear()

    def _resolve_context_folder(self, folder: str) -> Path:
        if not folder.strip():
            raise LocalFileAccessError("usage: /context <folder>")
        raw = Path(folder).expanduser()
        candidate = raw if raw.is_absolute() else self._project_root / raw
        path = candidate.resolve()
        self._ensure_inside_project(path)
        if not path.is_dir():
            raise LocalFileAccessError(f"context is not a folder: {folder}")
        if self._has_ignored_part(path):
            raise LocalFileAccessError(f"context folder is ignored: {self._display_path(path)}")
        return path

    def _resolve_file(self, file_name: str) -> Path:
        if not file_name.strip():
            raise LocalFileAccessError("file path required")
        raw = Path(file_name).expanduser()
        candidate = raw if raw.is_absolute() else self._active_root / raw
        path = candidate.resolve()
        self._ensure_inside_active_root(path)
        if not path.is_file():
            raise LocalFileAccessError(f"not a readable file: {file_name}")
        return path

    def _ensure_inside_project(self, path: Path) -> None:
        if not _is_relative_to(path, self._project_root):
            raise LocalFileAccessError(
                f"outside project boundary: {path}. Launch ask from that project to access it."
            )

    def _ensure_inside_active_root(self, path: Path) -> None:
        self._ensure_inside_project(path)
        if not _is_relative_to(path, self._active_root):
            raise LocalFileAccessError(f"outside active context: {path}")

    def _display_path(self, path: Path) -> str:
        try:
            rel = path.resolve().relative_to(self._project_root)
        except ValueError:
            return str(path)
        return "." if str(rel) == "." else rel.as_posix()

    def _walk(self, root: Path):
        stack = [root]
        while stack:
            current = stack.pop()
            try:
                entries = sorted(current.iterdir(), key=lambda p: p.name.lower())
            except OSError:
                continue
            dirs: list[str] = []
            files: list[str] = []
            for entry in entries:
                if entry.is_symlink():
                    continue
                if entry.is_dir():
                    dirs.append(entry.name)
                elif entry.is_file():
                    files.append(entry.name)
            yield current, dirs, files
            for name in reversed(dirs):
                path = current / name
                if not _is_ignored_dir_name(name):
                    stack.append(path)

    def _filter_dirs(self, current: Path, dirs: list[str]) -> int:
        kept: list[str] = []
        ignored = 0
        for name in dirs:
            if _is_ignored_dir_name(name) or self._has_ignored_part(current / name):
                ignored += 1
            else:
                kept.append(name)
        dirs[:] = kept
        return ignored

    def _has_ignored_part(self, path: Path) -> bool:
        try:
            rel = path.resolve().relative_to(self._project_root)
        except ValueError:
            return True
        return any(_is_ignored_dir_name(part) for part in rel.parts)

    def _should_skip_file(self, path: Path) -> bool:
        return self._has_ignored_part(path.parent) or _is_sensitive_file(path)

    def _read_text_file(self, path: Path, *, max_bytes: int) -> FileReadResult:
        try:
            size = path.stat().st_size
        except OSError as exc:
            raise LocalFileAccessError(f"cannot stat file: {self._display_path(path)}") from exc
        if size <= 0:
            return FileReadResult(path, self._display_path(path), "", 0, False)
        read_limit = min(size, max_bytes)
        try:
            with path.open("rb") as handle:
                data = handle.read(read_limit)
        except OSError as exc:
            raise LocalFileAccessError(f"cannot read file: {self._display_path(path)}") from exc
        if b"\x00" in data:
            raise LocalFileAccessError(f"binary file blocked: {self._display_path(path)}")
        text = data.decode("utf-8", errors="replace")
        return FileReadResult(
            path=path,
            display_path=self._display_path(path),
            content=text,
            bytes_read=len(data),
            truncated=size > max_bytes,
        )

    def _add_attachment(self, *, source: str, text: str) -> None:
        self._attachments.append(_ContextAttachment(source=source, text=text))
        if len(self._attachments) > self._max_attachments:
            self._attachments = self._attachments[-self._max_attachments :]

    @staticmethod
    def _context_summary_text(summary: ContextSummary) -> str:
        lines = [
            f"Active folder: {summary.root_label}",
            f"Readable files: {summary.file_count}",
            f"Ignored directories: {summary.ignored_dir_count}",
        ]
        if summary.sample_paths:
            lines.append("Sample files:")
            lines.extend(f"- {path}" for path in summary.sample_paths)
        return "\n".join(lines)

    @staticmethod
    def _file_attachment_text(result: FileReadResult) -> str:
        suffix = " (truncated)" if result.truncated else ""
        return f"File: {result.display_path}{suffix}\n\n```\n{result.content}\n```"

    @staticmethod
    def _find_attachment_text(result: FileFindResult) -> str:
        lines = [
            f"Search pattern: {result.pattern}",
            f"Active folder: {result.root_label}",
            f"Matches: {len(result.matches)}",
        ]
        for match in result.matches:
            lines.append(f"{match.path}:{match.line_number}: {match.line}")
        if result.truncated:
            lines.append("[search results truncated]")
        return "\n".join(lines)
