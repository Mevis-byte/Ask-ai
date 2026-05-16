# Commands Reference

All commands are prefixed with `/` and available in both the Textual TUI and the plain-terminal REPL.

## Workspace Commands

| Command | Description |
|---------|-------------|
| `/workspace <folder>` | Load a project directory as AI context. Scans for text files (respecting ignore rules). |
| `/clear-context` | Reset workspace state. Clears loaded files and RAG index. |

## Session Commands

| Command | Description |
|---------|-------------|
| `/session <name>` | Switch to or create a named session. |
| `/sessions` | List all saved sessions. |
| `/save` | Persist the current session to SQLite. |
| `/export` | Export the full session transcript as Markdown. |

## Model Commands

| Command | Description |
|---------|-------------|
| `/model <name>` | Switch the active Ollama model. |
| `/models` | List all available models from the local Ollama instance. |

## File Commands

| Command | Description |
|---------|-------------|
| `/read <path>` | Read a file and include it as context. |
| `/find <pattern>` | Search for text in the project directory. |
| `/save-file <path>` | Write the last AI response to a file. |

## Analysis Commands

| Command | Description |
|---------|-------------|
| `/explain` | Ask the AI to explain the current context or the last output. |
| `/summarize <text>` | Have the AI summarize the given text or context. |
| `/review <file>` | Request a code review of the specified file. |

## Git Commands (read-only)

| Command | Description |
|---------|-------------|
| `/git-status` | Show the working tree status. |
| `/git-diff [file]` | Show unstaged and staged diffs. |
| `/git-log [n]` | Show recent commit history (default: 10). |
| `/explain-commit` | Send the current diff to the AI for explanation. |
| `/generate-commit` | Generate a commit message from the current diff. |

## Utility Commands

| Command | Description |
|---------|-------------|
| `/help` | Show the help text with all available commands. |
| `/copy` | Copy the last AI response to the clipboard. |
| `/print` | Print the last AI response to stdout. |
| `/clear` | Clear the current conversation. |
| `/quit` | Exit the application. |

## Keyboard Shortcuts (Textual TUI)

| Key | Action |
|-----|--------|
| `Ctrl+Y` | Copy last response to clipboard |
| `Ctrl+Q` | Quit the application |
| `Tab` | Cycle focus between panes |
| `Up/Down` | Navigate history in input |
