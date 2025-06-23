# 📚 RAG (Retrieval-Augmented Generation)

본 모듈은 농촌진흥청 농업과학도서관의 귀농 관련 문서를 기반으로, 질의응답 시스템에서 정확하고 풍부한 정보를 제공하기 위한 RAG(Retrieval-Augmented Generation) 파이프라인을 구성합니다.  
한국어에 특화된 문서 임베딩, 효율적인 섹션 기반 검색, 그리고 LLM과의 통합 응답 생성을 통해 귀농 청년들에게 실질적인 도움을 주는 답변을 제공합니다.

---

## ✅ 주요 특징

- **한국어 특화 문장 임베딩 모델 사용**  
  - Ko-SRoBERTa: 멀티태스크 학습 기반의 Sentence-BERT 구조로 한국어 문장 간 의미 유사도 표현에 최적화됨.
- **PDF + OCR 기반 문서 수집 및 전처리**
  - PyPDF + Upstage OCR을 통해 500개 이상의 귀농 관련 문서에서 텍스트 추출.
- **2단계 Retrieval 구조 (Section-Level → Chunk-Level)**
  - Section 단위 coarse retrieval 후, Chunk 단위 fine retrieval 수행.
- **LLM과 통합된 프롬프트 기반 응답 생성**
  - 시스템 프롬프트를 통한 역할 부여 및 질의 컨텍스트 반영.

---

## 📦 디렉토리 구조

```

📂 rag/
├─ 📄 **init**.py
├─ 📄 embedding\_model.py       # Ko-SRoBERTa 기반 임베딩 생성
├─ 📄 fine\_search.py           # Chunk-level 유사도 검색 (Top-K)
├─ 📄 setup.py                 # 문서 전처리 및 인덱스 구성
├─ 📄 section\_coarse\_search.py # Section-level 평균 벡터 검색

````

---

## 🧪 데이터 구성 및 임베딩

### 📑 원본 문서
- 출처: [농업과학도서관 귀농귀촌 자료](https://lib.rda.go.kr)
- 수량: 총 500개 PDF
- 수집 방식:
  - PyPlumber로 텍스트 추출
  - OCR 누락 보완용으로 Upstage OCR API 사용

### 🤖 임베딩 모델
- 모델명: `Ko-SRoBERTa`
- 구조: Sentence-BERT 기반
- 특징: 한국어 문장 간 의미 유사도에 강건, 한국어 QA 성능 우수
- 사용처:
  - 질의(Query)
  - Section 제목 및 평균 임베딩
  - Chunk (500자 단위 문단)

---

## 🔍 RAG 검색 파이프라인

### 📘 단계 1: Section-Level 검색
- 각 Section(목차 단위)의 제목과 그 내부 텍스트 전체의 임베딩 평균값을 사전 계산 및 저장
- 사용자 질의를 임베딩한 후, cosine similarity 기반으로 Section 평균 벡터들과 비교
- 관련도가 가장 높은 Section 3개 추출

### 📗 단계 2: Chunk-Level 검색
- 선택된 Section 내부의 500자 단위 문단(Chunk)들을 대상
- Query와 모든 Chunk 간 유사도 계산
- 최종적으로 관련도 높은 Top-5 Chunk를 추출

### 📘 단계 3: 응답 생성
- 선택된 Top-5 Chunk를 LLM(ChatGPT-4o-mini)에 입력
- 사전 정의된 System Prompt와 함께 사용자 질의에 대한 완성도 높은 응답 생성

---

## 🧾 시스템 프롬프트 (LLM 응답 품질 제어)

```txt
당신은 귀농청년들의 성공적인 정착을 돕는 농업 전문가 '유귀농'입니다. 복잡한 농업 지식을 쉽고 실용적으로 전달하는 것이 특기입니다.

## 답변 원칙 ##
1. 시작을 "{state['disease'] if state['disease'] else ''}"로 하여, 사용자가 질문한 질병명이 있다면, 자연스럽게 문두에 포함시켜 정보를 전달하세요.
2. 제공된 문서 내용을 주요 근거로 활용하여 사용자 질문에 대해 답해주되, 질병과 관련이 없는 내용은 제외하세요.
3. 제공된 문서만으로 충분한 답변이 어려울 경우 당신의 전문적 지식을 바탕으로 보완 설명해주세요.
4. 반드시 완전한 응답을 생성해야합니다. 어떤 상황에서도 중간에 잘리거나 미완성된 응답을 제공하지 마세요.
5. 응답 분량을 미리 계획하여 마무리까지 온전히 표현될 수 있도록 하세요. 깊이 있고 집약적인 내용을 제공하되, 전체적으로 응답이 완성될 수 있게 균형을 맞추세요.
6. 생성한 응답을 사용자에게 답변하기 전에 검토하여 잘못된 정보가 포함되지 않도록 하세요. 특히 농업 관련 정보는 정확해야 합니다.

## 답변 스타일 ##
- 농업 전문용어는 유지하되, 필요한 경우 쉽게 풀어서 설명하세요.
- 구체적인 수치와 실례 제시하세요.
````

---

## 💡 사용 예시

```python
from rag.embedding_model import embed_text
from rag.fine_search import get_topk_chunks
from llm.agents import generate_response

query = "고추에 탄저병이 생겼을 때 방제 방법이 궁금해요"
query_vec = embed_text(query)

section_candidates = get_top3_sections(query_vec)
chunks = get_topk_chunks(section_candidates, query_vec, top_k=5)

response = generate_response(query, chunks)
print(response)
```

---

## ☁️ 배포 및 통합

* 본 모듈은 FastAPI 기반 서버(`u-guinong-backend`)에서 통합 제공됩니다.
* LLM 파이프라인 내에서 자동으로 호출되며, LangGraph 기반 워크플로우 내의 **RAG 분기 노드**로 통합됩니다.

---

## 📊 향후 확장 가능성

* 농업 관련 추가 문서 확보 시 인덱스 갱신 및 증설 가능
* OCR 성능 향상을 통한 PDF 처리 정확도 향상
* Multi-modal RAG (이미지+문서 기반 QA) 확장 고려

