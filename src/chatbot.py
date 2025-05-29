# src/chatbot.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import json
from src.inference.embedding_model import embedding_model
from src.inference.llm_model import get_local_llm
from src.search.section_coarse_search import coarse_search_sections
from src.search.fine_search import fine_search_chunks

SECTIONS_PATH = "data/extracted/sections_with_emb.json"
CHUNK_INDEX_PATH = "data/index/full_vectors.json"
TOP_K_SECTIONS = 10
TOP_K_CHUNKS = 5

def build_prompt(query, relevant_chunks):
    context = "\n\n".join([
        f"[출처: {c['metadata']['source_pdf']}, section: {c['metadata']['section']}] {c['metadata']['text']}"
        for c in relevant_chunks
    ])
    prompt = (
        f"사용자의 질문:\n{query}\n\n"
        f"다음은 참고할 수 있는 문서 정보입니다:\n{context}\n\n"
        f"이 문서를 참고하여 질문에 대해 한국어로 정성스럽고 신뢰성 있게 답변해주세요.\n"
        f"답변 마지막에 어떤 문서를 참고했는지도 요약해서 알려주세요.\n"
        f"답변:"
    )
    return prompt

def answer_query(query: str, streaming=False):
    # 1. query embedding
    query_emb = embedding_model.get_embedding(query)

    # 2. 섹션 불러오기
    with open(SECTIONS_PATH, "r", encoding="utf-8") as f:
        section_data = json.load(f)

    # 3. coarse search
    
    top_sections = coarse_search_sections(query, section_data, top_k=TOP_K_SECTIONS)
    print("=== Top Sections ===")
    for sec in top_sections:
        print(f"Section: {sec['section']}, Start Page: {sec['start_page']}, End Page: {sec['end_page']}")

    # 4. chunk index 로드
    with open(CHUNK_INDEX_PATH, "r", encoding="utf-8") as f:
        chunk_index = json.load(f)

    # 5. fine search
    
    top_chunks = fine_search_chunks(query_emb, chunk_index, target_sections=top_sections, top_k=TOP_K_CHUNKS)
    print("\n=== Top Chunks ===")
    for chunk in top_chunks:
        meta = chunk["metadata"]
        print(f"Section: {meta['section']}, Text: {meta['text'][:200]}... (총 길이: {len(meta['text'])}자)")
        
    # 6. 프롬프트 구성
    prompt = build_prompt(query, top_chunks)

    # 7. LLM 응답
    local_llm = get_local_llm()
    response = local_llm.generate(prompt, streaming=streaming)
    return response

if __name__ == "__main__":
    query = input("질문을 입력하세요: ")
    print("\nChatbot 답변:\n")
    response = answer_query(query, streaming=False)
    print(response)
