from __future__ import annotations

from ask.rag.base import Document


def augment_user_message(user_text: str, documents: list[Document]) -> str:
    """Prefix retrieved context to the user turn (simple RAG prompt shape)."""
    if not documents:
        return user_text
    blocks = []
    for i, doc in enumerate(documents, start=1):
        label = doc.source or f"doc-{i}"
        blocks.append(f"[{label}]\n{doc.text}")
    context = "\n\n".join(blocks)
    return f"Use the following context when answering.\n\n{context}\n\nUser:\n{user_text}"
