# ask.ai

> Offline AI workstation built for the terminal.

ask.ai is a local AI-powered terminal assistant designed for developers, Linux users, and cybersecurity enthusiasts who want fast AI assistance without relying on cloud services.

Built on top of Ollama and local LLMs, ask.ai runs completely offline, supports multiple models, streams responses in real time, analyzes files, remembers conversations locally, and provides a workstation-style terminal interface.

---

# Preview

## Neural Workstation UI

![ask.ai UI](./screenshots/askai1.png)

---

# Features

## Local & Offline

* Runs fully offline using Ollama
* No internet connection required
* Local-first workflow
* Better privacy and control over data

## Real-Time Streaming

* Token-by-token streaming responses
* Smooth terminal interaction
* Fast response rendering

## Multi-Model Support

Switch between different local models directly from the terminal.

Examples:

* llama3
* deepseek-coder
* mistral
* codellama

## File Intelligence

ask.ai can:

* read files
* explain code
* summarize files
* review source code
* analyze project structure

Supported workflows:

```bash
/explain main.py
/review app.js
/summarize config.yaml
```

## Local Memory System

* Persistent chat history
* SQLite-based memory
* Session tracking
* Local conversation storage

## Syntax Highlighting

* Rich-based code rendering
* Automatic language detection
* Clean terminal formatting

## Workstation UI

* Terminal-based interface
* Structured panels
* Status indicators
* Session management
* Retro workstation-inspired layout

---

# Tech Stack

| Component          | Technology                 |
| ------------------ | -------------------------- |
| AI Backend         | Ollama                     |
| Models             | LLaMA 3, DeepSeek, Mistral |
| Language           | Python                     |
| CLI Framework      | Typer                      |
| Terminal Rendering | Rich                       |
| TUI System         | Textual                    |
| Local Database     | SQLite                     |
| Packaging          | setuptools                 |

---

# Installation

## 1. Clone Repository

```bash
git clone https://github.com/Mevis-byte/Ask-ai.git
cd Ask-ai
```

---

## 2. Create Virtual Environment

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### Windows

```powershell
python -m venv venv
venv\Scripts\activate
```

---

## 3. Install Requirements

```bash
pip install -r requirements.txt
```

---

## 4. Install Ollama

Download Ollama:

[https://ollama.com](https://ollama.com)

Pull a model:

```bash
ollama pull llama3
```

Optional models:

```bash
ollama pull deepseek-coder:6.7b
ollama pull mistral
```

---

# Running ask.ai

```bash
python -m ask.main ai
```

or:

```bash
ask ai
```

---

# Commands

| Command              | Description           |
| -------------------- | --------------------- |
| `ask ai`             | Launch workstation UI |
| `ask chat`           | Start AI chat session |
| `ask analyze <file>` | Analyze source code   |
| `/read <file>`       | Display file contents |
| `/explain <file>`    | Explain file logic    |
| `/review <file>`     | Review code quality   |
| `/summarize <file>`  | Summarize file        |

---

# Project Structure

```text
ask/
├── app/
│   ├── chat.py
│   ├── workstation.py
│   └── session_manager.py
│
├── memory/
│   ├── sqlite_memory.py
│   └── factory.py
│
├── tools/
│   ├── file_reader.py
│   ├── analyzer.py
│   └── context_loader.py
│
├── ui/
│   └── workstation.py
│
└── main.py
```

---

# Why ask.ai?

Most AI assistants today are:

* cloud dependent
* subscription locked
* privacy invasive
* browser focused

ask.ai was built around a different idea:

```text
AI should feel like part of your operating system.
```

The goal is to create a local AI workstation that integrates naturally into terminal workflows while remaining private, customizable, and developer-focused.

---

# Roadmap

Planned features:

* Workspace-wide project context
* Plugin system
* Autonomous task mode
* Local RAG/document search
* Voice assistant mode
* Better session management
* Git integration
* Local embeddings support
* Improved Textual UI

---

# Security & Privacy

ask.ai is designed with a local-first workflow.

* Conversations stay on device
* Files are analyzed locally
* No cloud APIs required
* No external data collection

Current implementation is read-focused and avoids unrestricted system modification.

---

# Screenshots

## Main Interface

![Main UI](./screenshots/askai1.png)

---

# Contributing

Contributions, ideas, and improvements are welcome.

Possible areas:

* UI improvements
* Textual layouts
* plugin system
* memory improvements
* performance optimization
* model integrations

---

# Author

Mevis Lobo

GitHub:
[https://github.com/Mevis-byte](https://github.com/Mevis-byte)

---

# License

MIT License

