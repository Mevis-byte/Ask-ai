# Changelog

## v0.5.0 (2026-05-16)

### Workspace Context System

- `/workspace <folder>` loads an entire project directory as read-only AI context
- Recursive file scanning with ignore rules for `.git`, `node_modules`, `venv`, `__pycache__`, `dist`, `build`
- Binary and sensitive file detection
- `/clear-context` to reset workspace state

### Local RAG / Semantic Search

- ChromaDB-backed vector retriever for local semantic file search
- sentence-transformers for offline embeddings (`all-MiniLM-L6-v2`)
- Persistent vector index in `~/.local/share/ask/rag_index/`
- Automatic file indexing when workspace is loaded and RAG is enabled
- `rag.enabled`, `rag.embedding_model`, `rag.chunk_size`, `rag.persist_directory` config options

### Git Integration

- `/git-status`, `/git-diff [file]`, `/git-log [n]` for read-only repository inspection
- `/explain-commit` sends staged/unstaged diff to the AI for explanation
- `/generate-commit` generates a conventional commit message from the current diff
- All git operations are read-only with timeout and error handling
- `git.enabled` and `git.max_diff_lines` config options

### Model Router

- Automatic model selection based on detected task type (coding, summary, chat, analysis)
- Regex-based task detection from user messages
- Configurable per-task model mapping
- `router.enabled`, `router.*_model` config options

### Export & Copy

- `/save-file <path>` writes the last AI response to disk
- `/export` saves the full session transcript as Markdown
- `/copy` and `/print` commands for clipboard and terminal scrollback access
- `Ctrl+Y` keybinding for clipboard copy in the Textual workstation

### Config & Dependencies

- Expanded `Settings` dataclass with router, git, RAG embedding fields
- Environment variable overrides for all new settings (`ASK_ROUTER_*`, `ASK_GIT_*`, `ASK_RAG_*`)
- Optional `ask[rag]` extras for ChromaDB and sentence-transformers
- Updated `config.example.json` with all new sections

### Other

- Improved help text with categorized command listing
- Settings pane now shows router and git status
- Status bar shows git availability indicator
- `ask chat` now uses the plain-terminal REPL instead of Textual (selectable output)
- `stream_markdown_live()` outputs plain text via `sys.stdout` (no Rich Live redraws)
- Removed duplicate Rich Panel rendering after streaming

## v0.1.0 (2026-04-20)

### Initial Release

- Ollama-backed CLI chat application
- Real-time token streaming with Rich Live rendering
- Multi-model support via `/model` and `/models` commands
- Textual workstation UI with three-pane layout (sessions, chat, settings)
- SQLite-based chat memory with FTS5 full-text search
- Session management (create, list, switch, save)
- File analysis commands: `/read`, `/explain`, `/summarize`, `/review`
- `/find` for text search within project context
- LocalFileContext for safe, project-bounded file access
- Rich-based console UI with cyberpunk theme
- Animated startup sequence
- Plugin base class and registry
- RAG protocol with NoOpRetriever (pluggable architecture)
- Layered configuration: defaults → config.json → environment variables
- `ask ai`, `ask chat`, and `ask analyze <file>` CLI commands
- Requirements: Python 3.11+, Ollama, llama3/DeepSeek/Mistral models
