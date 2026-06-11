from setuptools import setup, find_packages

setup(
    name="ask",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "typer",
        "rich",
        "ollama",
        "pyfiglet",
        "rapidfuzz>=3.0.0",
        "textual>=0.85.0",
    ],
    extras_require={
        "rag": [
            "chromadb>=0.5.0",
            "sentence-transformers>=2.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "ask=ask.main:app",
        ],
    },
)
