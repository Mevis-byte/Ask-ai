# Architecture

## High-Level Overview

ask.ai is a local-first AI workstation for the terminal. It connects a user-facing frontend (TTY or Textual TUI) to a configurable pipeline of local LLM inference, memory, and tool execution.

```
User Input
    │
    ▼
┌──────────────┐
│  Frontend     │  Textual TUI or plain-terminal REPL
│  (ask/*.py)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Commands     │  Parser → Router (optional) → Dispatcher
│  (ask/*.py)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Chat Engine  │  Prompt building, streaming, memory attachment
│  (ask/*.py)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  LLM Layer    │  Ollama client (local inference)
│  (ask/*.py)   │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│  Memory/State │  SQLite (history), ChromaDB (RAG index)
│  (ask/*.py)   │
└──────────────┘
```

## Current Package Structure

```
ask/
├── main.py                  # Typer CLI: ask ai, ask chat, ask analyze
├── app/
│   ├── bootstrap.py         # Plain chat app assembly
│   ├── chat.py              # Plain-terminal REPL
│   ├── session_manager.py   # Session creation/list/switch/title APIs
│   └── workstation.py       # Textual workstation assembly
├── ui/
│   ├── workstation.py       # Main Textual app, layout, input, slash routing
│   ├── home_screen.py       # Startup home screen
│   ├── ask_command_palette.py # Ctrl+P fuzzy command palette
│   ├── pickers.py           # Session/model/workspace pickers
│   ├── fuzzy.py             # RapidFuzz helpers
│   └── command_catalog.py   # Shared command metadata
├── memory/
│   ├── sqlite_memory.py     # SQLite history, metadata, FTS5 context search
│   └── in_memory.py         # RAM fallback
├── files/local_context.py   # Read-only workspace context and file search
├── tools/
│   ├── files.py             # File analysis prompts and render panels
│   └── scanner.py           # Project scan and dependency graph
├── rag/                     # ChromaDB retriever and prompt injection helpers
├── models/                  # Ollama backend and model router
├── plugins/git/plugin.py    # Read-only git integration
├── security/                # Validation, prompt-injection checks, output filtering
└── config/                  # Defaults, JSON config, env overrides, save support
```

## Workstation Runtime

The Textual workstation preserves a three-pane layout:

- Left: sessions and current trace.
- Center: chat transcript and empty-state actions.
- Right: settings, local model state, workspace, git, and file context.
- Bottom: persistent status bar and command/message input.

Startup pushes a home screen overlay before the active session is entered. The home screen reads session/model/workspace state from the already-mounted workstation and dismisses into the same app instance.

`Ctrl+P` opens the command palette. The palette uses the shared command catalog plus dynamic sessions, installed models, and workspace files. Complete commands execute through the existing `_handle_command` dispatcher; commands needing arguments are inserted into the input.

Session titles are stored in the existing SQLite `conversations.title` column. Older databases are migrated by `sqlite_memory.py`; generated-id sessions are displayed as `New Session` until an AI-generated or manual title is available.

## Key Design Decisions

### 1. Protocol-Based Abstractions
Retrievers, plugins, and memory backends are defined as `typing.Protocol` classes. This allows swapping implementations without changing consumers.

### 2. Config Layering
Settings flow: defaults → config.json → environment variables → in-app changes. The `Settings` dataclass in `config.py` holds all configuration in one place with env-var overrides for every field.

### 3. Optional Dependencies
Heavy dependencies (ChromaDB, sentence-transformers) are gated behind extras (`ask[rag]`). The application degrades gracefully when they are not installed.

### 4. Read-Only Tooling
All built-in tool operations (file reading, git inspection, workspace scanning) are read-only by default. The only write operations are user-initiated (`/save-file`, `/export`) or internal to ask.ai's own state (SQLite, vector index).

## Data Flow for a Typical Request

1. User enters text in the TUI or REPL.
2. If it starts with `/`, the command parser intercepts it and dispatches to the appropriate handler.
3. If it's a plain message:
   a. The model router (if enabled) classifies the task and selects a model.
   b. If a workspace is loaded, its files are included as read-only context.
   c. If RAG is enabled and the workspace has been indexed, relevant chunks are retrieved.
   d. Recent conversation history from SQLite is attached.
   e. The prompt is sent to the selected Ollama model.
   f. Response tokens are streamed back to the frontend.
   g. The final response is appended to the SQLite history.

The design prioritizes locality, modularity, and developer workflow over cloud features and scale.
