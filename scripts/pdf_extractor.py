# scripts/pdf_extractor.py

import os
import json
import fitz  # PyMuPDF
from typing import Dict, Any, List
import pdfplumber
import requests
import tempfile
from pathlib import Path
import time

UPSTAGE_API_KEY = "up_kJSwCp4N44ppYR0gxDKaLNsMFNVDn"

UPSTAGE_OCR_URL = "https://api.upstage.ai/v1/document-digitization"

def build_sections_from_toc(toc: List[List], total_pages: int) -> List[Dict[str, Any]]:
    sections = []
    for i, entry in enumerate(toc):
        level, title, start_page = entry
        if i < len(toc) - 1:
            next_start = toc[i + 1][2]
            end_page = next_start - 1
        else:
            end_page = total_pages
        sections.append({
            "title": title,
            "start_page": start_page,
            "end_page": end_page,
            "method": "TOC"
        })
    return sections

def build_sections_from_layout(pdf_path: str, font_size_threshold: float = 14.0) -> List[Dict[str, Any]]:
    candidate_headings = []
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        for page in pdf.pages:
            words = page.extract_words(extra_attrs=["size", "fontname"])
            for word in words:
                size = word.get("size", 0)
                text = word.get("text", "")
                if size >= font_size_threshold and any(kw.lower() in text.lower() for kw in ["chapter", "section", "part", "장", "절"]):
                    candidate_headings.append({
                        "page": page.page_number,
                        "text": text,
                        "font_size": size
                    })
        candidate_headings.sort(key=lambda x: x["page"])

    sections = []
    if candidate_headings:
        for i, heading in enumerate(candidate_headings):
            start_page = heading["page"]
            end_page = candidate_headings[i + 1]["page"] - 1 if i < len(candidate_headings) - 1 else total_pages
            sections.append({
                "title": heading["text"],
                "start_page": start_page,
                "end_page": end_page,
                "method": "Layout"
            })
    return sections

def extract_text_with_ocr(pdf_path: str, page_num: int, doc: fitz.Document, cache_path: str) -> str:
    cache_file = os.path.join(cache_path, f"{Path(pdf_path).stem}_page_{page_num}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r', encoding='utf-8') as f:
            cached_data = json.load(f)
            return cached_data.get("text", "")

    max_retries = 3
    retry_delay = 5

    for attempt in range(max_retries):
        try:
            page = doc[page_num]
            pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_file:
                tmp_file.write(pix.tobytes("png"))
                tmp_file_path = tmp_file.name

            headers = {"Authorization": f"Bearer {UPSTAGE_API_KEY}"}
            with open(tmp_file_path, "rb") as f:
                files = {"document": f}
                data = {"model": "ocr"}
                response = requests.post(UPSTAGE_OCR_URL, headers=headers, files=files, data=data)

            os.unlink(tmp_file_path)

            if response.status_code == 200:
                result = response.json()
                extracted_text = result.get("text", "")
                if extracted_text:
                    os.makedirs(cache_path, exist_ok=True)
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        json.dump({"text": extracted_text}, f, ensure_ascii=False, indent=2)
                    return extracted_text
                return "No text extracted via OCR."

            elif response.status_code == 429:
                wait_time = retry_delay * (2 ** attempt)
                print(f"[RETRY] Rate limit on page {page_num + 1}. Waiting {wait_time}s...")
                time.sleep(wait_time)

            elif response.status_code == 401:
                error_json = response.json()
                error_msg = error_json.get("error", {}).get("message", "")
                print(f"[ERROR] OCR API failed on page {page_num + 1}: {response.status_code} - {error_msg}")
                
                if "suspended" in error_msg.lower() or "insufficient credit" in error_msg.lower():
                    print("[FATAL] API key is suspended or has insufficient credit. Halting execution.")
                    sys.exit(1)  # 프로그램 강제 종료
                break  # 다른 이유의 401이면 그냥 break
            else:
                print(f"[ERROR] OCR API failed on page {page_num + 1}: {response.status_code} - {response.text}")
                break

        except Exception as e:
            print(f"[ERROR] Exception on page {page_num + 1}: {str(e)}")
            break

    return ""

def extract_pdf_content(pdf_path: str) -> Dict[str, Any]:
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    cache_path = os.path.join("data", "cache")
    os.makedirs(cache_path, exist_ok=True)

    toc = doc.get_toc(simple=True)
    sections = build_sections_from_toc(toc, total_pages) if toc else build_sections_from_layout(pdf_path)
    if not sections:
        sections = [{"title": f"Page {i+1}", "start_page": i+1, "end_page": i+1, "method": "Page-based"} for i in range(total_pages)]

    enriched_sections = []
    for section in sections:
        start = section["start_page"] - 1
        end = section["end_page"]
        section_texts = []

        for i in range(start, end):
            text = doc[i].get_text("text").strip()
            if text:
                section_texts.append(text)
                print(f"[TEXT] Page {i+1}: Used PyMuPDF")
            else:
                ocr_text = extract_text_with_ocr(pdf_path, i, doc, cache_path)
                section_texts.append(ocr_text)
                print(f"[OCR ] Page {i+1}: Used OCR")

        full_text = "\n".join(section_texts)
        enriched_sections.append({
            "section": section["title"],
            "start_page": section["start_page"],
            "end_page": section["end_page"],
            "text": full_text,
            "source": section["method"]
        })

    doc.close()
    return {
        "file_path": pdf_path,
        "sections": enriched_sections
    }



if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_extractor.py <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    result = extract_pdf_content(pdf_path)

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join("data", "extracted", f"{base_name}.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"[DONE] Extracted content saved to: {output_path}")
