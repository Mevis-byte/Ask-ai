from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class GitError(Exception):
    """Raised when a git operation fails."""


def _find_repo(path: str | None = None) -> Path:
    start = Path(path or Path.cwd()).expanduser().resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=start,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise GitError(f"git not found or timeout: {exc}") from exc
    if result.returncode != 0:
        raise GitError("not a git repository")
    return Path(result.stdout.strip())


def _git_cmd(args: list[str], repo_path: Path, max_lines: int = 0) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=repo_path,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        raise GitError(str(exc)) from exc
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise GitError(stderr or f"git {' '.join(args)} failed")
    output = result.stdout
    if max_lines > 0:
        lines = output.splitlines()
        if len(lines) > max_lines:
            output = "\n".join(lines[:max_lines]) + f"\n... (truncated, {len(lines)} lines total)"
    return output


class GitPlugin:
    """Safe, read-only git operations."""

    def __init__(self, repo_path: str | None = None, max_diff_lines: int = 200) -> None:
        self._repo_path: Path | None = None
        self._max_diff_lines = max_diff_lines
        if repo_path:
            self.set_repo(repo_path)

    @property
    def is_available(self) -> bool:
        return shutil.which("git") is not None

    @property
    def repo_root(self) -> Path | None:
        return self._repo_path

    @property
    def current_branch(self) -> str | None:
        try:
            self._require_repo()
            result = _git_cmd(["rev-parse", "--abbrev-ref", "HEAD"], self._repo_path)
            return result.strip()
        except GitError:
            return None
        except subprocess.TimeoutExpired:
            return None

    def set_repo(self, path: str | None = None) -> str:
        self._repo_path = _find_repo(path)
        return str(self._repo_path)

    def status(self) -> str:
        self._require_repo()
        return _git_cmd(["status", "--short"], self._repo_path, max_lines=0)

    def diff(self, staged: bool = False, pathspec: str | None = None) -> str:
        self._require_repo()
        args = ["diff", "--no-color"]
        if staged:
            args.append("--cached")
        if pathspec:
            args.extend(["--", pathspec])
        return _git_cmd(args, self._repo_path, max_lines=self._max_diff_lines)

    def log(self, max_count: int = 10) -> str:
        self._require_repo()
        args = [
            "log",
            f"--max-count={max_count}",
            "--oneline",
            "--decorate=short",
        ]
        return _git_cmd(args, self._repo_path)

    def log_pretty(self, max_count: int = 5) -> str:
        self._require_repo()
        args = [
            "log",
            f"--max-count={max_count}",
            "--format=%h %s%n  Author: %an <%ae>%n  Date:   %ai%n",
        ]
        return _git_cmd(args, self._repo_path)

    def changed_files(self) -> list[str]:
        self._require_repo()
        raw = _git_cmd(["diff", "--name-only"], self._repo_path)
        return [f for f in raw.splitlines() if f.strip()]

    def diff_stat(self) -> str:
        self._require_repo()
        return _git_cmd(["diff", "--stat"], self._repo_path, max_lines=30)

    def staged_files(self) -> list[str]:
        self._require_repo()
        raw = _git_cmd(["diff", "--cached", "--name-only"], self._repo_path)
        return [f for f in raw.splitlines() if f.strip()]

    def full_diff(self) -> str:
        self._require_repo()
        staged = self.diff(staged=True)
        unstaged = self.diff(staged=False)
        parts: list[str] = []
        if staged:
            parts.append("STAGED CHANGES:\n" + staged)
        if unstaged:
            parts.append("UNSTAGED CHANGES:\n" + unstaged)
        return "\n\n".join(parts) if parts else ""

    def _require_repo(self) -> None:
        if self._repo_path is None:
            self.set_repo()
