# Roadmap

## v0.6.0 (Next)

- [ ] **Agent mode** — allow ask.ai to autonomously execute approved terminal commands (e.g., `npm test`, `ruff check`) with user confirmation.
- [ ] **Plugin API** — stable plugin interface for third-party extensions (tools, retrievers, commands).
- [ ] **Session search** — full-text search across all saved sessions.
- [ ] **Workspace watch mode** — auto-reindex workspace files on change (using `inotify` / `watchdog`).
- [ ] **Token usage tracking** — per-model and per-session token counters.
- [ ] **Theme customization** — user-configurable color themes for the TUI.

## v0.7.0

- [ ] **Multi-turn agent loops** — chain multiple tool calls (read, search, git) in a single agentic request.
- [ ] **Streaming RAG** — incremental indexing UI for large workspaces.
- [ ] **Diff viewer** — inline diff display in the Textual chat pane.
- [ ] **Custom commands** — user-defined shortcuts and command sequences.
- [ ] **Performance** — lazy file loading, file caching, faster workspace scanning.

## Future / Ideas

- [ ] Multi-modal support (image understanding via LLaVA / llava models)
- [ ] MCP server support via stdin/stdout
- [ ] Conversation branching / forking
- [ ] API mode (HTTP server for external tool integration)
- [ ] Vim/Neovim integration plugin
- [ ] Docker-based install: `docker run ask.ai`
- [ ] Interactive debugger integration (pdb, ipdb)
- [ ] Batch mode: non-interactive script execution

## Non-Goals

- Cloud-hosted model inference
- User accounts or authentication
- Multi-user collaboration features
- Web UI or GUI (beyond the terminal TUI)
- Mobile support
- Commercial licensing / enterprise features
