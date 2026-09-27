"""슬라이드 21 질문 변환 완성 예시."""

from collections.abc import Callable
import re

from .query_transform import PROMPTS, SYSTEM_PROMPT
from .s32_bridge import ask_llm


def _response_text(response) -> str:
    """S3.2 dict 응답과 일반 문자열·객체 응답을 모두 문자열로 변환함."""
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return str(response.get("content") or response.get("text") or "")
    return str(getattr(response, "text", "") or "")


def _clean_lines(text: str) -> list[str]:
    """모델이 붙인 글머리 번호를 제거하고 비어 있지 않은 줄만 남김."""
    lines = []
    for raw in text.splitlines():
        value = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw).strip()
        if value and value not in lines:
            lines.append(value)
    return lines


def transform_query(
    query: str,
    mode: str = "rewrite",
    ask_fn: Callable = ask_llm,
) -> list[str]:
    """LLM을 한 번 호출해 검색용 질의를 만들고 실패 시 원 질문을 유지함."""
    if mode not in PROMPTS:
        raise ValueError(f"지원하지 않는 변환 방식: {mode}")
    if not isinstance(query, str) or not query.strip():
        raise ValueError("질문이 비어 있음")
    original = query.strip()

    try:
        response = ask_fn(SYSTEM_PROMPT, PROMPTS[mode].format(q=original))
        lines = _clean_lines(_response_text(response))
    except (ValueError, RuntimeError, TypeError, KeyError):
        return [original]

    if not lines:
        return [original]
    if mode == "multi":
        return lines[:3]
    if mode == "hyde":
        return [" ".join(lines[:2])]
    if mode == "stepback":
        return [lines[0], original] if lines[0] != original else [original]
    return [lines[0]]
