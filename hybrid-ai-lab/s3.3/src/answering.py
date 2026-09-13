"""슬라이드 28-1: 질문 조건과 청크 메타데이터를 확인하는 답변 프롬프트."""

from __future__ import annotations

import json

from .groq_client import ask_groq
from .s32_bridge import load_s32_module


RAG_SYSTEM = """당신은 카드 상담 근거 답변 생성기입니다.
답변보다 답변 가능성 판정을 먼저 수행하십시오.
질문의 핵심 제도·혜택이 원문에 직접 없으면 관련된 다른 제도로 바꾸지 말고 확인 필요로 답하십시오.
제공된 검색 결과만 사용하고 JSON 객체 하나만 출력하십시오.
마크다운 코드 블록과 JSON 밖의 설명은 출력하지 마십시오."""


def _metadata_for_prompt(metadata: dict) -> dict:
    """질문 조건과 비교할 수 있는 메타데이터만 프롬프트에 포함함."""
    keys = (
        "chunk_id",
        "doc_type",
        "card_name",
        "member_pseudo_id",
        "channel",
        "version",
        "effective_date",
        "consult_date",
        "clause_no",
        "source",
    )
    return {
        key: metadata[key]
        for key in keys
        if metadata.get(key) not in (None, "")
    }


def build_answer_prompt(question: str, hits: list) -> str:
    """프롬프트 작성 가이드의 8개 섹션으로 답변 요청을 조립함."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("질문이 비어 있음")
    blocks = []
    for index, hit in enumerate(hits, start=1):
        metadata = json.dumps(
            _metadata_for_prompt(hit.metadata),
            ensure_ascii=False,
            sort_keys=True,
        )
        blocks.append(
            f"[검색결과 {index}]\n메타데이터: {metadata}\n본문:\n{hit.text}"
        )
    contexts = "\n\n".join(blocks) or "검색결과 없음"
    return f"""[목표]
사용자 질문에 직접 답하고, 사용한 원문 발췌를 연결한 카드 상담 답변 JSON 생성

[역할]
당신은 카드 약관·혜택·상담이력을 검토하는 10년 경력의 카드 고객상담 품질검수자입니다.

[맥락]
- 내 상황: 검색·질문 변환·Hybrid Search·Re-ranking을 거친 Top-5 청크가 제공됨
- 결과물 독자: 고객에게 답변하기 전에 근거를 검토하는 카드 상담사
- 검토 목적: 비슷한 다른 상품이나 다른 고객의 청크를 근거로 사용하는 오류 방지

[입력정보]
- 사용자 질문: {question.strip()}
- 검색 결과:
{contexts}

[작업방법]
1. 질문을 답변해야 할 주장 단위로 나누고, 각 주장에 직접 적용되는 명시 조건을 찾음
2. 명시 조건은 상품명·고객·기간·채널·버전·문서 종류를 포함함
3. 각 주장과 검색결과의 본문 및 메타데이터를 비교함
4. 질문에 명시된 조건과 메타데이터 값이 다르면 해당 주장의 근거로 사용하지 않음
5. 질문에 없는 조건은 청크 배제 기준으로 사용하지 않음
6. 일반 약관 주장은 상품명이 없어도 규정 본문이 직접 뒷받침하면 사용 가능함
7. 상품별 혜택 주장은 질문의 상품명과 `card_name`이 일치하는 검색결과만 사용함
8. 결론의 각 사실을 하나 이상의 원문 발췌와 연결함
9. 일부 주장만 확인되면 확인된 내용만 답하고 미확인 내용은 caution에 기록함
10. 질문의 핵심 개념을 관련 있어 보이는 다른 혜택·제도·조건으로 바꾸지 않음
11. 각 결론을 원문이 직접 뒷받침하는지 확인하고 단순히 관련된 내용은 근거로 사용하지 않음
12. 원문이 충분조건만 설명하면 조건을 충족하지 못한 경우의 결과를 임의로 단정하지 않음
13. 고객의 실제 이용금액·연체 여부 등 상태 자료가 없으면 적용 기준만 안내하고 결과를 확정하지 않음
14. 질문의 핵심 개념을 직접 뒷받침하는 청크가 없으면 `확인 필요`로 답함
15. 출력 직전에 각 `quote`가 지정한 `ref`의 본문에 실제로 있는지 다시 확인함
16. 원문의 핵심 명사와 수치를 결론에서도 그대로 사용하고 반대 의미나 비슷한 표현으로 바꾸지 않음
17. 하나의 evidence에는 같은 조·항 또는 같은 표 행의 짧은 연속 원문 하나만 넣음

