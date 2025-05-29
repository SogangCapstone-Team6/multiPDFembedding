# src/search/fine_search.py

import numpy as np

# src/search/fine_search.py
def fine_search_chunks(query_emb, chunk_index, target_sections, top_k=10):
    """
    chunk_index: [{ "embedding": [...], "metadata": {"section_title": "...", ...}}, ...]
    target_sections: [{ "section": "2장 설치방법", ...}, ...]  # "title" 대신 "section" 사용
    """
    section_titles = [sec["section"] for sec in target_sections]  # "title" -> "section"으로 변경

    candidates = [
        item for item in chunk_index
        if item["metadata"]["section"] in section_titles  # "section_title" -> "section"으로 변경
    ]

    results = []
    qv = np.array(query_emb)
    q_norm = np.linalg.norm(qv)
    for c in candidates:
        emb = np.array(c["embedding"])
        dot = np.dot(qv, emb)
        denom = np.linalg.norm(emb) * q_norm + 1e-8
        cos_val = dot / denom
        results.append((cos_val, c))

    results.sort(key=lambda x: x[0], reverse=True)
    top_results = [r[1] for r in results[:top_k]]
    return top_results


def fast_fine_search(query_emb, chunk_index, top_k=10):
    results = []
    qv = np.array(query_emb)
    q_norm = np.linalg.norm(qv)

    for item in chunk_index:
        emb = np.array(item["embedding"])
        dot = np.dot(qv, emb)
        denom = np.linalg.norm(emb) * q_norm + 1e-8
        cos_val = dot / denom
        results.append((cos_val, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in results[:top_k]]