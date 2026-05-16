# Contributing to ask.ai

Thanks for considering contributing. ask.ai is a local-first AI workstation for the terminal, and contributions that respect its offline, developer-focused identity are always welcome.

## Project Setup

```bash
# Clone the repository
git clone https://github.com/Mevis-byte/Ask-ai.git
cd Ask-ai

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install RAG dependencies (optional, for vector search)
pip install chromadb sentence-transformers

# Install Ollama and pull a model
# https://ollama.com
ollama pull llama3
```

## Development Workflow

1. Create a branch for your change:

   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes. Keep them focused on a single concern.

3. Run the application to verify it works:

   ```bash
   python -m ask.main ai
   ```

4. Ensure all existing source files are syntactically valid:

   ```bash
   python3 -m py_compile ask/main.py
   # repeat for any files you changed
   ```

5. Commit your changes (see commit message guidelines below).

6. Push and open a pull request.

## Coding Style

- **Follow the existing patterns.** The codebase uses protocol-based abstractions (`typing.Protocol`), dataclasses for data objects, and factory functions for construction. Mimic the style you see in neighboring files.
- **No comments unless the code cannot be made self-documenting.** Prefer clear variable names and small functions over inline explanations.
- **Type hints everywhere.** All function signatures should be annotated.
- **No external dependencies unless necessary.** If you add one, justify it in the PR description.
- **Keep it local.** ask.ai is an offline tool. Avoid introducing cloud dependencies or telemetry.
- **Error handling.** Use specific exception types. Catch at the appropriate layer. Avoid bare `except:`.
- **Imports.** Standard library first, then third-party, then local. One import group per section.

Example:

```python
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from rich.text import Text

from ask.config import Settings
```

## Pull Request Process

1. Open an issue describing the problem or feature before starting work. This avoids duplicated effort.
2. Keep PRs small and focused on a single feature or bug fix.
3. In the PR description, explain what changed and why.
4. If the PR adds a new command, include the `/help` snippet and update the relevant documentation.
5. Do not commit generated files (`.pyc`, `__pycache__`, vector database indexes, SQLite files, etc.).
6. The maintainer will review and may request changes. Be responsive.

## Commit Message Recommendations

Use conventional commits:

```
feat: add semantic search via ChromaDB
fix: prevent crash on empty workspace directory
docs: add RAG architecture documentation
refactor: extract retriever factory from chat module
chore: bump textual to 8.2.6
```

- First line under 72 characters.
- Use the imperative mood ("add" not "added" or "adds").
- Reference issues when relevant: `fix: handle missing config file (#42)`

## Contribution Philosophy

ask.ai is designed to be:

- **Local-first.** Everything runs on your machine. No cloud, no telemetry, no accounts.
- **Developer-focused.** Terminal workflows, not web UIs.
- **Modular.** Components should be replaceable. If you want to swap out the model backend, memory store, or UI, the architecture should support it.
- **Stable.** Avoid breaking changes. If a change is breaking, it needs a strong justification and a migration path.

If you are unsure about an approach, open an issue first. Discussion is better than a reverted PR.

## What to Work On

- Bug fixes and edge cases in existing features.
- Improving the Textual TUI (keyboard navigation, theming, layout).
- Additional plugin implementations.
- Performance improvements for file scanning and RAG indexing.
- Better error messages and recovery.
- Documentation improvements.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