[출력]
- 아래 스키마의 JSON 객체 하나만 출력함
{{"answerability":"answer 또는 confirm","conclusion":"질문에 직접 답하는 결론","evidence":[{{"ref":1,"quote":"한 조·항 또는 한 표 행의 연속 원문"}}],"caution":"추가 확인 사항 또는 없음"}}

[제약조건]
- MUST: `ref`는 사용한 `[검색결과 N]`의 N과 일치함
- MUST: `quote`는 해당 본문의 연속된 원문이며 글자·숫자·기호를 바꾸지 않음
- MUST: 조건이 다른 검색결과는 결론과 evidence에서 제외함
- MUST: 결론의 모든 조건·수치·판단을 하나 이상의 원문 발췌가 직접 뒷받침함
- MUST: 질문의 핵심 개념과 다른 개념의 관계를 원문에서 확인할 수 없으면 동일하게 간주하지 않음
- MUST: `유이자`·`무이자`처럼 뜻이 달라지는 핵심 단어를 원문과 한 글자씩 대조함
- MUST: 핵심 제도·혜택이 원문에 없으면 answerability를 `confirm`으로 설정함
- MUST: answerability가 `confirm`이면 conclusion은 `확인 필요`, evidence는 빈 목록으로 작성함
- MUST: 답할 근거가 전혀 없으면 conclusion을 `확인 필요`, evidence를 빈 목록으로 작성함
- MUST NOT: 이름이 비슷한 다른 상품을 같은 상품으로 간주하지 않음
- MUST NOT: 충분조건이 충족되지 않았다는 이유만으로 반대 결과를 확정하지 않음
- MUST NOT: 검색결과 밖의 상식·조건·수치·예외를 추가하지 않음
- 완료조건: JSON 해석 가능, 모든 ref가 Top-5 범위, 모든 quote가 해당 청크 원문과 일치함

[예시]
질문이 `한빛 모아생활 카드의 적립 조건은?`이고 `한빛 모아생활 플러스`와
`한빛 모아생활` 청크가 함께 있으면 `한빛 모아생활` 청크만 evidence로 사용함.

질문이 `장기 보유 고객의 유지 혜택은?`인데 검색결과에 장기 보유·유지 혜택과 연회비 면제의
관계를 직접 설명한 내용이 없으면, 연회비 면제를 유지 혜택으로 추정하지 않고 `확인 필요`로 답함.

원문이 `유이자 할부`이면 결론도 `유이자 할부`로 작성함. `무이자 할부`로 바꾸지 않음.

질문이 `조건을 충족했는지 모르겠는데 연회비를 내야 하나요?`이고 원문이 면제 조건만 설명하면,
면제 조건과 고객 상태 확인 필요성을 답함. 조건 미충족 시 반드시 납부한다고 단정하지 않음.

적립률과 한도가 서로 다른 표 행에 있으면 같은 ref를 사용한 evidence 두 개로 나누고,
각 evidence의 quote에는 표 행 하나만 복사함.
"""


def _needs_check(question: str, reason: str) -> dict:
    """LLM 호출이나 원문 검증에 실패한 안전 응답을 반환함."""
    return {
        "conclusion": "확인 필요",
        "evidence": [],
        "sources": [],
        "caution": f"{question}: {reason}",
        "verification": {
            "automatic_valid": False,
            "branch": "needs_check",
        },
    }


def _validate_response(raw: str, hits: list) -> tuple[dict | None, str]:
    """LLM 출력을 검증하고 실패 이유를 재시도용 문자열로 반환함."""
    evidence_module = load_s32_module("evidence")
    try:
        answer = evidence_module.build_evidence_answer(raw, hits)
    except ValueError as error:
        return None, str(error)
    if answer["verification"]["automatic_valid"]:
        return answer, ""
    return answer, json.dumps(
        answer["verification"],
        ensure_ascii=False,
    )


def _build_retry_prompt(prompt: str, raw: str, failure: str) -> str:
    """검증 오류만 고쳐 전체 JSON을 다시 출력하도록 요청함."""
    return f"""{prompt}

