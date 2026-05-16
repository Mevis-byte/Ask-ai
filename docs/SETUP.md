# Setup

## Prerequisites

- **Python 3.11+**
- **Ollama** — [ollama.com](https://ollama.com)
- A local LLM model pulled via Ollama

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Mevis-byte/Ask-ai.git
cd Ask-ai
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. (Optional) Install RAG dependencies

Required for semantic search and vector indexing:

```bash
pip install chromadb sentence-transformers
# or
pip install "ask[rag]"
```

### 5. Install and start Ollama

```bash
# Linux / macOS
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3.2:3b
```

### 6. Configure

Copy the example config and adjust as needed:

```bash
mkdir -p ~/.config/ask
cp config.example.json ~/.config/ask/config.json
```

### 7. Run

```bash
# Textual TUI (recommended)
python -m ask.main ai

# Plain-terminal REPL
python -m ask.main chat

# One-shot analysis
python -m ask.main analyze path/to/file.py
```

## Platform Notes

### Linux
Works out of the box. Ensure `python3-venv` is installed if using a venv.

### macOS
Tested on macOS 14+ with Homebrew Python. Clipboard commands require `pbcopy`.

### Windows
Tested in WSL2. Native Windows support is not currently tested.

## Troubleshooting

**Ollama connection refused** — ensure Ollama is running: `ollama serve`

**Model not found** — pull the model: `ollama pull llama3.2:3b`

**RAG import error** — ChromaDB or sentence-transformers not installed:
```bash
pip install chromadb sentence-transformers
```

**Textual TUI display issues** — ensure your terminal supports true color (modern terminals: Kitty, iTerm2, Windows Terminal, GNOME Terminal). Fall back to `ask chat` for plain-terminal mode.

**Permission errors on workspace** — ask.ai respects filesystem permissions. Ensure the workspace directory is readable.

## Uninstall

```bash
# Remove the application files
rm -rf /path/to/Ask-ai

# Remove configuration and data
rm -rf ~/.config/ask ~/.local/share/ask

# Uninstall Ollama (optional)
# https://ollama.com
```
