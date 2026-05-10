import ollama

def analyze_code(file_path):

    print("Reading file...")

    with open(file_path, "r") as f:
        code = f.read()

    print("Sending prompt to AI...")

    prompt = f"""
Explain this code:

{code}
"""

    response = ollama.chat(
        model="deepseek-coder:6.7b",
        messages=[{"role": "user", "content": prompt}]
    )

    print("AI responded!")

    return response["message"]["content"]