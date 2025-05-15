# scripts/build_vector_db.py

import os
import json
import hashlib
import glob
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
LOG_PATH = "data/processed_pdfs.log"
CHUNK_SIZE = 500

os.makedirs(EXTRACTED_DIR, exist_ok=True)
os.makedirs(CHUNK_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

def get_pdf_hash(pdf_path):
    with open(pdf_path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()

# 기존 처리된 PDF 해시 불러오기
if os.path.exists(LOG_PATH):
    with open(LOG_PATH, 'r', encoding='utf-8') as f:
        processed_hashes = set(line.strip() for line in f)
else:
    processed_hashes = set()

# 통합 적켜야 하는 정보
all_sections = []
all_vectors = []

for fname in os.listdir(RAW_DIR):
    if not fname.lower().endswith(".pdf"):
        continue

    pdf_path = os.path.join(RAW_DIR, fname)
    file_hash = get_pdf_hash(pdf_path)

    if file_hash in processed_hashes:
        print(f"[SKIP] {fname} already processed.")
        continue

    print(f"[PROCESSING] {fname}")
    try:
        # 1. 세트션 추출
        extracted = extract_pdf_content(pdf_path)
        sections = extracted["sections"]

        for sec in sections:
            sec["source_pdf"] = fname
        all_sections.extend(sections)

        # 2. 체크 나누기
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

        # 경로에 다시 결과 저장
        base_name = os.path.splitext(fname)[0]
        with open(os.path.join(EXTRACTED_DIR, f"{base_name}.json"), 'w', encoding='utf-8') as f:
            json.dump(extracted, f, ensure_ascii=False, indent=2)

        with open(os.path.join(CHUNK_DIR, f"{base_name}_chunks.json"), 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        with open(os.path.join(INDEX_DIR, f"{base_name}_vectors.json"), 'w', encoding='utf-8') as f:
            json.dump(all_vectors, f, ensure_ascii=False, indent=2)

        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(file_hash + "\n")

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
