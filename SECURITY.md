# Security Policy

## Local-First Design

ask.ai is built around a local-first architecture. No data leaves your machine unless you explicitly choose to share it.

- All LLM inference runs locally through Ollama.
- All conversation history is stored in a local SQLite database.
- All file analysis reads files directly from your filesystem.
- All vector embeddings are computed and stored locally.
- No cloud APIs, no telemetry, no external service calls.

## Offline Workflow

ask.ai is designed to function without any network connectivity. Once Ollama and the required models are installed, the application works entirely offline. There is no built-in mechanism to send data to external servers.

## Safe Filesystem Access

The `LocalFileContext` module implements several safety mechanisms:

### Project Boundary Enforcement

File operations are restricted to a project root directory. Any attempt to read files outside this boundary raises a `LocalFileAccessError`.

### Ignored Directories

The following directories are automatically skipped during recursive scans:

- `.git`, `.hg`, `.svn`
- `node_modules`, `venv`, `.venv`, `env`
- `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`
- `build`, `dist`, `site-packages`
- `.nox`, `.tox`

### Sensitive File Detection

Files matching known credential or key patterns are blocked:

- `.env`, `.env.local`, `.env.production`
- `.netrc`, `.npmrc`, `.pypirc`
- SSH keys: `id_rsa`, `id_dsa`, `id_ecdsa`, `id_ed25519`
- Certificate files: `*.crt`, `*.key`, `*.pem`, `*.pfx`, `*.p12`
- Database files: `*.db`, `*.sqlite`, `*.sqlite3`

### Binary File Detection

Files containing null bytes are treated as binary and rejected. This prevents the AI from processing non-text content.

### Read-Only Operations

File operations in the workspace context are read-only. The application does not write to any files in the project directory. The only files ask.ai writes are:
- Its own SQLite database (`~/.local/share/ask/chat.sqlite`)
- Its vector index (`~/.local/share/ask/rag_index/`)
- Files explicitly written via `/save-file <path>` (user-initiated)

## No Cloud Dependency

ask.ai does not require:

- API keys
- User accounts
- Cloud accounts
- Network connectivity (after initial model download)

If you choose to run Ollama on a remote host, the connection is configured via `ollama_host` and uses standard HTTP. This is optional and the default is `localhost`.

## Plugin Safety

The plugin system is an extension mechanism, not a code sandbox. Plugins run with the same permissions as the host process. Review any third-party plugin code before installing it.

The built-in Git plugin is read-only:
- It only executes `git status`, `git diff`, and `git log` commands.
- No destructive git operations (`push`, `reset`, `rebase`, etc.) are exposed.
- Subprocess calls include timeouts to prevent hanging.

## Current Security Limitations

- Plugins are not sandboxed. A malicious plugin could access any resource accessible to the user running ask.ai.
- File access restrictions rely on path resolution and can be bypassed by symlinks in certain configurations. Review workspaces before loading.
- The application does not encrypt its SQLite database or vector index at rest. If your threat model requires this, consider using filesystem-level encryption.
- Input from the AI model is rendered as Markdown. While Rich's Markdown parser is reasonably safe, treat model output as untrusted content.
- The application does not implement authentication or multi-user isolation. It is designed for single-user use on a trusted machine.

## Reporting Issues

If you discover a security issue, open an issue on GitHub rather than sending email. Security-related issues will be prioritized.
