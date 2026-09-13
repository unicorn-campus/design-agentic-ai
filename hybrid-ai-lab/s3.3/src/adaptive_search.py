"""Top-1 관문, 단일 질문 변환, 가중 RRF를 연결한 적응형 검색."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
import re

from .s32_bridge import ask_llm


TECHNIQUES = {"rewrite", "multi", "hyde", "stepback", "decomposition"}

ROUTER_SYSTEM_PROMPT = """당신은 한국어 카드 상담 문서 검색용 질의 라우터입니다.
원 질문의 상품명, 기간, 금액, 수치, 조건, 의도를 빠뜨리거나 새 사실을 만들지 마십시오.
변환한다면 반드시 한 가지 기법만 선택하고 JSON 객체만 출력하십시오."""

ROUTER_USER_PROMPT = """아래 원 질문의 검색 결과가 부족합니다.
질문을 확인할지, 원 결과를 유지할지, 한 기법으로 변환할지 결정하십시오.

행동 기준:
- clarify: '그 카드·그거'처럼 핵심 대상을 문맥에서 복원할 수 없어 사용자 답이 꼭 필요함
- keep: 질문이 문서 용어로 명확하고 하나의 답만 요구하여 변환 이득이 없음
- transform: 질문 유형에 맞는 기법 하나를 선택해 추가 검색 질의를 생성

선택 기준:
- rewrite: 구어체·모호한 표현을 문서 용어가 포함된 한 문장으로 정리
- multi: 하나의 검색 의도를 서로 다른 표현으로 바꾼 질의 3개 생성
- hyde: 원문에 있을 법한 짧은 답변형 문단 1개 생성. 모르는 숫자는 만들지 않음
- stepback: 세부 질문을 관련 정책·원칙을 묻는 상위 질문 1개로 일반화
- decomposition: 서로 다른 답을 요구하는 대상이 둘 이상이면 답의 대상별 하위 질문 생성

출력 형식:
{{"action":"clarify|keep|transform","technique":"기법 또는 null","queries":[],"reason":"선택 이유","clarification":"확인 질문 또는 빈 문자열"}}

규칙:
- clarify이면 technique은 null, queries는 빈 목록, clarification은 사용자에게 물을 한 문장
- keep이면 technique은 null이고 queries는 빈 목록
- transform이면 technique을 정확히 하나만 선택하고 아래 개수 규칙에 맞춰 queries 생성
- 서로 다른 답의 대상이 둘 이상이면 keep보다 transform·decomposition을 우선
- 일상 표현을 문서 용어로 바꿀 수 있으면 clarify보다 transform·rewrite를 우선
- multi일 때 queries는 정확히 3개 생성
- decomposition일 때 queries는 독립적인 요구사항별로 2~4개 생성
- rewrite·hyde·stepback일 때 queries는 정확히 1개 생성
- 독립적인 요구사항이 둘 이상이면 multi가 아니라 decomposition을 선택
- multi는 하나의 의도를 유지하고 표현만 바꾸며 요구사항별로 분리하지 않음
- 하나의 결론에 함께 적용되는 금액·기간·연체 등의 조건은 서로 나누지 않음
- 같은 혜택의 적립률·한도·실적처럼 함께 답할 수 있는 여러 속성은 한 하위 질문으로 유지
- 쉼표나 나열 항목 수가 아니라 서로 다른 상위 주제의 수를 기준으로 분해
- 상품명은 그 상품을 직접 묻는 하위 질문에만 유지하고 다른 요구사항에 임의로 붙이지 않음
- decomposition의 하위 질문 수는 서로 다른 답의 대상 수와 같아야 함
- 원 질문 자체를 queries에 반복하지 않음
- 설명이나 마크다운 코드 블록을 JSON 밖에 출력하지 않음

