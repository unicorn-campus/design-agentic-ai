"""슬라이드 18~22 조별 구현: 검색 결과를 조립하고 안전한 답변을 만듦."""

from .evidence import build_evidence_answer
from .llm_client import ask_llm
from .models import Hit
from .sources import format_source


RAG_SYSTEM = """당신은 카드 상담 답변 도우미입니다.
검색 결과에 있는 내용만 사용하고 JSON 객체 하나만 출력하세요. 마크다운 코드 울타리는 쓰지 마세요.
스키마는 다음과 같습니다.
{"conclusion":"질문에 직접 답하는 결론","evidence":[{"ref":1,"quote":"연속된 원문 발췌"}],
 "caution":"추가 확인 사항 또는 없음"}
규칙:
1. conclusion은 질문이 묻는 조건·금액·기한 등을 빠뜨리지 않고 직접 답하세요.
2. evidence의 ref는 사용한 [검색결과 N]의 N입니다.
3. quote는 해당 검색결과 본문의 연속된 원문을 사용하세요. quote 문자열에는 줄바꿈을 넣지 마세요.
   PDF 줄바꿈은 자연스러운 띄어쓰기로 복원하되 글자·숫자·기호를 바꾸거나 요약하지 마세요.
4. 서로 다른 조·항이나 문단을 사용하면 evidence 원소를 각각 나누세요.
5. conclusion이나 caution에 쓴 원문 기반 사실은 하나 이상의 evidence로 뒷받침하세요.
6. 조건을 묻는 질문이면 검색 결과에 있는 충족 조건, 실적 제외, 적용 절차와 예외를 conclusion에
   포함하고, 서로 다른 문단은 각각 evidence로 제시하세요.
7. 검색 결과로 답할 수 없으면 conclusion을 '확인 필요', evidence를 빈 목록으로 작성하세요."""

THRESHOLD = 0.62


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


def needs_check(question: str, reason: str) -> dict:
    """검색 근거가 부족하거나 응답 검증이 실패한 결과를 만듦."""
    return {
        "conclusion": "확인 필요",
        "evidence": [],
        "sources": [],
        "caution": f"{question}: {reason}",
        "verification": {"automatic_valid": True, "branch": "needs_check"},
    }


def answer_with_sources(question: str, hits: list[Hit], threshold: float = THRESHOLD,
                        ask_fn=ask_llm) -> dict:
    """검색 전 점수와 생성 후 원문 발췌 검사를 통과한 답을 반환함."""
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
