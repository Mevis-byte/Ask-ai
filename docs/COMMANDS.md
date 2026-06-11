# Commands Reference

Commands are prefixed with `/`. The Textual workstation also exposes these through `Ctrl+P`.

## Workspace Commands

| Command | Description |
|---------|-------------|
| `/workspace <folder>` | Load a project directory as AI context. Scans for text files (respecting ignore rules). |
| `/context` | Show the active workspace summary. |
| `/clear-context` | Reset workspace state. Clears loaded files and RAG index. |

## Session Commands

| Command | Description |
|---------|-------------|
| `/new` | Create a fresh session. |
| `/session <id\|num\|title>` | Switch to a session. With no argument, opens the session picker in the TUI. |
| `/resume <id\|num\|title>` | Alias for `/session`. With no argument, opens the session picker in the TUI. |
| `/sessions` | List sessions using readable titles. |
| `/history [query]` | Search sessions by title, id, or summary. |
| `/save [title]` | Mark the current session saved; optional title updates the title. |
| `/rename <title>` | Rename the current session without changing saved status. |
| `/clear` | Clear the current transcript. |
| `/export` | Export the full session transcript as Markdown. |

## Model Commands

| Command | Description |
|---------|-------------|
| `/model <name>` | Switch the active Ollama model. With no argument, opens the model picker in the TUI. |
| `/models` | List all available models from the local Ollama instance. |
| `/baseurl <url\|host>` | Change the Ollama host. |

## File Commands

| Command | Description |
|---------|-------------|
| `/read <path>` | Read a file and include it as context. |
| `/find <pattern>` | Search for text in the project directory. |
| `/save-file <path>` | Write the last AI response to a file. |

## Analysis Commands

| Command | Description |
|---------|-------------|
| `/explain <file>` | Ask the AI to explain a file. |
| `/summarize <file>` | Ask the AI to summarize a file. |
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
| `Ctrl+P` | Open command palette |
| `Ctrl+N` | New session |
| `Ctrl+S` | Save current session |
| `Ctrl+Y` | Copy last response to clipboard |
| `Ctrl+C` | Quit request; press twice quickly to exit |
| `Tab` | Cycle focus between panes |
| `Up/Down` | Navigate history in input |
| `Esc` | Leave the home screen or close modal overlays |

See [KEYBOARD_SHORTCUTS.md](./KEYBOARD_SHORTCUTS.md) for a focused shortcut guide.