원 질문: {query}"""


@dataclass(frozen=True)
class RouteDecision:
    """한 번의 LLM 호출로 얻은 행동·기법 선택과 변환 질의."""

    action: str
    technique: str | None
    queries: tuple[str, ...]
    reason: str = ""
    clarification: str = ""
    error: str = ""


def _response_text(response) -> str:
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        return str(response.get("content") or response.get("text") or "")
    return str(getattr(response, "text", "") or "")


def _parse_json_object(text: str) -> dict:
    """코드 블록이 섞여도 첫 JSON 객체만 추출함."""
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", text.strip(), flags=re.I)
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.S)
        if not match:
            raise ValueError("LLM 응답에서 JSON 객체를 찾지 못함") from None
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError as error:
            raise ValueError("LLM 응답의 JSON 형식이 올바르지 않음") from error
    if not isinstance(value, dict):
        raise ValueError("LLM 응답은 JSON 객체여야 함")
    return value


def select_and_transform(
    query: str,
    ask_fn: Callable = ask_llm,
) -> RouteDecision:
    """기법 선택과 질의 생성을 LLM 한 번으로 수행함."""
    original = query.strip()
    if not original:
        raise ValueError("질문이 비어 있음")
    try:
        response = ask_fn(
            ROUTER_SYSTEM_PROMPT,
            ROUTER_USER_PROMPT.format(query=original),
        )
        value = _parse_json_object(_response_text(response))
        technique = str(value.get("technique", "")).strip().lower()
        action = str(value.get("action", "")).strip().lower()
        action = {
            "변환": "transform",
            "변환함": "transform",
            "유지": "keep",
            "원 결과 유지": "keep",
            "확인": "clarify",
            "확인 필요": "clarify",
        }.get(action, action)
        technique = {
            "다중 질의": "multi",
            "다중질의": "multi",
            "가설 답변": "hyde",
            "분해": "decomposition",
            "분해하기": "decomposition",
        }.get(technique, technique)
        if not action and technique:
            action = "transform"
        if action not in {"clarify", "keep", "transform"}:
            raise ValueError("지원하지 않는 라우터 행동")
        reason = str(value.get("reason", "")).strip()
        clarification = str(value.get("clarification", "")).strip()
        if action in {"clarify", "keep"}:
            if action == "clarify" and not clarification:
                raise ValueError("clarify에는 clarification 질문이 필요함")
            return RouteDecision(
                action=action,
                technique=None,
                queries=(),
                reason=reason,
                clarification=clarification,
            )
        raw_queries = value.get("queries")
        if technique not in TECHNIQUES:
            raise ValueError("지원하지 않는 질문 변환 기법")
        if not isinstance(raw_queries, list):
            raise ValueError("queries가 목록이 아님")
        queries = tuple(
            dict.fromkeys(
                str(item).strip()
                for item in raw_queries
                if str(item).strip() and str(item).strip() != original
            )
        )
        if technique == "multi" and len(queries) != 3:
            raise ValueError("multi의 변환 질의 수는 3개여야 함")
        if technique == "decomposition" and not 2 <= len(queries) <= 4:
            raise ValueError("decomposition의 하위 질문 수는 2~4개여야 함")
        if technique not in {"multi", "decomposition"} and len(queries) != 1:
            raise ValueError(f"{technique}의 변환 질의 수는 1개여야 함")
        return RouteDecision(
            action="transform",
            technique=technique,
            queries=queries,
            reason=reason,
        )
    except (KeyError, RuntimeError, TypeError, ValueError) as error:
        return RouteDecision("keep", None, (), error=str(error))


def _hit_id(hit) -> str:
    return str(hit.metadata.get("chunk_id", "")).strip()


def weighted_rrf(
    ranked_lists: list[tuple[str, list, float]],
    *,
    rrf_k: int = 60,
) -> list[dict]:
    """목록별 가중치를 적용한 RRF로 점수 척도가 다른 결과를 병합함."""
    if rrf_k < 0:
        raise ValueError("rrf_k는 0 이상이어야 함")
    merged: dict[str, dict] = {}
    for label, hits, weight in ranked_lists:
        if weight <= 0:
            raise ValueError("RRF 목록 가중치는 양수여야 함")
        for rank, hit in enumerate(hits, start=1):
            chunk_id = _hit_id(hit)
            if not chunk_id:
                continue
            item = merged.setdefault(
                chunk_id,
                {"hit": hit, "rrf_score": 0.0, "source_ranks": {}},
            )
            item["rrf_score"] += weight / (rrf_k + rank)
            item["source_ranks"][label] = rank
    return sorted(
        merged.values(),
        key=lambda item: (
            -item["rrf_score"],
            min(item["source_ranks"].values()),
            _hit_id(item["hit"]),
        ),
    )


def ensure_decomposition_coverage(ranked: list[dict], hit_groups: list[list]) -> list[dict]:
    """하위 질문마다 1위 청크 한 건을 보존하고 나머지는 RRF 순위를 유지함."""
    by_id = {_hit_id(item["hit"]): item for item in ranked}
    reserved = []
    reserved_ids = set()
    for hits in hit_groups:
        if not hits:
            continue
        chunk_id = _hit_id(hits[0])
        if chunk_id and chunk_id not in reserved_ids and chunk_id in by_id:
            reserved.append(by_id[chunk_id])
            reserved_ids.add(chunk_id)
    return reserved + [item for item in ranked if _hit_id(item["hit"]) not in reserved_ids]


def adaptive_search(
    query: str,
    search_fn: Callable,
    *,
    threshold: float = 0.70,
    retrieve_k: int = 10,
    user_role: str = "agent",
    filters: dict | None = None,
    rrf_k: int = 60,
    ask_fn: Callable = ask_llm,
) -> dict:
    """원 질문을 먼저 검색하고 Top-1 점수가 낮을 때만 한 기법을 적용함."""
    if not 0 <= threshold <= 1:
        raise ValueError("threshold는 0과 1 사이여야 함")
    if isinstance(retrieve_k, bool) or not isinstance(retrieve_k, int) or retrieve_k <= 0:
        raise ValueError("retrieve_k는 양의 정수여야 함")
    original = query.strip()
    if not original:
        raise ValueError("질문이 비어 있음")

    baseline_hits = search_fn(original, retrieve_k, filters, user_role)
    top1_score = baseline_hits[0].score if baseline_hits else None
    sufficient = top1_score is not None and top1_score >= threshold

    if sufficient:
        return {
            "query": original,
            "threshold": threshold,
            "baseline_top1_score": top1_score,
            "gate_sufficient": True,
            "route_action": "gate_pass",
            "technique": None,
            "transformed_queries": [],
            "route_reason": "",
            "route_error": "",
            "clarification": "",
            "coverage_applied": False,
            "llm_calls": 0,
            "baseline_hits": baseline_hits,
            "ranked_hits": [
                {"hit": hit, "rrf_score": None, "source_ranks": {"original": rank}}
                for rank, hit in enumerate(baseline_hits, start=1)
            ],
        }

    decision = select_and_transform(original, ask_fn=ask_fn)
    if not decision.queries:
        ranked = [
            {"hit": hit, "rrf_score": None, "source_ranks": {"original": rank}}
            for rank, hit in enumerate(baseline_hits, start=1)
        ]
    else:
        transformed_groups = [
            search_fn(transformed, retrieve_k, filters, user_role)
            for transformed in decision.queries
        ]
        # 서로 다른 답의 대상을 나눈 Decomposition은 하위 질문이 각 답을
        # 대표하므로 원 질문은 보조 역할(0.1)만 부여함.
        original_weight = 0.1 if decision.technique == "decomposition" else 0.5
        transformed_weight = (1 - original_weight) / len(transformed_groups)
        lists = [("original", baseline_hits, original_weight)] + [
            (f"transformed_{index}", hits, transformed_weight)
            for index, hits in enumerate(transformed_groups, start=1)
        ]
        ranked = weighted_rrf(lists, rrf_k=rrf_k)
        if decision.technique == "decomposition":
            ranked = ensure_decomposition_coverage(ranked, transformed_groups)

    return {
        "query": original,
        "threshold": threshold,
        "baseline_top1_score": top1_score,
        "gate_sufficient": False,
        "route_action": decision.action,
        "technique": decision.technique,
        "transformed_queries": list(decision.queries),
        "route_reason": decision.reason,
        "route_error": decision.error,
        "clarification": decision.clarification,
            "coverage_applied": decision.technique == "decomposition" and bool(decision.queries),
            "merge_weights": {
                "original": original_weight,
                "transformed_total": 1 - original_weight,
                "transformed_each": transformed_weight,
            },
            "llm_calls": 1,
        "baseline_hits": baseline_hits,
        "ranked_hits": ranked,
    }
