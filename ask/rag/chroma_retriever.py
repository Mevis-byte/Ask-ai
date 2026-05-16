from __future__ import annotations

from pathlib import Path

from ask.rag.base import Document, Retriever


class ChromaRetriever:
    """Lightweight semantic file-content retriever using Ollama embeddings via ChromaDB."""

    def __init__(
        self,
        *,
        persist_directory: str | Path,
        embedding_model: str = "all-MiniLM-L6-v2",
        collection_name: str = "project_files",
    ) -> None:
        self._persist = Path(persist_directory).expanduser().resolve()
        self._embedding_model = embedding_model
        self._collection_name = collection_name
        self._collection = None
        self._chroma = None
        self._embedding_fn = None

    def _lazy_init(self) -> None:
        if self._chroma is not None:
            return
        try:
            import chromadb
            from chromadb.utils import embedding_functions
        except ImportError:
            raise ImportError("chromadb is required. Install: pip install chromadb")

        self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=self._embedding_model
        )
        self._persist.mkdir(parents=True, exist_ok=True)
        self._chroma = chromadb.PersistentClient(str(self._persist))
        self._collection = self._chroma.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._embedding_fn,
        )

    def index_file(self, file_path: str | Path, content: str, metadata: dict | None = None) -> None:
        self._lazy_init()
        path = str(file_path)
        existing = self._collection.get(ids=[path])
        meta = {"source": path}
        if metadata:
            meta.update(metadata)
        if existing["ids"]:
            self._collection.update(ids=[path], documents=[content], metadatas=[meta])
        else:
            self._collection.add(ids=[path], documents=[content], metadatas=[meta])

    def remove_file(self, file_path: str | Path) -> None:
        self._lazy_init()
        try:
            self._collection.delete(ids=[str(file_path)])
        except Exception:
            pass

    def clear(self) -> None:
        if self._chroma is None:
            return
        try:
            self._chroma.delete_collection(self._collection_name)
        except Exception:
            pass
        self._collection = self._chroma.get_or_create_collection(
            name=self._collection_name,
            embedding_function=self._embedding_fn,
        )

    def retrieve(self, query: str, *, top_k: int = 4) -> list[Document]:
        if not query.strip():
            return []
        self._lazy_init()
        try:
            results = self._collection.query(query_texts=[query], n_results=top_k)
        except Exception:
            return []
        docs: list[Document] = []
        if results["documents"] and results["metadatas"]:
            for texts, metas in zip(results["documents"], results["metadatas"]):
                for text, meta in zip(texts, metas):
                    source = (meta or {}).get("source")
                    docs.append(Document(text=str(text or ""), source=str(source) if source else None))
        return docs

    def count(self) -> int:
        if self._chroma is None:
            return 0
        try:
            return self._collection.count()
        except Exception:
            return 0
