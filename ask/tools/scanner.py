from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Counter


_LANGUAGE_BY_SUFFIX = {
    ".py": "Python",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".jsx": "JSX",
    ".tsx": "TSX",
    ".rs": "Rust",
    ".go": "Go",
    ".java": "Java",
    ".rb": "Ruby",
    ".php": "PHP",
    ".c": "C",
    ".h": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".hpp": "C++",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".zig": "Zig",
    ".lua": "Lua",
    ".r": "R",
    ".sh": "Shell",
    ".bash": "Shell",
    ".zsh": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
    ".less": "Less",
    ".vue": "Vue",
    ".svelte": "Svelte",
    ".pyx": "Cython",
    ".pxd": "Cython",
    ".cuh": "CUDA",
    ".cu": "CUDA",
    ".toml": "TOML",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".json": "JSON",
    ".xml": "XML",
    ".md": "Markdown",
    ".rst": "reStructuredText",
    ".dockerfile": "Dockerfile",
    ".cmake": "CMake",
    ".mk": "Makefile",
    ".proto": "Protobuf",
}

_FRAMEWORK_SIGNATURES: list[tuple[str, set[str], list[str]]] = [
    ("Django", {"django"}, {"settings.py", "wsgi.py", "asgi.py", "urls.py", "manage.py"}),
    ("Flask", {"flask"}, {"app.py", "application.py"}),
    ("FastAPI", {"fastapi"}, {"main.py"}),
    ("React", {"react", "react-dom"}, {"jsconfig.json", "tsconfig.json"}),
    ("Vue", {"vue"}, {"nuxt.config.js", "nuxt.config.ts"}),
    ("Svelte", {"svelte"}, {"svelte.config.js"}),
    ("Next.js", {"next"}, {"next.config.js", "next.config.mjs"}),
    ("Express", {"express"}, {}),
    ("Spring Boot", {"spring-boot-starter"}, {"pom.xml", "build.gradle"}),
    ("PyTorch", {"torch"}, {}),
    ("TensorFlow", {"tensorflow"}, {}),
    ("Rails", {"rails"}, {"Gemfile", "config/routes.rb"}),
    ("Django REST", {"rest_framework"}, {}),
    ("SQLAlchemy", {"sqlalchemy"}, {}),
    ("pytest", {"pytest"}, {}),
]

_PYTHON_IMPORT_RE = re.compile(
    r'(?:from\s+([.\w]+)\s+import|\bimport\s+([.\w]+))'
)

_JS_IMPORT_RE = re.compile(
    r"(?:import\s+(?:\{[^}]*\}|[^;{]+)\s+from\s+['\"]([^'\"]+)['\"]|require\s*\(\s*['\"]([^'\"]+)['\"]\s*\))"
)

_IGNORED_SCAN_DIRS = frozenset({
    ".git", ".hg", ".svn", "__pycache__", "node_modules",
    "venv", ".venv", "env", "build", "dist", ".mypy_cache",
    ".pytest_cache", ".ruff_cache", ".nox", ".tox",
    "site-packages", ".eggs", "eggs", ".cache",
})


def _is_text_file(path: Path) -> bool:
    try:
        if path.stat().st_size > 262144:
            return False
        data = path.read_bytes()[:8192]
        return b"\x00" not in data
    except OSError:
        return False


def _walk_project(root: Path):
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
            name_lower = entry.name.lower()
            if entry.is_dir():
                if name_lower not in _IGNORED_SCAN_DIRS:
                    dirs.append(entry.name)
            elif entry.is_file():
                files.append(entry.name)
        yield current, dirs, files
        for name in reversed(dirs):
            stack.append(current / name)


@dataclass
class ProjectSummary:
    root: str
    total_files: int
    languages: dict[str, int]
    frameworks: list[str]
    has_tests: bool
    has_docs: bool
    has_docker: bool
    has_ci: bool
    entry_points: list[str]
    sample_structure: list[str]


