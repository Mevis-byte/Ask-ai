import typer

from ask.app.analysis import analyze_file
from ask.app.bootstrap import build_default_chat_app
from ask.config import load_settings
from ask.models import OllamaChatBackend
from ask.ui import ConsoleUI

app = typer.Typer()


@app.command()
def analyze(file: str) -> None:
    """Analyze a Python file using AI."""
    settings = load_settings()
    backend = OllamaChatBackend(host=settings.ollama_host)
    ui = ConsoleUI(settings)
    analyze_file(file, settings=settings, backend=backend, ui=ui)


@app.command()
def ai() -> None:
    """Launch Ask AI interface."""
    settings = load_settings()
    ui = ConsoleUI(settings)
    if settings.ui_startup_animation:
        ui.play_startup_animation()
    elif settings.show_banner_on_ai_command:
        ui.print_banner()
    ui.print_hint(settings.ui_exit_hint)
    build_default_chat_app(settings, ui).run()


@app.command()
def chat() -> None:
    """Start AI chat directly."""
    build_default_chat_app().run()


if __name__ == "__main__":
    app()
