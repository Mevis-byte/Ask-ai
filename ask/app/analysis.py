from __future__ import annotations

from ask.config import Settings
from ask.models import OllamaChatBackend
from ask.ui import ConsoleUI


def analyze_file(
    file_path: str,
    *,
    settings: Settings,
    backend: OllamaChatBackend,
    ui: ConsoleUI,
) -> str:
    ui.print_status("Reading file…")
    with open(file_path, "r", encoding="utf-8") as handle:
        code = handle.read()

    ui.print_status("Sending prompt to AI…")
    prompt = f"Explain this code:\n\n{code}"
    with ui.thinking("NEURAL DECODE · model inference"):
        response = backend.chat(
            model=settings.analyze_model,
            messages=[{"role": "user", "content": prompt}],
            stream=False,
        )
    text = response["message"]["content"]
    ui.print_markdown(text)
    return text