[오류 수정]
이전 출력은 자동 검증을 통과하지 못했음.
- 검증 오류: {failure}
- 이전 출력: {raw}

결론의 의미를 임의로 바꾸지 말고 다음 순서로 JSON 전체를 다시 작성함.
1. 각 quote가 해당 ref 본문에 연속된 원문으로 실제 존재하는지 확인함
2. quote가 다른 검색결과에 있으면 올바른 ref로 수정함
3. 원문 줄바꿈·글자·숫자·기호를 그대로 복사함
4. 서로 다른 조·항이나 표 행을 하나의 quote로 합치지 않음
5. 수정된 JSON 객체 하나만 출력함
"""


def _repair_hints(raw: str, hits: list) -> str:
    """발췌문마다 위치까지 검증되는 ref 후보를 찾아 재시도 힌트로 제공함."""
    evidence_module = load_s32_module("evidence")
    sources_module = load_s32_module("sources")
    try:
        value = evidence_module.parse_json_response(raw)
    except ValueError:
        return "JSON 형식부터 수정할 것"
    hints = []
    for order, item in enumerate(value.get("evidence", []), start=1):
        if not isinstance(item, dict) or not isinstance(item.get("quote"), str):
            continue
        quote = item["quote"]
        candidates = []
        for ref, hit in enumerate(hits, start=1):
            quote_ok = sources_module.quote_is_in_text(quote, hit.text)
            _, location_ok = sources_module.format_location(
                hit.metadata,
                hit.text,
                quote,
            )
            if quote_ok and location_ok:
                candidates.append(ref)
        if candidates:
            hints.append(f"evidence {order}의 검증 가능 ref 후보: {candidates}")
            continue
        line_hints = []
        for line in (part.strip() for part in quote.splitlines() if part.strip()):
            line_candidates = []
            for ref, hit in enumerate(hits, start=1):
                quote_ok = sources_module.quote_is_in_text(line, hit.text)
                _, location_ok = sources_module.format_location(
                    hit.metadata,
                    hit.text,
                    line,
                )
                if quote_ok and location_ok:
                    line_candidates.append(ref)
            if line_candidates:
                line_hints.append(f"{line[:30]!r} → ref {line_candidates}")
        if line_hints:
            hints.append(
                f"evidence {order}를 행·항별로 분리: " + "; ".join(line_hints)
            )
    return "\n".join(hints) or "각 quote를 더 짧은 한 문장 또는 한 표 행으로 다시 선택할 것"


def answer_with_condition_prompt(
    question: str,
    hits: list,
    ask_fn=ask_groq,
    return_debug: bool = False,
    max_retries: int = 1,
) -> dict | tuple[dict, dict]:
    """Top-5 청크로 답변을 생성하고 ref·원문 발췌·위치를 코드로 검증함."""
    if not hits:
        answer = _needs_check(question, "검색 근거 없음")
        return (answer, {}) if return_debug else answer
    prompt = build_answer_prompt(question, hits)
    response = ask_fn(
        RAG_SYSTEM,
        prompt,
        max_tokens=4000,
    )
    raw = response.get("content", "") if isinstance(response, dict) else str(response)
    answer, failure = _validate_response(raw, hits)
    attempts = [response]

    if failure and max_retries > 0:
        failure = f"{failure}\n{_repair_hints(raw, hits)}"
        response = ask_fn(
            RAG_SYSTEM,
            _build_retry_prompt(prompt, raw, failure),
            max_tokens=4000,
        )
        attempts.append(response)
        raw = response.get("content", "") if isinstance(response, dict) else str(response)
        answer, failure = _validate_response(raw, hits)

    if failure or answer is None:
        answer = _needs_check(question, failure or "응답 검증 실패")
    if isinstance(response, dict):
        response = {
            **response,
            "attempt_count": len(attempts),
            "attempts": attempts,
        }
    return (answer, response) if return_debug else answer
