"""하이브리드 점수·답변 관문·근거 원문 대조 규칙."""

from __future__ import annotations

import re
from typing import Any, Iterable

from ..application.state import Answer, AnswerDraft, Evidence, Hit, Verification


# 목적: 후보별 점수를 서로 비교하기 쉽도록 최솟값 0.0, 최댓값 1.0 범위에 맞춤.
# 공식: 정규화 점수 = (현재 점수 - 최솟값) / (최댓값 - 최솟값).
# 예: A=2, B=5, C=8이면 A=(2-2)/(8-2)=0.0, B=(5-2)/(8-2)=0.5, C=(8-2)/(8-2)=1.0.
# candidate_ids에는 있지만 scores에 없는 ID는 원래 점수를 0.0으로 보며, 모든 값이 같으면 결과를 모두 0.0으로 만듦.
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

    # 벡터 검색 결과의 id별 유사도 점수 구하기
    vector_by_id = {hit.chunk_id: float(hit.vector_score if hit.vector_score is not None else hit.score) for hit in vector_hits}

    # 후보 수는 최댓값을 고르지 않음. Python의 or가 왼쪽부터 처음 만나는 0이 아닌 값을 선택하므로,
    # vector_hits가 있으면 그 개수, 없으면 top_k, 그것도 없거나 0이면 BM25 점수 전체 개수를 사용함.
    bm25_candidate_count = len(vector_hits) or (top_k or len(bm25_scores))

    # 선택한 개수만큼의 BM25 상위 후보만 후보 집합에 점수가 높은순으로 정렬하여 넣음
    bm25_candidate_ids = {
        chunk_id
        for chunk_id, _score in sorted(
            bm25_scores.items(),  # 첫 번째 인자: 정렬할 대상인 (chunk_id, 점수) 쌍
            key=lambda item: (-float(item[1]), item[0]),  # key 인자: 정렬에 사용할 점수 내림차순·동점 ID 오름차순 기준
        )[:bm25_candidate_count]
    }

    # 예: vector_by_id={"chunk-A": 0.9, "chunk-B": 0.8}는 벡터 결과의 ID별 점수임.
    # set(vector_by_id)={"chunk-A", "chunk-B"}처럼 딕셔너리의 key인 chunk_id만 집합으로 만듦.
    # bm25_candidate_ids={"chunk-B", "chunk-C"}라면 |로 두 집합의 모든 ID를 합침.
    # 결과 candidate_ids={"chunk-A", "chunk-B", "chunk-C"}이며, 양쪽의 chunk-B는 한 번만 남고 표시 순서는 정해지지 않음.
    candidate_ids = set(vector_by_id) | bm25_candidate_ids

    normalized_vector = normalize(vector_by_id, candidate_ids)  # vector 검색 결과 점수를 0~1 사이로 정규화
    normalized_bm25 = normalize(bm25_scores, candidate_ids)     # bm25 검색 결과 점수를 0~1 사이로 정규화

    vector_objects = {hit.chunk_id: hit for hit in vector_hits}
    output = []


    for chunk_id in candidate_ids:
        base = vector_objects.get(chunk_id) or chunks.get(chunk_id)
        if base is None:
            continue

        score = weight_bm25 * normalized_bm25[chunk_id] + weight_vector * normalized_vector[chunk_id]
        # 목적: 기존 검색 결과의 나머지 정보는 유지하면서 융합 점수를 반영한 새 후보를 만듦.
        # 작업: score와 vector_score를 새 값으로 교체하고 rerank_score를 비운 복사본을 output에 추가함.
        output.append(
            base.model_copy(  # 원본 base를 바꾸지 않고 update에 지정한 필드만 교체한 복사본 생성
                update={
                    "score": round(score, 6),
                    "vector_score": vector_by_id.get(chunk_id),
                    "rerank_score": None,
                }
            )
        )

    # 점수순으로 정렬 
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


