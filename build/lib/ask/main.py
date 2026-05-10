import typer
from ask.analyzer import analyze_code
from ask.chat import start_chat

app = typer.Typer()

@app.command()
def analyze(file: str):
    """Analyze a code file using AI"""
    result = analyze_code(file)
    print(result)

@app.command()
def chat():
    """Start AI chat session"""
    start_chat()

@app.command()
def hello():
    print("CLI working")

if __name__ == "__main__":
    app()