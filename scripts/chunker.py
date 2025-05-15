# scripts/chunker.py

import os
import json
from typing import List, Dict, Any
from src.utils.text_cleaning import basic_clean_text  

CHUNK_SIZE = 500  # 글자 기준

def chunk_sections(sections: List[Dict[str, Any]], chunk_size: int = 500) -> List[Dict[str, Any]]:
    chunked = []
    for sec in sections:
        text = basic_clean_text(sec["text"])
        start = 0
        chunk_idx = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end].strip()
            if chunk_text:
                chunked.append({
                    "section": sec["section"],
                    "start_page": sec["start_page"],
                    "end_page": sec["end_page"],
                    "chunk_index": chunk_idx,
                    "text": chunk_text
                })
                chunk_idx += 1
            start = end
    return chunked

if __name__ == "__main__":
    extracted_folder = "data/extracted"
    chunk_folder = "data/chunks"
    os.makedirs(chunk_folder, exist_ok=True)

    for fname in os.listdir(extracted_folder):
        if fname.endswith(".json") and fname != "sections.json":
            path = os.path.join(extracted_folder, fname)
            with open(path, 'r', encoding='utf-8') as f:
                extracted = json.load(f)

            sections = extracted.get("sections", [])
            chunked_data = chunk_sections(sections, chunk_size=CHUNK_SIZE)

            base_name = os.path.splitext(fname)[0]
            out_json = os.path.join(chunk_folder, f"{base_name}_chunks.json")
            with open(out_json, 'w', encoding='utf-8') as f:
                json.dump(chunked_data, f, ensure_ascii=False, indent=2)

            print(f"[OK] Chunked: {fname} → {len(chunked_data)} chunks")
    
    print("Section-based Chunking Complete.")
