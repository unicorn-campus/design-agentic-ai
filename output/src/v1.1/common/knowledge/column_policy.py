"""조회 컬럼 허용 목록과 차단 목록 — 각각 **상수 1벌**임.

- 허용 목록의 주인은 ④ 역할계약서 「접근 가능한 정보 항목」임. 여기서 열을 더하지 않음
- 차단 목록의 주인은 ⑤ 4절 「정형 접근 금지 컬럼」임. 걸리면 **조회를 만들다 말고 실패**함.
  값을 읽어 놓고 가려서 내보내는 길은 만들지 않음
- ④에 허용 목록이 없는 경로는 **비운 채로 열지 않음.** 왜 못 여는지 사유를 돌려줌
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = [
    "AGENT_ALLOWED_COLUMNS",
    "BLOCKED_COLUMNS",
    "BLOCKED_COLUMN_EXCEPTIONS",
    "BLOCKED_TABLES",
    "UNASSIGNED_PATHS",
    "AllowListMissing",
    "BlockedColumn",
    "ColumnBlocked",
    "ColumnNotAllowed",
    "allowed_columns_for",
    "assert_columns_allowed",
    "blocked_columns_of_table",
    "project",
    "resolve_columns",
]


class ColumnBlocked(PermissionError):
    """차단 목록에 걸린 열임. 조회를 만들지 않고 여기서 멈춤."""


class ColumnNotAllowed(PermissionError):
    """허용 목록 밖의 열임. 조회문에 넣지 않음."""


class AllowListMissing(LookupError):
    """이 담당자·경로 짝에 허용 목록이 없음. 비운 채로 열지 않음."""


@dataclass(frozen=True, slots=True)
class BlockedColumn:
    """차단 1건. `표.열` 꼴 전건을 ⑤ 4절에서 옮겼음."""

    rule_id: str
    logical_table: str
    column: str
    reason: str
    allowed_agents: tuple[str, ...] = ()

    @property
    def qualified(self) -> str:
        return f"{self.logical_table}.{self.column}"


# ⑤ 4절 `D-1` ~ `D-9` 9건을 하나도 빼지 않고 옮김. `D-8`만 예외 담당자가 1명 있음.
_BLOCKED: tuple[BlockedColumn, ...] = (
    BlockedColumn("D-1", "member_profile", "email", "계정 식별정보"),
    BlockedColumn("D-2", "member_profile", "kakao_id", "외부 계정 식별자"),
    BlockedColumn("D-3", "member_profile", "push_token", "발송 채널 전용 값"),
    BlockedColumn(
        "D-4", "diet_restriction", "allergy_free_text", "자유 입력 문자열 — 주입 경로"
    ),
    BlockedColumn("D-5", "location_history", "lat", "정확 좌표"),
    BlockedColumn("D-6", "location_history", "lng", "정확 좌표"),
    BlockedColumn("D-7", "audit_log", "*", "개인정보 접근 감사 기록 — 전 열"),
    BlockedColumn(
        "D-8",
        "subscription",
        "payment_id",
        "결제 식별자 — 모델을 쓰는 담당자에게 보이지 않게 함",
        allowed_agents=("R-9",),
    ),
    BlockedColumn(
        "D-9", "accept_reject_log", "accept_latency_ms", "행동 로그 — 학습 배치만 씀",
        allowed_agents=("R-3",),
    ),
)

BLOCKED_COLUMNS: dict[str, BlockedColumn] = {rule.rule_id: rule for rule in _BLOCKED}
BLOCKED_COLUMN_EXCEPTIONS: dict[str, tuple[str, ...]] = {
    rule.rule_id: rule.allowed_agents for rule in _BLOCKED if rule.allowed_agents
}
# 표 전체가 담당자 조회 대상이 아닌 경우 — 경로 자체를 만들지 않음.
BLOCKED_TABLES: dict[str, str] = {"audit_log": "D-7", "location_history": "D-5 · D-6"}

# ④ 「접근 가능한 정보 항목」을 담당자 × 경로로 펼친 것.
# 열 이름은 ⑤ 3절 경로 표의 논리 열 이름과 맞춘 것이며 여기서 새 이름을 짓지 않았음.
AGENT_ALLOWED_COLUMNS: dict[str, dict[str, tuple[str, ...]]] = {
    "R-2": {
        "T-2": ("member_id", "allergen_labels", "diet_type"),
        "T-3": ("member_id", "consent_kind", "consent_state", "consented_at"),
        "T-4": ("member_id", "eaten_at", "restaurant_id", "restaurant_name", "category_code"),
        "T-8": ("member_id", "recommendation_id", "reject_reason"),
        "T-10": ("member_id", "vector"),
        "T-11": ("member_id", "recommendation_set", "cached_at"),
    },
    "R-3": {
        "T-3": ("member_id", "consent_kind", "consent_state"),
        "T-4": ("member_id", "eaten_at", "category_code"),
        "T-6": ("member_id", "satisfaction", "keyword", "created_at"),
        "T-8": ("member_id", "recommendation_id", "reject_reason"),
        "T-10": ("member_id", "vector"),
    },
    "R-5": {
        "T-4": ("member_id", "eaten_at", "restaurant_id", "restaurant_name", "category_code"),
        "T-6": ("member_id", "satisfaction", "keyword", "created_at"),
    },
    "R-6": {
        "T-1": ("member_id", "nickname", "notify_enabled", "subscription_state"),
        "T-3": ("member_id", "consent_kind", "consent_state"),
    },
    "R-7": {"T-12": ("member_id", "plan_code", "next_billing_on")},
    "R-9": {"T-12": ("member_id", "plan_code", "next_billing_on")},
    "R-11": {"T-12": ("member_id", "plan_code", "next_billing_on")},
    "R-12": {
        "T-1": ("member_id", "subscription_state"),
        "T-12": ("member_id", "plan_code", "next_billing_on"),
    },
    "R-13": {"T-1": ("member_id", "subscription_state")},
    "R-14": {
        "T-1": ("member_id", "subscription_state"),
        "T-5": ("member_id", "eaten_on", "restaurant_name", "category_code"),
        "T-9": ("member_id", "metric", "bucket", "value"),
    },
    "R-15": {
        "T-1": ("member_id", "subscription_state"),
        "T-5": ("member_id", "eaten_on"),
    },
}

# ④ 7절 · 7-2절 어느 담당자에게도 배정되지 않은 경로. 허용 목록이 없어 **열지 않음**.
UNASSIGNED_PATHS: dict[str, str] = {
    "T-7": "[확인필요: 선행 미배정 — ④에 `recommendation` 조회 담당자·허용 열이 없음]",
    "T-13": "[확인필요: 선행 미배정 — ④에 `insight_weekly_agg` 조회 담당자·허용 열이 없음]",
    "T-14": "[확인필요: 선행 미배정 — ④에 `subscription_plan` 조회 담당자·허용 열이 없음]",
    "T-15": "[확인필요: 선행 미배정 — ④가 해지 사전 조건을 `T-12` 허용 열로만 적었음]",
    "T-16": "[확인필요: 선행 미배정 — ④에 만료 전환 배치 조회 담당자·허용 열이 없음]",
    "T-17": "[확인필요: 선행 미배정 — ④가 기억 제한 집계를 `T-5` 허용 열로만 적었음]",
    "T-18": "[확인필요: 선행 미배정 — ④에 `payment_fail_log` 조회 담당자·허용 열이 없음]",
}


def blocked_columns_of_table(logical_table: str, agent_id: str) -> tuple[BlockedColumn, ...]:
    """이 담당자에게 이 표에서 막힌 열. 예외 담당자면 그 행만 빠짐."""
    return tuple(
        rule
        for rule in _BLOCKED
        if rule.logical_table == logical_table and agent_id not in rule.allowed_agents
    )


def allowed_columns_for(agent_id: str, path_id: str) -> tuple[str, ...]:
    """④가 이 담당자에게 허용한 열. 없으면 비운 채로 열지 않고 실패함."""
    by_path = AGENT_ALLOWED_COLUMNS.get(agent_id)
    if by_path is None:
        raise AllowListMissing(
            f"④ 「접근 가능한 정보 항목」에 {agent_id}의 조회 경로가 없음 — 허용 목록을 비운 채로 열지 않음"
        )
    try:
        return by_path[path_id]
    except KeyError as exc:
        unassigned = UNASSIGNED_PATHS.get(path_id)
        tail = f" — {unassigned}" if unassigned else ""
        raise AllowListMissing(
            f"④가 {agent_id}에게 {path_id}의 허용 열을 적지 않았음{tail}"
        ) from exc


def assert_columns_allowed(agent_id: str, logical_table: str, columns: tuple[str, ...]) -> None:
    """차단 목록을 먼저 보고, 그 다음 허용 목록을 봄. 차단이 이김."""
    if logical_table in BLOCKED_TABLES:
        raise ColumnBlocked(
            f"{logical_table}은 표 전체가 차단 목록임({BLOCKED_TABLES[logical_table]})"
        )
    for rule in _BLOCKED:
        if rule.logical_table != logical_table:
            continue
        if agent_id in rule.allowed_agents:
            continue
        if rule.column == "*" or rule.column in columns:
            raise ColumnBlocked(
                f"{rule.qualified}은 ⑤ 4절 {rule.rule_id} 차단 목록임 — {rule.reason}"
            )


def resolve_columns(
    agent_id: str,
    path_id: str,
    logical_table: str,
    spec_columns: tuple[str, ...],
    requested: tuple[str, ...] | None = None,
) -> tuple[str, ...]:
    """조회문에 실제로 넣을 열을 정함.

    - 부르는 쪽이 열을 지목했으면 **허용 목록 밖이면 거부**함
    - 지목하지 않았으면 `허용 목록 ∩ 경로가 가진 열`만 넣음
    - 어느 쪽이든 차단 목록 검사를 먼저 지남
    """
    allowed = allowed_columns_for(agent_id, path_id)
    if requested is None:
        columns = tuple(name for name in allowed if name in spec_columns)
    else:
        outside = sorted(set(requested) - set(allowed))
        if outside:
            raise ColumnNotAllowed(
                f"④ 「접근 가능한 정보 항목」에 없는 열임 — {agent_id} · {path_id} · {outside}"
            )
        missing = sorted(set(requested) - set(spec_columns))
        if missing:
            raise ColumnNotAllowed(
                f"⑤ 3절 {path_id}의 열 목록에 없는 이름임 — {missing}"
            )
        columns = tuple(name for name in allowed if name in requested)
    assert_columns_allowed(agent_id, logical_table, columns)
    if not columns:
        raise AllowListMissing(
            f"{agent_id} · {path_id}에서 조회문에 넣을 열이 0건임 — 빈 조회를 만들지 않음"
        )
    return columns


def project(row: Any, allowed: tuple[str, ...]) -> dict[str, Any]:
    """허용된 열만 남기는 사영(projection). 허용 목록 밖 값은 결과에 담지 않음."""
    given = dict(row)
    return {name: given[name] for name in allowed if name in given}
