"""근거 글자 대조에 쓰는 정규화 규칙(리트리버 코드 채점과 같은 기준)."""

from __future__ import annotations

import re
import unicodedata

# 숫자 덩어리: 3,000,000 · 1.2 · 12 처럼 쉼표 · 소수점을 품은 숫자
_NUMBER = re.compile(r"\d[\d,.]*\d|\d")


def normalize(text: str) -> str:
    """유니코드 표기와 공백 차이가 근거 판정을 흐리지 않도록 NFKC 정규화 후 공백을 모두 지움.

    리트리버 코드 채점과 같은 규칙이어야 검증을 통과한 평가셋이 채점에서도 같은 판정을 받음.
    """

    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(text)))


def numbers_in(text: str) -> list[str]:
    """글 속 숫자를 쉼표를 뺀 꼴로 뽑음.

    예시: "3,000,000원 · 1.2%" → ["3000000", "1.2"]. 문장 끝 마침표는 숫자에 붙지 않게 떼어 냄.
    """

    found = []
    for token in _NUMBER.findall(unicodedata.normalize("NFKC", str(text))):
        found.append(token.rstrip(".,").replace(",", ""))
    return found
