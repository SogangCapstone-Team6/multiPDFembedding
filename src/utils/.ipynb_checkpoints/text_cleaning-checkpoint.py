import re

def basic_clean_text(text: str) -> str:
    """
    - 탭, 줄바꿈을 공백으로 대체
    - 여러 연속 공백 -> 1개 공백
    - 앞뒤 공백 제거
    예시로 간단히 작성
    """
    # 탭, 줄바꿈을 공백으로
    text = text.replace('\t', ' ').replace('\n', ' ')

    # 여러 공백 -> 단일 공백
    text = re.sub(r'\s+', ' ', text)

    return text.strip()