import os
import json
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.chunker import chunk_sections
from src.inference.embedding_model import embedding_model
from scripts.section_rep_builder import build_section_reps

# 디렉토리 설정
EXTRACTED_DIR = "data/extracted"
CHUNK_DIR = "data/chunks"
INDEX_DIR = "data/index"
CHUNK_SIZE = 500

# 디렉토리 생성
os.makedirs(CHUNK_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# 통합 시켜야 하는 정보
all_sections = []
all_vectors = []

# 1. extracted 디렉토리의 모든 json 파일 읽기
print(f"[LOADING] Reading extracted sections from {EXTRACTED_DIR}")
for fname in os.listdir(EXTRACTED_DIR):
    if not fname.lower().endswith(".json"):
        continue

    extracted_file_path = os.path.join(EXTRACTED_DIR, fname)
    base_name = os.path.splitext(fname)[0]
    pdf_name = base_name  # 파일 이름이 PDF 이름과 동일하다고 가정

    print(f"[PROCESSING] Loading {fname}")
    try:
        with open(extracted_file_path, 'r', encoding='utf-8') as f:
            extracted = json.load(f)
            sections = extracted.get("sections", [])

        # 섹션에 source_pdf 추가 (필요 시)
        for sec in sections:
            if "source_pdf" not in sec:
                sec["source_pdf"] = pdf_name
        all_sections.extend(sections)

        # 2. 섹션을 chunk로 나누기
        chunk_file_path = os.path.join(CHUNK_DIR, f"{base_name}_chunks.json")
        if os.path.exists(chunk_file_path):
            print(f"[SKIP] {pdf_name} already processed (chunk file exists).")
            continue

        print(f"[CHUNKING] Processing {pdf_name}")
        chunks = chunk_sections(sections, chunk_size=CHUNK_SIZE)

        # 3. 임베딩 생성
        contents = [chunk["text"] for chunk in chunks]
        embeddings = embedding_model.get_embeddings(contents)

        # 4. 벡터와 메타데이터 저장
        pdf_vectors = []
        for i, emb in enumerate(embeddings):
            pdf_vectors.append({
                "embedding": emb.tolist(),
                "metadata": {
                    **chunks[i],
                    "source_pdf": pdf_name
                }
            })
        all_vectors.extend(pdf_vectors)

        # 5. 결과 저장
        with open(chunk_file_path, 'w', encoding='utf-8') as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        with open(os.path.join(INDEX_DIR, f"{base_name}_vectors.json"), 'w', encoding='utf-8') as f:
            json.dump(pdf_vectors, f, ensure_ascii=False, indent=2)

        print(f"[DONE] {pdf_name}: {len(chunks)} chunks, {len(contents)} embeddings")

    except Exception as e:
        print(f"[ERROR] {fname}: {str(e)}")

# 6. sections.json 저장 (통합된 섹션)
with open(os.path.join(EXTRACTED_DIR, "sections.json"), 'w', encoding='utf-8') as f:
    json.dump(all_sections, f, ensure_ascii=False, indent=2)

# 7. section_rep_builder로 coarse search용 임베딩 추가
updated_sections = build_section_reps(all_sections, all_vectors)
with open(os.path.join(EXTRACTED_DIR, "sections_with_emb.json"), 'w', encoding='utf-8') as f:
    json.dump(updated_sections, f, ensure_ascii=False, indent=2)

# 8. 전체 벡터 저장
with open(os.path.join(INDEX_DIR, "full_vectors.json"), 'w', encoding='utf-8') as f:
    json.dump(all_vectors, f, ensure_ascii=False, indent=2)

print("All extracted sections processed.")