import os
import sys
import json

# 상위 폴더 경로 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

EXTRACTED_DIR = "data/extracted"
keyword = "rural development administration"

matching_files = []

# 디렉토리 내 모든 파일 순회
for filename in os.listdir(EXTRACTED_DIR):
    if filename.endswith('.json'):
        file_path = os.path.join(EXTRACTED_DIR, filename)
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                sections = data.get("sections", [])
                # 각 section의 text 필드 검사
                for section in sections:
                    text = section.get("text", "").lower()
                    if keyword in text:
                        matching_files.append(file_path)
                        break  # 하나라도 찾으면 더 안 봐도 됨
        except Exception as e:
            print(f"⚠️ Failed to read or parse {filename}: {e}")

# 결과 출력 및 삭제
if matching_files:
    print("✅ Keyword found in these files (will be deleted):")
    for file_path in matching_files:
        print(f"- {file_path}")
        try:
            os.remove(file_path)
            print(f"🗑️ Deleted: {file_path}")
        except Exception as e:
            print(f"❌ Failed to delete {file_path}: {e}")
else:
    print("❌ No files contain the keyword in sections' text fields.")
