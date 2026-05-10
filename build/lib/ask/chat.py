import ollama

def start_chat():
    print("Offline AI Chat (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ")

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        response = ollama.chat(
            model="llama3",
            messages=[
                {"role": "user", "content": user_input}
            ]
        )

        print("\nAI:", response["message"]["content"])
        print()