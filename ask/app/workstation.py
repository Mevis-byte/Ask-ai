from __future__ import annotations

from ask.app.session_manager import ChatSessionManager
from ask.config import Settings, load_settings
from ask.files import LocalFileContext
from ask.models import OllamaChatBackend
from ask.plugins import PluginRegistry
from ask.rag import create_retriever
from ask.ui.workstation import AskWorkstationApp


def build_default_workstation_app(settings: Settings | None = None) -> AskWorkstationApp:
    settings = settings or load_settings()
    return AskWorkstationApp(
        settings=settings,
        backend=OllamaChatBackend(host=settings.ollama_host),
        session_manager=ChatSessionManager(settings),
        file_context=LocalFileContext(),
        retriever=create_retriever(settings),
        plugins=PluginRegistry(),
    )


def run_default_workstation(settings: Settings | None = None) -> None:
    build_default_workstation_app(settings).run()
