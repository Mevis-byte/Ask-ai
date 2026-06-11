from __future__ import annotations

from rapidfuzz import fuzz, process


def fuzzy_score(query: str, choice: str) -> float:
    return fuzz.WRatio(query, choice) / 100.0


def fuzzy_filter(
    choices: list[str],
    query: str,
    *,
    score_cutoff: float = 0.3,
    limit: int = 30,
) -> list[tuple[str, float]]:
    results = process.extract(
        query, choices, scorer=fuzz.WRatio,
        limit=limit, score_cutoff=int(score_cutoff * 100),
    )
    return [(text, score / 100.0) for text, score, _ in results]


def fuzzy_filter_objects(
    objects: list[tuple[str, ...]],
    query: str,
    *,
    score_cutoff: float = 0.3,
    limit: int = 30,
) -> list[tuple]:
    if not query:
        return [obj + (1.0,) for obj in objects][:limit]
    choices = [obj[0] for obj in objects]
    results = process.extract(
        query, choices, scorer=fuzz.WRatio,
        limit=limit, score_cutoff=int(score_cutoff * 100),
    )
    out: list[tuple] = []
    for text, score, idx in results:
        obj = objects[idx]
        out.append(obj + (score / 100.0,))
    return out
