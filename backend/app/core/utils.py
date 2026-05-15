from typing import List, Dict, Any
import numpy as np


def min_max_normalize(scores: List[float]) -> List[float]:
    if not scores:
        return []
    min_s = min(scores)
    max_s = max(scores)
    if max_s == min_s:
        return [1.0] * len(scores)
    return [(s - min_s) / (max_s - min_s) for s in scores]


def reciprocal_rank_fusion(
    result_lists: List[List[Dict[str, Any]]],
    doc_key_fn,
    k: int = 60,
) -> List[Dict[str, Any]]:
    scores: Dict[str, float] = {}
    docs: Dict[str, Dict[str, Any]] = {}

    for results in result_lists:
        for rank, doc in enumerate(results):
            key = doc_key_fn(doc)
            rrf_score = 1.0 / (k + rank + 1)
            scores[key] = scores.get(key, 0.0) + rrf_score
            if key not in docs:
                docs[key] = doc

    merged = [(key, scores[key]) for key in scores]
    merged.sort(key=lambda x: x[1], reverse=True)

    output = []
    for key, score in merged:
        entry = dict(docs[key])
        entry["rrf_score"] = round(score, 6)
        output.append(entry)
    return output


def mmr_diversify(
    candidates: List[Dict[str, Any]],
    query_embedding: List[float],
    content_key: str = "content",
    lambda_param: float = 0.7,
    top_k: int = 5,
    get_embedding_fn=None,
) -> List[int]:
    n = len(candidates)
    if n <= top_k:
        return list(range(n))

    selected: List[int] = []
    remaining = set(range(n))

    sim_cache: Dict[int, float] = {}
    for i in range(n):
        if get_embedding_fn is not None:
            doc_emb = get_embedding_fn(candidates[i][content_key])
        else:
            arr = np.array([0.0])
            doc_emb = arr.tolist()
        sim_cache[i] = np.dot(query_embedding, doc_emb) / (
            np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb)
        )

    first = max(remaining, key=lambda i: sim_cache.get(i, 0.0))
    selected.append(first)
    remaining.remove(first)

    doc_embs: Dict[int, List[float]] = {}
    if get_embedding_fn is not None:
        for i in range(n):
            doc_embs[i] = get_embedding_fn(candidates[i][content_key])

    doc_sim_cache: Dict[str, float] = {}

    def _doc_sim(i: int, j: int) -> float:
        key = f"{min(i, j)}_{max(i, j)}"
        if key in doc_sim_cache:
            return doc_sim_cache[key]
        if get_embedding_fn is None or i not in doc_embs or j not in doc_embs:
            return 0.0
        a = np.array(doc_embs[i])
        b = np.array(doc_embs[j])
        val = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        doc_sim_cache[key] = float(val)
        return float(val)

    while remaining and len(selected) < top_k:
        best_score = -float("inf")
        best_idx = -1
        for i in remaining:
            query_sim = sim_cache.get(i, 0.0)
            max_red = 0.0
            for s in selected:
                ds = _doc_sim(i, s)
                if ds > max_red:
                    max_red = ds
            mmr = lambda_param * query_sim - (1 - lambda_param) * max_red
            if mmr > best_score:
                best_score = mmr
                best_idx = i
        selected.append(best_idx)
        remaining.remove(best_idx)

    return selected
