"""하이브리드 점수·답변 관문·근거 원문 대조 규칙."""

from __future__ import annotations

import re
from typing import Any, Iterable

from ..application.state import Answer, AnswerDraft, Evidence, Hit, Verification


def normalize(scores: dict[str, float], candidate_ids: Iterable[str] | None = None) -> dict[str, float]:
    ids = set(candidate_ids if candidate_ids is not None else scores)
    if not ids:
        return {}
    values = [float(scores.get(chunk_id, 0.0)) for chunk_id in ids]
    low, high = min(values), max(values)
    if high == low:
        return {chunk_id: 0.0 for chunk_id in ids}
    return {chunk_id: (float(scores.get(chunk_id, 0.0)) - low) / (high - low) for chunk_id in ids}


def rank(hits: Iterable[Hit], top_k: int) -> list[Hit]:
    if top_k <= 0:
        raise ValueError("top_k는 양수여야 함")
    return sorted(hits, key=lambda hit: (-hit.score, hit.chunk_id))[:top_k]


def fuse(
    vector_hits: list[Hit],
    bm25_scores: dict[str, float],
    chunks: dict[str, Hit],
    *,
    weight_bm25: float,
    weight_vector: float,
    top_k: int | None = None,
) -> list[Hit]:
    """기존 최소-최대 정규화 가중합을 재현하며 vector_score를 보존함."""

    if weight_bm25 < 0 or weight_vector < 0 or weight_bm25 + weight_vector <= 0:
        raise ValueError("검색 가중치는 0 이상이고 합은 양수여야 함")
    vector_by_id = {hit.chunk_id: float(hit.vector_score if hit.vector_score is not None else hit.score) for hit in vector_hits}
    # 기존 Hybrid Search와 같이 벡터 후보 수만큼의 BM25 상위 후보만
    # 후보 집합에 넣음. 전체 색인을 정규화 대상으로 삼으면 무관한 0점
    # 문서가 최솟값을 고정하여 기준선 점수와 순위를 바꿈.
    bm25_candidate_count = len(vector_hits) or (top_k or len(bm25_scores))
    bm25_candidate_ids = {
        chunk_id
        for chunk_id, _score in sorted(
            bm25_scores.items(),
            key=lambda item: (-float(item[1]), item[0]),
        )[:bm25_candidate_count]
    }
    candidate_ids = set(vector_by_id) | bm25_candidate_ids
    normalized_vector = normalize(vector_by_id, candidate_ids)
    normalized_bm25 = normalize(bm25_scores, candidate_ids)
    vector_objects = {hit.chunk_id: hit for hit in vector_hits}
    output = []
    for chunk_id in candidate_ids:
        base = vector_objects.get(chunk_id) or chunks.get(chunk_id)
        if base is None:
            continue
        score = weight_bm25 * normalized_bm25[chunk_id] + weight_vector * normalized_vector[chunk_id]
        output.append(base.model_copy(update={
            "score": round(score, 6),
            "vector_score": vector_by_id.get(chunk_id),
            "rerank_score": None,
        }))
    ranked = sorted(output, key=lambda hit: (-hit.score, hit.chunk_id))
    return ranked if top_k is None else ranked[:top_k]


def apply_rerank(hits: list[Hit], scores: list[float], top_k: int) -> list[Hit]:
    if len(hits) != len(scores):
        raise ValueError("후보와 리랭킹 점수 개수 불일치")
    updated = [hit.model_copy(update={"rerank_score": float(score)}) for hit, score in zip(hits, scores)]
    return sorted(updated, key=lambda hit: (-float(hit.rerank_score), -hit.score, hit.chunk_id))[:top_k]


def passes_gate(hits: list[Hit], threshold: float) -> bool:
    """최종 1위의 원 벡터 점수만 사용함. BM25 전용 후보는 통과하지 못함."""

    if not 0 <= threshold <= 1:
        raise ValueError("threshold는 0과 1 사이여야 함")
    return bool(hits and hits[0].vector_score is not None and hits[0].vector_score >= threshold)


def gate_score(hits: list[Hit]) -> float | None:
    return hits[0].vector_score if hits else None


def _normalize_quote(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().strip('“”\"')).strip()


def verify_quote(quote: str, text: str) -> bool:
    """따옴표와 줄바꿈 차이만 정규화하고 연속 원문 포함 여부를 확인함."""

    normalized = _normalize_quote(quote)
    return bool(normalized and normalized in _normalize_quote(text))


def _source_record(metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        key: metadata[key]
        for key in ("source", "page", "page_end", "record_id", "consult_date", "channel")
        if key in metadata
    }


def build_answer(raw: AnswerDraft | dict[str, Any], hits: list[Hit]) -> Answer:
    """LLM 참조 번호를 검증 가능한 위치·인용·출처로 변환함."""

    if isinstance(raw, AnswerDraft):
        value = raw.model_dump()
    elif isinstance(raw, dict):
        value = raw
    else:
        raise ValueError("답변 초안 형식이 올바르지 않음")
    schema_errors, invalid_refs, quote_failures, location_failures = [], [], [], []
    evidence: list[Evidence] = []
    used_sources: list[str] = []
    for item in value.get("evidence", []):
        ref, quote = item.get("ref"), item.get("quote")
        if isinstance(ref, bool) or not isinstance(ref, int) or not 1 <= ref <= len(hits):
            invalid_refs.append(ref)
            continue
        hit = hits[ref - 1]
        quote_ok = isinstance(quote, str) and verify_quote(quote, hit.text)
        location_ok = bool(hit.location)
        if not quote_ok:
            quote_failures.append({"ref": ref, "reason": "청크의 연속 원문과 불일치"})
        if not location_ok:
            location_failures.append({"ref": ref, "reason": "원문 위치 확인 실패"})
        evidence.append(Evidence(
            location=hit.location,
            quote=_normalize_quote(quote) if isinstance(quote, str) else "",
            quote_verified=quote_ok,
            location_verified=location_ok,
            chunk_id=hit.chunk_id,
            source=_source_record(hit.metadata),
        ))
        if hit.source not in used_sources:
            used_sources.append(hit.source)
    conclusion = value.get("conclusion")
    caution = value.get("caution")
    if not isinstance(conclusion, str) or not conclusion.strip():
        schema_errors.append("conclusion 누락")
        conclusion = "확인 필요"
    if not isinstance(caution, str) or not caution.strip():
        schema_errors.append("caution 누락")
        caution = "응답 구조 확인 필요"
    if conclusion.strip() != "확인 필요" and not evidence:
        schema_errors.append("답변 결론에 원문 근거가 없음")
    automatic_valid = not (schema_errors or invalid_refs or quote_failures or location_failures)
    verification = Verification(
        automatic_valid=automatic_valid,
        schema_errors=schema_errors,
        invalid_refs=invalid_refs,
        quote_failures=quote_failures,
        location_failures=location_failures,
        verified_quote_count=sum(item.quote_verified for item in evidence),
        semantic_review_required=bool(evidence),
    )
    return Answer(
        conclusion=conclusion.strip(),
        caution=caution.strip(),
        evidence=evidence,
        sources=used_sources,
        verification=verification,
    )
