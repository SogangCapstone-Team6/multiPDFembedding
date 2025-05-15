# src/search/fine_search.py

import numpy as np

def fine_search_chunks(query_emb, chunk_index, target_sections, top_k=10):
    """
    chunk_index: [{ "embedding": [...], "metadata": {"section_title": "...", ...}}, ...]
    target_sections: [{ "title": "2장 설치방법", ...}, ...]

    - target_sections에 포함된 섹션 title만 필터링
    - 코사인 유사도 내림차순으로 상위 top_k 청크 반환
    """
    section_titles = [sec["title"] for sec in target_sections]

    candidates = [
        item for item in chunk_index
        if item["metadata"]["section_title"] in section_titles
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