from setuptools import setup, find_packages

setup(
    name="ask",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "typer",
        "rich",
        "ollama",
        "pyfiglet",
        "textual>=0.85.0",
    ],
    entry_points={
        "console_scripts": [
            "ask=ask.main:app",
        ],
    },
)
