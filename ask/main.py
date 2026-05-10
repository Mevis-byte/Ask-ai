import typer
from ask.analyzer import analyze_code
from ask.chat import start_chat
from pyfiglet import Figlet
from rich import print

app = typer.Typer()

@app.command()
def analyze(file: str):
    """Analyze a Python file using AI"""
    analyze_code(file)


@app.command()
def ai():
    """Launch Ask AI interface"""

    f = Figlet(font="slant")
    ascii_art = f.renderText("ASK AI")

    print(f"[bold magenta]{ascii_art}[/bold magenta]")
    print("[bold magenta]Offline Developer AI Assistant[/bold magenta]\n")

    print("[cyan]Type 'exit' to quit the AI[/cyan]\n")

    start_chat()


@app.command()
def chat():
    """Start AI chat directly"""
    start_chat()


if __name__ == "__main__":
    app()