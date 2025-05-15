# scripts/build_index.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
import numpy as np
from src.inference.embedding_model import embedding_model

def build_chunk_index(chunks):
    """
    chunks: [{"text": "...", "section": "...", ...}, ...]
    임베딩 모델로 각 chunk["text"]를 임베딩하고,
    metadata 포함한 벡터 리스트 반환
    """
    contents = [c["text"] for c in chunks]  
    embeddings = embedding_model.get_embeddings(contents)

    index_data = []
    for i, emb in enumerate(embeddings):
        index_data.append({
            "embedding": emb.tolist(),
            "metadata": chunks[i]
        })
    return index_data

if __name__ == "__main__":
    chunk_folder = "data/chunks"
    index_folder = "data/index"
    os.makedirs(index_folder, exist_ok=True)

    for fname in os.listdir(chunk_folder):
        if fname.endswith("_chunks.json"):
            path = os.path.join(chunk_folder, fname)
            with open(path, 'r', encoding='utf-8') as f:
                chunked_data = json.load(f)

            index_data = build_chunk_index(chunked_data)

            base_name = os.path.splitext(fname)[0]
            out_path = os.path.join(index_folder, f"{base_name}_vectors.json")
            with open(out_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Indexed: {fname} → {len(index_data)} vectors")

    print("Build index complete.")
