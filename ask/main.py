import typer

from ask.app.analysis import analyze_file
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
    """Launch the Textual Ask AI workstation."""
    settings = load_settings()
    try:
        from ask.app.workstation import run_default_workstation
    except ModuleNotFoundError as exc:
        if exc.name == "textual":
            typer.echo("Textual is required for the workstation UI. Install project dependencies first.")
            raise typer.Exit(1) from exc
        raise
    run_default_workstation(settings)


@app.command()
def chat() -> None:
    """Start a plain-terminal AI chat session (selectable output)."""
    settings = load_settings()
    from ask.app.bootstrap import build_default_chat_app
    build_default_chat_app(settings).run()


if __name__ == "__main__":
    app()
