# Configuration

## Configuration File

The default config file is `~/.config/ask/config.json`. A template is provided as `config.example.json` in the repository root.

All settings can also be overridden via environment variables with the prefix `ASK_`.

## Option Reference

### General

| Option | Env Variable | Default | Description |
|--------|-------------|---------|-------------|
| `default_model` | `ASK_DEFAULT_MODEL` | `llama3.2:3b` | Default Ollama model |
| `ollama_host` | `ASK_OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `system_prompt` | `ASK_SYSTEM_PROMPT` | _(see config.example.json)_ | Base system prompt |
| `memory_limit` | `ASK_MEMORY_LIMIT` | `100` | Recent messages sent as context |

### Workspace

| Option | Env Variable | Default | Description |
|--------|-------------|---------|-------------|
| `workspace.ignore_dirs` | `ASK_WORKSPACE_IGNORE_DIRS` | `[".git", "node_modules", "venv", "__pycache__", "build", "dist"]` | Directories ignored during workspace scan |
| `workspace.max_file_size` | `ASK_WORKSPACE_MAX_FILE_SIZE` | `1048576` | Maximum file size in bytes (1 MB) |
| `workspace.max_files` | `ASK_WORKSPACE_MAX_FILES` | `500` | Maximum number of files to load |

### RAG (Vector Search)

| Option | Env Variable | Default | Description |
|--------|-------------|---------|-------------|
| `rag.enabled` | `ASK_RAG_ENABLED` | `false` | Enable semantic file search |
| `rag.embedding_model` | `ASK_RAG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | sentence-transformers model |
| `rag.chunk_size` | `ASK_RAG_CHUNK_SIZE` | `512` | Chunk size for document splitting |
| `rag.top_k` | `ASK_RAG_TOP_K` | `5` | Number of chunks to retrieve |
| `rag.persist_directory` | `ASK_RAG_PERSIST_DIR` | `~/.local/share/ask/rag_index/` | Vector index storage path |

### Git

| Option | Env Variable | Default | Description |
|--------|-------------|---------|-------------|
| `git.enabled` | `ASK_GIT_ENABLED` | `true` | Enable git commands |
| `git.max_diff_lines` | `ASK_GIT_MAX_DIFF_LINES` | `500` | Max lines for diff in context |

### Model Router

| Option | Env Variable | Default | Description |
|--------|-------------|---------|-------------|
| `router.enabled` | `ASK_ROUTER_ENABLED` | `true` | Enable automatic model routing |
| `router.coding_model` | `ASK_ROUTER_CODING_MODEL` | `deepseek-coder:6.7b` | Model for coding/technical tasks |
| `router.summary_model` | `ASK_ROUTER_SUMMARY_MODEL` | `llama3.2:3b` | Model for summarization |
| `router.chat_model` | `ASK_ROUTER_CHAT_MODEL` | `llama3.2:3b` | Model for general chat |
| `router.analysis_model` | `ASK_ROUTER_ANALYSIS_MODEL` | `deepseek-coder:6.7b` | Model for code analysis |

## Example: Minimal Config

```json
{
  "default_model": "llama3.2:3b",
  "ollama_host": "http://localhost:11434",
  "memory_limit": 50
}
```

## Example: Full Config

See `config.example.json` in the repository root for a complete reference.

## Environment Variable Precedence

Settings are resolved in this order (later overrides earlier):

1. Defaults in `Settings` dataclass
2. Values from `~/.config/ask/config.json`
3. Environment variables (`ASK_*`)
4. In-app runtime changes
