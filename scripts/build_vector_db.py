# scripts/build_vector_db.py

import os
import json
import hashlib
import numpy as np
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.pdf_extractor import extract_pdf_content
from scripts.chunker import chunk_sections
from src.inference.embedding_model import embedding_model
from scripts.section_rep_builder import build_section_reps

RAW_DIR = "data/raw"
EXTRACTED_DIR = "data/extracted"
CHUNK_DIR = "data/chunks"
INDEX_DIR = "data/index"
CHUNK_SIZE = 500

os.makedirs(EXTRACTED_DIR, exist_ok=True)
os.makedirs(CHUNK_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# 통합 시켜야 하는 정보
all_sections = []
all_vectors = []

for fname in os.listdir(RAW_DIR):
    if not fname.lower().endswith(".pdf"):
        continue

    base_name = os.path.splitext(fname)[0]
    chunk_file_path = os.path.join(CHUNK_DIR, f"{base_name}_chunks.json")

    # 처리된 PDF인지 확인: chunk 결과 파일이 있으면 SKIP
    if os.path.exists(chunk_file_path):
        print(f"[SKIP] {fname} already processed (chunk file exists).")
        continue

    pdf_path = os.path.join(RAW_DIR, fname)

    print(f"[PROCESSING] {fname}")
    try:
        # 1. 섹션 추출
        extracted = extract_pdf_content(pdf_path)
        sections = extracted["sections"]

        for sec in sections:
            sec["source_pdf"] = fname
        all_sections.extend(sections)

        # 2. 섹션을 chunk로 나누기
        chunks = chunk_sections(sections, chunk_size=CHUNK_SIZE)

        # 3. 임베딩 생성
        contents = [chunk["text"] for chunk in chunks]
        embeddings = embedding_model.get_embeddings(contents)

        # 4. 버퍼 + 메타데이터
        for i, emb in enumerate(embeddings):
            all_vectors.append({
                "embedding": emb.tolist(),
                "metadata": {
                    **chunks[i],
                    "source_pdf": fname
                }
            })

        # 5. 결과 저장
        with open(os.path.join(EXTRACTED_DIR, f"{base_name}.json"), 'w', encoding='utf-8') as f:
            json.dump(extracted, f, ensure_ascii=False, indent=2)

        with open(chunk_file_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        with open(os.path.join(INDEX_DIR, f"{base_name}_vectors.json"), 'w', encoding='utf-8') as f:
            json.dump(all_vectors, f, ensure_ascii=False, indent=2)

        print(f"[DONE] {fname}: {len(chunks)} chunks, {len(contents)} embeddings")

    except Exception as e:
        print(f"[ERROR] {fname}: {str(e)}")

# sections.json 저장
with open(os.path.join(EXTRACTED_DIR, "sections.json"), 'w', encoding='utf-8') as f:
    json.dump(all_sections, f, ensure_ascii=False, indent=2)

# section_rep_builder 함수 사용해 coarse search용 embedding 추가
updated_sections = build_section_reps(all_sections, all_vectors)
with open(os.path.join(EXTRACTED_DIR, "sections_with_emb.json"), 'w', encoding='utf-8') as f:
    json.dump(updated_sections, f, ensure_ascii=False, indent=2)

with open(os.path.join(INDEX_DIR, "full_vectors.json"), 'w', encoding='utf-8') as f:
    json.dump(all_vectors, f, ensure_ascii=False, indent=2)

print("All PDFs processed.")
