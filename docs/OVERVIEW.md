# Overview

ask.ai is a local-first AI workstation for the terminal. Everything runs on your machine with no cloud dependency.

## What It Does

ask.ai connects local LLMs (via Ollama) to your development environment. You can:

- **Chat** with an AI assistant that has access to your project files.
- **Analyze code** with commands like `/explain`, `/review`, and `/summarize`.
- **Search your codebase** using full-text search (`/find`) or semantic vector search (RAG with ChromaDB).
- **Inspect git state** with read-only git commands (`/git-status`, `/git-diff`, `/git-log`).
- **Generate commit messages** from your working diff (`/generate-commit`).
- **Load entire workspaces** as AI context (`/workspace <folder>`).
- **Switch models** on the fly (`/model <name>`) or let the router auto-select the best model for each task.

## Frontends

| Entry Point | Description |
|-------------|-------------|
| `ask ai` | Textual-based TUI with three-pane layout (sessions, chat, settings) |
| `ask chat` | Plain-terminal REPL (no TUI dependencies) |
| `ask analyze <file>` | One-shot file analysis, prints result and exits |

## Quick Start

```bash
# Install
pip install -r requirements.txt

# Run TUI
python -m ask.main ai

# Or plain terminal
python -m ask.main chat
```

## Design Principles

- **Local-first.** Everything runs on your machine. No telemetry, no accounts, no cloud APIs.
- **Offline.** Works without internet after model download.
- **Developer-focused.** Designed for terminal workflows.
- **Modular.** Components (retrievers, plugins, memory backends) are swappable via protocols.
- **Safe.** All built-in tool operations are read-only. File access is bounded to project directories.

See also: [Architecture](ARCHITECTURE.md), [Commands](COMMANDS.md), [Configuration](CONFIGURATION.md)
