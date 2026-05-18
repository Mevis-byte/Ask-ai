from __future__ import annotations

from ask.rag.base import Document


def augment_user_message(user_text: str, documents: list[Document]) -> str:
    if not documents:
        return user_text
    blocks: list[str] = []
    blocks.append(
        "Relevant project context from semantic search (use only what is relevant):"
    )
    for i, doc in enumerate(documents, start=1):
        label = doc.source or f"doc-{i}"
        blocks.append(f"[{label}]\n{doc.text}")

    context = "\n\n".join(blocks)
    instructions = (
        "From the above context, use only information directly relevant to the question. "
        "If the context does not contain the answer, say so instead of guessing."
    )
    return f"{context}\n\n{instructions}\n\nUser:\n{user_text}"


def augment_with_structural_context(user_text: str,
                                     documents: list[Document],
                                     dependency_context: str | None = None,
                                     session_context: str | None = None) -> str:
    parts: list[str] = []
    if dependency_context:
        parts.append(
            f"Project dependency context:\n{dependency_context}"
        )
    if documents:
        docs_block: list[str] = []
        for i, doc in enumerate(documents, start=1):
            label = doc.source or f"doc-{i}"
            docs_block.append(f"[{label}]\n{doc.text}")
        parts.append("Semantic search results:\n" + "\n\n".join(docs_block))
    if session_context:
        parts.append(f"Session memory:\n{session_context}")

    if not parts:
        return user_text

    context = "\n\n---\n\n".join(parts)
    instructions = (
        "Use the above project context where relevant. "
        "If the context does not contain the answer, state that. "
        "Do not guess file paths, function names, or imports not visible in the provided context."
    )
    return f"{context}\n\n{instructions}\n\nUser:\n{user_text}"
