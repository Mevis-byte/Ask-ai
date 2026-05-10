import ollama
from rich.console import Console
from rich.markdown import Markdown

console = Console()

def start_chat():

    console.print("[bold green]ASK AI Chat (type 'exit' to quit)[/bold green]\n")

    while True:
        user_input = input("You > ")

        if user_input.lower() == "exit":
            break

        console.print("\n[bold cyan]AI Response:[/bold cyan]\n")

        response = ollama.chat(
            model="llama3",
            messages=[{"role": "user", "content": user_input}],
            stream=True
        )

        full_response = ""

        for chunk in response:
            content = chunk["message"]["content"]
            full_response += content
            print(content, end="", flush=True)

        console.print(Markdown(full_response))