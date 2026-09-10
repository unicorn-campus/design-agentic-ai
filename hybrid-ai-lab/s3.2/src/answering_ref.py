"""슬라이드 18~21 강사 완성본: 검색 결과와 질문을 조립함."""

from .answering import RAG_SYSTEM, THRESHOLD, needs_check
from .evidence import build_evidence_answer
from .llm_client import ask_llm
from .models import Hit
from .sources import format_source


def build_rag_prompt(question: str, hits: list[Hit]) -> str:
    """번호 붙인 검색 결과와 질문을 user 메시지로 조립함."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("질문이 비어 있음")
    blocks = []
    for index, hit in enumerate(hits, start=1):
        source = format_source(hit.metadata)
        chunk_id = hit.metadata.get("chunk_id") or "미지정"
        blocks.append(
            f"[검색결과 {index}]\n원본 문서: {source}\n"
            f"내부 chunk_id: {chunk_id}\n본문:\n{hit.text}"
        )
    joined = "\n\n".join(blocks)
    return f"[검색결과 목록]\n{joined}\n\n[질문]\n{question.strip()}"


def answer_with_sources(question: str, hits: list[Hit], threshold: float = THRESHOLD,
                        ask_fn=ask_llm) -> dict:
    """검색 전 점수와 생성 후 원문 발췌 검사를 모두 통과한 답을 반환함."""
    if not hits or hits[0].score < threshold:
        return needs_check(question, "근거 없음 또는 유사도 미달")
    response = ask_fn(RAG_SYSTEM, build_rag_prompt(question, hits))
    raw = response.get("content", "") if isinstance(response, dict) else str(response)
    try:
        answer = build_evidence_answer(raw, hits)
    except ValueError:
        return needs_check(question, "LLM JSON 해석 실패")
    if not answer["verification"]["automatic_valid"]:
        return needs_check(question, "응답 구조·원문 발췌 검사 실패")
    return answer
