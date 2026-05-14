from __future__ import annotations

from ask.app.chat import ChatApplication
from ask.config import Settings, load_settings
from ask.memory import create_chat_memory
from ask.models import OllamaChatBackend
from ask.plugins import PluginRegistry
from ask.rag import create_retriever
from ask.ui import ConsoleUI


def build_default_chat_app(
    settings: Settings | None = None,
    ui: ConsoleUI | None = None,
) -> ChatApplication:
    settings = settings or load_settings()
    ui = ui or ConsoleUI(settings)
    return ChatApplication(
        settings=settings,
        ui=ui,
        backend=OllamaChatBackend(host=settings.ollama_host),
        memory=create_chat_memory(settings),
        retriever=create_retriever(settings),
        plugins=PluginRegistry(),
    )