@dataclass
class DependencyGraph:
    _imports: dict[str, list[str]] = field(default_factory=dict)
    _dependents: dict[str, list[str]] = field(default_factory=dict)

    def add_file(self, file_path: str, imports: list[str]) -> None:
        self._imports[file_path] = imports
        for imp in imports:
            if imp not in self._dependents:
                self._dependents[imp] = []
            self._dependents[imp].append(file_path)

    def imports_for(self, file_path: str) -> list[str]:
        return self._imports.get(file_path, [])

    def dependents_of(self, module: str) -> list[str]:
        return self._dependents.get(module, [])

    def related_files(self, file_path: str, depth: int = 1) -> list[str]:
        related: set[str] = set()
        seen: set[str] = set()
        queue: list[tuple[str, int]] = [(file_path, 0)]
        while queue:
            current, d = queue.pop(0)
            if current in seen:
                continue
            seen.add(current)
            if d > 0 and current != file_path:
                related.add(current)
            if d >= depth:
                continue
            for imp in self._imports.get(current, []):
                for dep_file, dep_imports in self._imports.items():
                    if dep_file not in seen and any(imp in i for i in dep_imports):
                        queue.append((dep_file, d + 1))
                for dep in self._dependents.get(imp, []):
                    if dep not in seen:
                        queue.append((dep, d + 1))
        return sorted(related)

    def all_files(self) -> list[str]:
        return sorted(self._imports.keys())

    def count(self) -> int:
        return len(self._imports)


_PROJECT_ROOT_KEY_FILES = frozenset({
    "manage.py", "setup.py", "setup.cfg", "pyproject.toml",
    "package.json", "go.mod", "Cargo.toml", "Gemfile",
    "build.gradle", "pom.xml", "CMakeLists.txt",
    "Makefile", "Rakefile", "Dockerfile",
    "docker-compose.yml", "docker-compose.yaml",
    ".github/workflows", ".gitlab-ci.yml", "Jenkinsfile",
    "README.md", "CONTRIBUTING.md",
})


def scan_project(root: Path) -> ProjectSummary:
    root = root.expanduser().resolve()
    languages: Counter[str] = Counter()
    frameworks: set[str] = set()
    all_imports: list[str] = []
    has_tests = False
    has_docs = False
    has_docker = False
    has_ci = False
    entry_points: list[str] = []
    sample_structure: list[str] = []
    total_files = 0

    for level in range(3):
        sample_structure.clear()

    dir_count = 0
    for current, dirs, files in _walk_project(root):
        rel = _safe_rel_path(current, root)
        parts = rel.parts if rel != Path(".") else ()

        if len(parts) <= 2:
            dir_count += 1
            indent = "  " * len(parts)
            sample_structure.append(f"{indent}{current.name}/")

        for name in files:
            path = current / name
            if not _is_text_file(path):
                continue
            total_files += 1
            suffix = path.suffix.lower()
            lang = _LANGUAGE_BY_SUFFIX.get(suffix) or _LANGUAGE_BY_SUFFIX.get(f".{name.split('.')[-1].lower()}")
            if lang:
                languages[lang] += 1

            name_lower = name.lower()
            if name_lower in {"setup.py", "pyproject.toml", "main.py", "app.py",
                              "cli.py", "index.js", "index.ts", "server.js",
                              "server.ts", "main.rs", "main.go"}:
                entry_points.append(str(path.relative_to(root)))

            if "test" in name_lower or name_lower.startswith("test_"):
                has_tests = True

            if suffix in {".md", ".rst", ".txt"} and name_lower in {"readme.md",
                    "readme.rst", "contributing.md", "changelog.md"}:
                has_docs = True

            if len(parts) == 1 and parts[0] in {"docs", "documentation"}:
                has_docs = True

            if suffix == ".dockerfile" or name_lower == "dockerfile":
                has_docker = True
            if name_lower in {"docker-compose.yml", "docker-compose.yaml"}:
                has_docker = True

            if name_lower in {".github/workflows", ".gitlab-ci.yml", "Jenkinsfile"}:
                has_ci = True

            if suffix in _LANGUAGE_BY_SUFFIX and len(sample_structure) < 60 and len(parts) <= 2:
                indent = "  " * len(parts)
                sample_structure.append(f"{indent}  {name}")

        for d in dirs:
            if d == "tests" or d.startswith("test"):
                has_tests = True
            if d == "docs":
                has_docs = True

    known_frameworks = detect_frameworks_from_structure(languages, sample_structure, root)
    frameworks.update(known_frameworks)

    if not languages:
        languages["Unknown"] = total_files

    return ProjectSummary(
        root=str(root),
        total_files=total_files,
        languages=dict(languages.most_common()),
        frameworks=sorted(frameworks),
        has_tests=has_tests,
        has_docs=has_docs,
        has_docker=has_docker,
        has_ci=has_ci,
        entry_points=entry_points[:8],
        sample_structure=sample_structure[:60],
    )