def top_vector_score(hits: list[Hit]) -> float | None:
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
    """
    LLM 응답을 검증 가능한 위치·인용·출처로 변환함.
    - AnserDraft 구조: { conclusion: str, caution: str, evidence: list[EvidenceDraft] }
    - EvidenceDraft 구조: { ref: int, quote: str }
    """

    if isinstance(raw, AnswerDraft):
        value = raw.model_dump()  # Pydantic AnswerDraft 객체의 필드와 값을 일반 Python 딕셔너리로 변환함
    elif isinstance(raw, dict):
        value = raw
    else:
        raise ValueError("답변 초안 형식이 올바르지 않음")
    
    schema_errors, invalid_refs, quote_failures, location_failures = [], [], [], []
    evidence: list[Evidence] = []
    used_sources: list[str] = []
    for evidence_index, item in enumerate(value.get("evidence", []), start=1):
        ref, quote = item.get("ref"), item.get("quote")
        if isinstance(ref, bool) or not isinstance(ref, int) or not 1 <= ref <= len(hits):
            invalid_refs.append({
                "code": "INVALID_REF",
                "evidence_index": evidence_index,
                "ref": ref,
                "valid_ref_range": f"1~{len(hits)}" if hits else "검색결과 없음",
                "repair_hint": (
                    f"[INVALID_REF] evidence[{evidence_index}].ref={ref!r}가 유효 범위를 벗어남. "
                    f"<검색결과목록>의 순번 {f'1~{len(hits)}' if hits else '없음'} 중에서 "
                    "근거를 다시 선택함."
                ),
            })
            continue
        
        # LLM 응답이 검색 결과에 기반하였는지 체크    
        hit = hits[ref - 1]     # LLM에서 참조하고 있는 검색결과 객체 
        quote_ok = isinstance(quote, str) and verify_quote(quote, hit.text) # LLM응답의 인용이 검색 결과 텍스트내 존재 
        location_ok = bool(hit.location)
        if not quote_ok:
            submitted_quote = _normalize_quote(quote) if isinstance(quote, str) else ""
            quote_failures.append({
                "code": "QUOTE_NOT_FOUND",
                "evidence_index": evidence_index,
                "ref": ref,
                "chunk_id": hit.chunk_id,
                "submitted_quote": submitted_quote,
                "reason": "제출한 인용문이 참조 청크 본문에 연속해서 존재하지 않음",
                "repair_hint": (
                    f"[QUOTE_NOT_FOUND] evidence[{evidence_index}], ref={ref}, "
                    f"chunk_id={hit.chunk_id}: 제출 quote={submitted_quote!r}가 해당 청크의 "
                    "<본문>에 연속해서 존재하지 않음. 같은 본문에서 연속된 원문을 그대로 "
                    "인용하거나 다른 ref를 선택함."
                ),
            })
        if not location_ok:
            location_failures.append({
                "code": "LOCATION_MISSING",
                "evidence_index": evidence_index,
                "ref": ref,
                "chunk_id": hit.chunk_id,
                "reason": "참조 청크에 원문 위치 정보가 없음",
                "repair_hint": (
                    f"[LOCATION_MISSING] evidence[{evidence_index}], ref={ref}, "
                    f"chunk_id={hit.chunk_id}: 해당 검색결과의 <위치>가 비어 있음. "
                    "동일한 주장을 뒷받침하면서 위치가 있는 다른 ref를 선택함."
                ),
            })
        
        # 출처 객체 생성     
        evidence.append(Evidence(
            location=hit.location,  # 인용 원문을 다시 찾을 수 있는 조항·페이지 또는 상담 ID·턴 범위
            quote=_normalize_quote(quote) if isinstance(quote, str) else "",  # 공백을 정규화한 LLM 인용문
            quote_verified=quote_ok,  # 인용문이 해당 검색 청크에 연속된 원문으로 존재하는지 여부
            location_verified=location_ok,  # 검색 결과에 원문 위치 정보가 존재하는지 여부
            chunk_id=hit.chunk_id,  # 인용 근거로 사용한 검색 청크의 고유 ID
            source=_source_record(hit.metadata),  # metadata: 문서 출처·페이지·상담 식별 정보를 정리한 딕셔너리
        ))
        
        if hit.source not in used_sources:
            used_sources.append(hit.source)
    
    # 결론, 주의사항 구함         
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
        
    # 에러 정보 생성
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
