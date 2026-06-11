from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandSpec:
    category: str
    title: str
    command: str
    description: str

    @property
    def requires_argument(self) -> bool:
        return self.command.endswith(" ")


COMMANDS: tuple[CommandSpec, ...] = (
    CommandSpec("Workspace", "Analyze Workspace", "/workspace ", "Load a project folder as active context."),
    CommandSpec("Workspace", "Open Current Workspace", "/workspace .", "Load the current directory as active context."),
    CommandSpec("Workspace", "Show Context", "/context", "Show the active workspace context summary."),
    CommandSpec("Workspace", "Clear Context", "/clear-context", "Clear loaded workspace attachments."),
    CommandSpec("Workspace", "Find in Workspace", "/find ", "Search files in the active workspace."),
    CommandSpec("Files", "Read File", "/read ", "Display a file and attach it as context."),
    CommandSpec("Files", "Explain File", "/explain ", "Ask the active model to explain a source file."),
    CommandSpec("Files", "Summarize File", "/summarize ", "Ask the active model for a short file summary."),
    CommandSpec("Files", "Review File", "/review ", "Ask the active model to review a source file."),
    CommandSpec("Git", "Git Status", "/git-status", "Show read-only working tree status."),
    CommandSpec("Git", "Git Diff", "/git-diff", "Show unstaged diff."),
    CommandSpec("Git", "Git Log", "/git-log", "Show recent commits."),
    CommandSpec("Git", "Git Review", "/git-review", "Review current changes with the active model."),
    CommandSpec("Git", "Explain Commit", "/explain-commit", "Explain staged or unstaged changes."),
    CommandSpec("Git", "Generate Commit Message", "/generate-commit", "Generate a commit message from the diff."),
    CommandSpec("Sessions", "New Session", "/new", "Create a new chat session."),
    CommandSpec("Sessions", "Save Session", "/save", "Mark the current session saved."),
    CommandSpec("Sessions", "Rename Session", "/rename ", "Rename the current session."),
    CommandSpec("Sessions", "List Sessions", "/sessions", "List saved and recent sessions."),
    CommandSpec("Sessions", "Switch Session", "/session ", "Open the session picker or switch by id/title."),
    CommandSpec("Sessions", "Session History", "/history ", "Search sessions by title, id, or summary."),
    CommandSpec("Sessions", "Clear Session", "/clear", "Clear the current transcript."),
    CommandSpec("Models", "Switch Model", "/model ", "Open the model picker or switch by name."),
    CommandSpec("Models", "List Models", "/models", "Refresh installed Ollama models."),
    CommandSpec("Models", "Set Ollama Host", "/baseurl ", "Change the Ollama server URL."),
    CommandSpec("Export", "Save Last Response", "/save-file ", "Save the last assistant response to a file."),
    CommandSpec("Export", "Export Session", "/export", "Export the current transcript as Markdown."),
    CommandSpec("Export", "Copy Last Response", "/copy", "Copy the last assistant response."),
    CommandSpec("Export", "Print Last Response", "/print", "Print the last response to terminal scrollback."),
    CommandSpec("Settings", "Help", "/help", "Show command help."),
    CommandSpec("Settings", "Quit", "/quit", "Exit ASK.AI."),
)


def command_names() -> list[str]:
    return [spec.command.rstrip() for spec in COMMANDS]


def command_help_lines() -> list[str]:
    lines: list[str] = []
    current = ""
    for spec in COMMANDS:
        if spec.category != current:
            current = spec.category
            lines.append(f"-- {current.lower()} --")
        lines.append(f"{spec.command:<18} {spec.description}")
    return lines