def detect_frameworks_from_structure(
    languages: Counter[str],
    sample_structure: list[str],
    root: Path,
) -> set[str]:
    frameworks: set[str] = set()
    all_text = " ".join(sample_structure).lower()
    for framework, imports_needed, key_files in _FRAMEWORK_SIGNATURES:
        fw_lower = framework.lower()
        for kf in key_files:
            if kf.lower() in all_text:
                frameworks.add(framework)
                break
        else:
            continue
        break

    if "Python" in languages:
        req_file = root / "requirements.txt"
        if req_file.is_file():
            try:
                req_text = req_file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                req_text = ""
            for framework, imports_needed, _ in _FRAMEWORK_SIGNATURES:
                for imp in imports_needed:
                    if imp.lower() in req_text.lower():
                        frameworks.add(framework)
                        break
        pyproj = root / "pyproject.toml"
        if pyproj.is_file():
            try:
                pyproj_text = pyproj.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pyproj_text = ""
            for framework, imports_needed, _ in _FRAMEWORK_SIGNATURES:
                for imp in imports_needed:
                    if imp.lower() in pyproj_text.lower():
                        frameworks.add(framework)
                        break

    if "JavaScript" in languages or "TypeScript" in languages:
        pkg = root / "package.json"
        if pkg.is_file():
            try:
                pkg_text = pkg.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pkg_text = ""
            for framework, imports_needed, _ in _FRAMEWORK_SIGNATURES:
                for imp in imports_needed:
                    if imp.lower() in pkg_text.lower():
                        frameworks.add(framework)
                        break

    return frameworks


def build_dependency_graph(root: Path) -> DependencyGraph:
    graph = DependencyGraph()
    for current, _, files in _walk_project(root):
        for name in files:
            path = current / name
            if not _is_text_file(path):
                continue
            suffix = path.suffix.lower()
            try:
                text = path.read_text(encoding="utf-8", errors="replace")[:65536]
            except OSError:
                continue
            rel = _safe_rel_path(current, root)
            file_key = str(rel / name) if rel != Path(".") else name
            imports: list[str] = []
            if suffix == ".py":
                for m in _PYTHON_IMPORT_RE.finditer(text):
                    imp = (m.group(1) or m.group(2)).split(".")[0]
                    if imp and imp not in imports:
                        imports.append(imp)
            elif suffix in {".js", ".ts", ".jsx", ".tsx"}:
                for m in _JS_IMPORT_RE.finditer(text):
                    imp = (m.group(1) or m.group(2))
                    if imp and not imp.startswith(".") and imp not in imports:
                        parts = imp.split("/")
                        imports.append(parts[0] if imp.startswith("@") else parts[0])
            if imports:
                graph.add_file(file_key, imports)
    return graph


def _safe_rel_path(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(root)
    except ValueError:
        return Path(".")


def format_project_summary(summary: ProjectSummary) -> str:
    lines: list[str] = []
    lines.append(f"Project root: {summary.root}")
    lines.append(f"Total files: {summary.total_files}")
    if summary.languages:
        lang_parts = [f"{lang}: {count}" for lang, count in sorted(summary.languages.items(), key=lambda x: -x[1])]
        lines.append(f"Languages: {', '.join(lang_parts)}")
    if summary.frameworks:
        lines.append(f"Frameworks: {', '.join(summary.frameworks)}")
    flags: list[str] = []
    if summary.has_tests:
        flags.append("tests")
    if summary.has_docs:
        flags.append("docs")
    if summary.has_docker:
        flags.append("docker")
    if summary.has_ci:
        flags.append("CI")
    if flags:
        lines.append(f"Detected: {', '.join(flags)}")
    if summary.entry_points:
        lines.append("Entry points:")
        for ep in summary.entry_points[:4]:
            lines.append(f"  - {ep}")
    if summary.sample_structure:
        lines.append("Structure:")
        lines.extend("  " + s for s in summary.sample_structure[:20])
    return "\n".join(lines)


def format_dependency_context(graph: DependencyGraph, target_file: str) -> str:
    imports = graph.imports_for(target_file)
    if not imports:
        return ""
    lines: list[str] = []
    lines.append(f"File dependencies for {target_file}:")
    for imp in imports:
        dependents = graph.dependents_of(imp)
        if dependents:
            lines.append(f"  imports from {imp} → affects: {', '.join(dependents[:5])}")
        else:
            lines.append(f"  imports {imp}")
    related = graph.related_files(target_file, depth=1)
    if related:
        lines.append(f"Related files: {', '.join(related[:8])}")
    return "\n".join(lines)
