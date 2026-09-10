"""LLM JSON을 원문 위치·발췌·출처가 있는 검증 가능 응답으로 변환함."""

import json

from .models import Hit
from .sources import format_location, format_source, quote_is_in_text, source_record


def parse_json_response(raw: str) -> dict:
    """코드 울타리 유무와 관계없이 응답의 JSON 객체 하나를 읽음."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1]).strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("LLM 응답에 JSON 객체가 없음")
    try:
        value = json.loads(text[start:end + 1])
    except json.JSONDecodeError as error:
        raise ValueError(f"LLM JSON 해석 실패: {error.msg}") from None
    if not isinstance(value, dict):
        raise ValueError("LLM 응답은 JSON 객체여야 함")
    return value


def build_evidence_answer(raw: str, hits: list[Hit]) -> dict:
    """참조 번호는 내부에서만 쓰고 화면용 위치·발췌·출처를 코드로 만듦."""
    value = parse_json_response(raw)
    conclusion = value.get("conclusion")
    caution = value.get("caution")
    raw_evidence = value.get("evidence")
    schema_errors = []
    if not isinstance(conclusion, str) or not conclusion.strip():
        schema_errors.append("conclusion 누락")
    if not isinstance(caution, str) or not caution.strip():
        schema_errors.append("caution 누락")
    if not isinstance(raw_evidence, list):
        schema_errors.append("evidence는 목록이어야 함")
        raw_evidence = []

    evidence = []
    invalid_refs = []
    quote_failures = []
    location_failures = []
    used_hits = []
    for order, item in enumerate(raw_evidence, start=1):
        if not isinstance(item, dict):
            schema_errors.append(f"evidence {order}가 객체가 아님")
            continue
        ref, quote = item.get("ref"), item.get("quote")
        if isinstance(ref, bool) or not isinstance(ref, int) or not 1 <= ref <= len(hits):
            invalid_refs.append(ref)
            continue
        if not isinstance(quote, str) or not quote.strip():
            quote_failures.append({"ref": ref, "reason": "발췌문 누락"})
            continue
        hit = hits[ref - 1]
        quote_verified = quote_is_in_text(quote, hit.text)
        location, location_verified = format_location(hit.metadata, hit.text, quote)
        if not quote_verified:
            quote_failures.append({"ref": ref, "reason": "청크의 연속 원문과 불일치"})
        if not location_verified:
            location_failures.append({"ref": ref, "reason": "원문 위치 확인 실패"})
        evidence.append({
            "location": location,
            "quote": quote.strip().strip('“”"'),
            "quote_verified": quote_verified,
            "location_verified": location_verified,
            "chunk_id": hit.metadata.get("chunk_id"),
            "source": source_record(hit.metadata),
        })
        used_hits.append(hit)

    needs_check = str(conclusion).strip() == "확인 필요"
    if not needs_check and not evidence:
        schema_errors.append("답변 결론에 원문 근거가 없음")
    if needs_check and evidence:
        schema_errors.append("확인 필요 응답에는 원문 근거를 넣지 않음")

    sources = []
    seen = set()
    for hit in used_hits:
        source = format_source(hit.metadata)
        if source not in seen:
            seen.add(source)
            sources.append(source)
    automatic_valid = not schema_errors and not invalid_refs and not quote_failures and not location_failures
    return {
        "conclusion": conclusion.strip() if isinstance(conclusion, str) else "확인 필요",
        "evidence": evidence,
        "sources": sources,
        "caution": caution.strip() if isinstance(caution, str) else "응답 구조 확인 필요",
        "verification": {
            "automatic_valid": automatic_valid,
            "schema_errors": schema_errors,
            "invalid_refs": invalid_refs,
            "quote_failures": quote_failures,
            "location_failures": location_failures,
            "verified_quote_count": sum(item["quote_verified"] for item in evidence),
            "semantic_review_required": bool(evidence),
        },
    }


def render_answer(answer: dict) -> str:
    """구조화 응답을 사람이 읽는 형식으로 표시함."""
    lines = [f"결론: {answer['conclusion']}", "", "근거:"]
    if answer["evidence"]:
        for item in answer["evidence"]:
            lines.append(f"- 원문 위치: {item['location']}")
            lines.append(f"  원문 발췌: “{item['quote']}”")
    else:
        lines.append("- 확인된 원문 없음")
    lines.extend(["", "출처:"])
    lines.extend([f"- {source}" for source in answer["sources"]] or ["- 없음"])
    lines.extend(["", f"주의사항: {answer['caution']}"])
    return "\n".join(lines)
