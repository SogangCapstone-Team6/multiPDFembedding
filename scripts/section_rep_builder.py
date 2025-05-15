# scripts/section_rep_builder.py

import sys
import os
import glob
import json
import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.inference.embedding_model import embedding_model

def build_section_reps(sections, chunk_index):
    """
    sections: [
      { "section": "2장 설치방법", "start_page":10, "end_page":19, ... },
      ...
    ]
    chunk_index: [{ "embedding": [...], "metadata": {"section": "...", ...}}, ...]
    
    → 각 섹션에 sec["title_emb"], sec["avg_chunk_emb"] 추가
    """
    # 1) 섹션 제목 임베딩
    titles = [sec["section"] for sec in sections]
    title_embs = embedding_model.get_embeddings(titles)
    for i, sec in enumerate(sections):
        sec["title_emb"] = title_embs[i].tolist()

    # 2) 섹션별 청크 임베딩 그룹핑
    section2embs = {}
    for item in chunk_index:
        sec_t = item["metadata"]["section"]
        emb = item["embedding"]
        if sec_t not in section2embs:
            section2embs[sec_t] = []
        section2embs[sec_t].append(emb)

    # 3) 평균 임베딩 추가
    for sec in sections:
        stitle = sec["section"]
        if stitle not in section2embs:
            sec["avg_chunk_emb"] = None
        else:
            arr = np.array(section2embs[stitle])
            sec["avg_chunk_emb"] = arr.mean(axis=0).tolist()
    
    return sections

if __name__ == "__main__":
    sections_json = "data/extracted/sections.json"
    with open(sections_json, 'r', encoding='utf-8') as f:
        sections_data = json.load(f)

    vector_files = glob.glob("data/index/*_chunks_vectors.json")
    if not vector_files:
        raise FileNotFoundError("No chunk vectors found in 'data/index/'.")

    vector_files.sort(key=os.path.getmtime, reverse=True)
    chunk_index_json = vector_files[0]
    print(f"[INFO] Using chunk index file: {chunk_index_json}")

    with open(chunk_index_json, 'r', encoding='utf-8') as f:
        chunk_index_data = json.load(f)

    updated_sections = build_section_reps(sections_data, chunk_index_data)

    out_path = "data/extracted/sections_with_emb.json"
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(updated_sections, f, ensure_ascii=False, indent=2)

    print("[INFO] Section reps built and saved to:", out_path)
