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

## Package Structure

```
ask/
├── __init__.py          # package marker
├── __main__.py          # CLI entry: ask ai, ask chat, ask analyze
├── chat.py              # plain-terminal chat REPL loop
├── config.py            # Settings dataclass, layered config loader
├── engine.py            # stream_ollama(), prompt building
├── exporter.py          # /save-file, /export session transcripts
├── git_plugin.py        # read-only git commands (status, diff, log)
├── llm.py               # HTTP client to Ollama API
├── main.py              # Textual TUI app definition
├── memory.py            # SQLite-backed MessageStore with FTS5 search
├── model_router.py      # task-aware model selection
├── rag.py               # ChromaDB-based vector retriever (optional)
├── retriever.py         # Retriever protocol + NoOpRetriever
├── settings.py          # Textual settings pane
├── sessions.py          # Textual session list pane
├── tools.py             # File operations (read, find, workspace)
└── utils.py             # formatting helpers, markdown rendering
```

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
