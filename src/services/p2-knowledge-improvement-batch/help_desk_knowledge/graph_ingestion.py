from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping

from help_desk_dataset.glossary import Glossary


CONFLICTING_RELATIONSHIPS = frozenset(
    {frozenset({"분쟁제기함", "분쟁제기하지않음"})}
)


@dataclass(frozen=True)
class Relationship:
    source: str
    relation_type: str
    target: str
    domain_valid: bool = True
    orphaned: bool = False


@dataclass(frozen=True)
class IngestionDecision:
    accepted: bool
    reason: str
    action: str


def prepare_rows(
    rows: Iterable[Mapping[str, object]],
    glossary: Glossary,
    alias_fields: tuple[str, ...],
) -> tuple[dict[str, object], ...]:
    prepared = []
    for row in rows:
        item = dict(row)
        for field in alias_fields:
            value = str(item[field])
            normalized = glossary.normalize(value)
            if len(normalized.canonical_terms) != 1:
                raise ValueError(f"미등록어 또는 1:N 충돌로 신규 개체 생성 보류: {field}")
            item[field] = normalized.canonical_terms[0]
        prepared.append(item)
    return tuple(prepared)


def validate_structure(rows: Iterable[Relationship], failure_action: str) -> IngestionDecision:
    materialized = tuple(rows)
    if any(not item.domain_valid or item.orphaned for item in materialized):
        return IngestionDecision(False, "정의역·치역 위반 또는 고아 노드 1건 이상", failure_action)
    by_pair: dict[tuple[str, str], set[str]] = {}
    for item in materialized:
        by_pair.setdefault((item.source, item.target), set()).add(item.relation_type)
    for relation_types in by_pair.values():
        if any(pair.issubset(relation_types) for pair in CONFLICTING_RELATIONSHIPS):
            return IngestionDecision(False, "상충 관계 쌍 동시 존속 1건 이상", failure_action)
    return IngestionDecision(True, "구조 검사 통과", failure_action)


def validate_human_accuracy(
    matched: int,
    sampled: int,
    required_sample_size: int,
    required_accuracy: float,
    failure_action: str,
) -> IngestionDecision:
    if sampled != required_sample_size:
        return IngestionDecision(False, "사람 판정 표본 수 불일치", failure_action)
    accuracy = matched / sampled if sampled else 0.0
    if accuracy < required_accuracy:
        return IngestionDecision(False, "사람 판정 정확도 합격선 미달", failure_action)
    return IngestionDecision(True, "사람 판정 검사 통과", failure_action)
