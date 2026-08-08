"""도구 호출측 — 승인 없는 호출이 거부되는지 확인함(시험 1번).

⑥ 승인 지점 표에서 **사람 승인·확인 필수로 판정된 행 수**와 거부 로그 수가 같아야 함.
제한 장치로 대체된 행과 규제 때문에 문을 두지 않은 행도 전건을 따로 확인함.
"""

from __future__ import annotations

import pytest

from common.guardrail.tool_guard import ApprovalEvidence, ToolGuard

NOW = 1_000_000
LATER = NOW + 60_000


def _evidence(tool_id: str, *, expires_at_ms: int | None = LATER) -> ApprovalEvidence:
    return ApprovalEvidence(
        approval_id=f"AP-{tool_id}",
        approver_ref="회원해시12자리",
        approved_at_ms=NOW,
        subject=f"{tool_id}:월 4900원 정기",
        shown_items=("청약철회 7일", "자동 갱신·다음 결제일", "해지 방법"),
        expires_at_ms=expires_at_ms,
    )


def test_human_gate_row_count_equals_denial_log_count(rulebook) -> None:
    """⑥ 승인 지점 표 전 행 → 승인 없는 호출이 거부됨. **행 수와 로그 수가 같음.**"""
    guard = ToolGuard(rulebook)
    rows = guard.human_gate_tool_ids()
    denial_log: list[str] = []
    for tool_id in rows:
        decision = guard.evaluate(tool_id, request_id="REQ-1", now_ms=NOW)
        assert not decision.allowed, f"{tool_id}이 승인 없이 통과했음"
        denial_log.append(f"{tool_id} 거부 — {decision.decision.rule_id}:{decision.reason}")
    assert len(denial_log) == len(rows) == rulebook.counts["human_gate_tool"] == 3
    print("\n".join(denial_log))


def test_unknown_tool_is_denied_by_default(rulebook) -> None:
    """허용을 적어 두지 않은 것은 일단 못 하게 막음 — 기본 거부."""
    guard = ToolGuard(rulebook)
    decision = guard.evaluate("C-99", request_id="REQ-1", now_ms=NOW)
    assert not decision.allowed
    assert decision.mode == "unknown"


@pytest.mark.parametrize("tool_id", ["C-9", "C-12", "R-9"])
def test_approval_with_all_guards_is_allowed(rulebook, tool_id) -> None:
    guard = ToolGuard(rulebook)
    row = rulebook.approval_tool(tool_id)
    decision = guard.evaluate(
        tool_id,
        request_id="REQ-1",
        now_ms=NOW,
        evidence=_evidence(tool_id),
        guards_met={g: True for g in row["guards"]},
        idempotency_key="IDEM-1",
    )
    assert decision.allowed, decision.reason
    assert decision.record["승인 ID 해시"] != _evidence(tool_id).approval_id


def test_approval_evidence_is_not_a_single_boolean() -> None:
    """승인 표시는 참·거짓 한 값이 아님 — 누가 · 언제 · 무엇을 담음."""
    ev = _evidence("C-9")
    assert ev.approver_ref and ev.approved_at_ms and ev.subject


def test_same_approval_cannot_be_used_twice(rulebook) -> None:
    """같은 승인 표시를 두 번 쓸 수 없음. 중복 방지 키와 짝지음."""
    guard = ToolGuard(rulebook)
    row = rulebook.approval_tool("C-9")
    met = {g: True for g in row["guards"]}
    first = guard.evaluate(
        "C-9", request_id="REQ-1", now_ms=NOW, evidence=_evidence("C-9"),
        guards_met=met, idempotency_key="IDEM-1",
    )
    second = guard.evaluate(
        "C-9", request_id="REQ-2", now_ms=NOW, evidence=_evidence("C-9"),
        guards_met=met, idempotency_key="IDEM-2",
    )
    assert first.allowed
    assert not second.allowed
    assert second.reason == "approval_reused"


def test_expired_approval_is_denied(rulebook) -> None:
    """`B-22` — 승인 플래그가 있으나 세션이 만료되면 차단하고 승인 화면부터 다시."""
    guard = ToolGuard(rulebook)
    row = rulebook.approval_tool("C-9")
    decision = guard.evaluate(
        "C-9",
        request_id="REQ-1",
        now_ms=LATER + 1,
        evidence=_evidence("C-9", expires_at_ms=LATER),
        guards_met={g: True for g in row["guards"]},
        idempotency_key="IDEM-1",
    )
    assert not decision.allowed
    assert decision.reason == "approval_session_expired"


def test_approval_without_shown_items_is_not_an_approval(rulebook) -> None:
    """고지 없는 승인은 승인으로 세지 않음(`B-21` · `B-13`)."""
    guard = ToolGuard(rulebook)
    row = rulebook.approval_tool("C-12")
    ev = ApprovalEvidence(
        approval_id="AP-X",
        approver_ref="회원해시",
        approved_at_ms=NOW,
        subject="C-12:해지",
        shown_items=(),
    )
    decision = guard.evaluate(
        "C-12", request_id="REQ-1", now_ms=NOW, evidence=ev,
        guards_met={g: True for g in row["guards"]}, idempotency_key="IDEM-1",
    )
    assert not decision.allowed
    assert decision.reason == "shown_items_absent"


def test_every_guarded_row_is_denied_when_a_guard_is_missing(rulebook) -> None:
    """제한 장치로 대체된 행 전건 — 장치 증거가 없으면 거부됨."""
    guard = ToolGuard(rulebook)
    log: list[str] = []
    for tool_id in guard.guarded_tool_ids():
        decision = guard.evaluate(tool_id, request_id="REQ-1", now_ms=NOW, guards_met={})
        assert not decision.allowed, f"{tool_id}이 제한 장치 없이 통과했음"
        log.append(f"{tool_id} 거부 — 빠진 장치 {list(decision.missing_guards)}")
    assert len(log) == len(guard.guarded_tool_ids()) == 10
    print("\n".join(log))


def test_regulated_rows_are_never_gated(rulebook) -> None:
    """승인을 붙이면 규제가 요구한 기록이 막히는 2행은 문을 두지 않음(⑥ 3-2절 7 · 15번)."""
    guard = ToolGuard(rulebook)
    ids = guard.regulated_tool_ids()
    assert len(ids) == 2
    for tool_id in ids:
        decision = guard.evaluate(tool_id, request_id="REQ-1", now_ms=NOW)
        assert decision.allowed


def test_all_fifteen_write_tools_are_covered(rulebook) -> None:
    """쓰기·발송·과금 도구 15종 전부가 승인·제한 장치·규제 예외 중 하나로 덮임. 맨몸 실행 0건."""
    guard = ToolGuard(rulebook)
    covered = set(guard.human_gate_tool_ids()) | set(guard.guarded_tool_ids()) | set(
        guard.regulated_tool_ids()
    )
    assert len(covered) == rulebook.counts["approval_tool"] == 15


def test_daily_cap_blocks_send_connector(rulebook) -> None:
    """`C-10` 1일 1회 상한 — 넘으면 막고 기록함(⑥ 3-2절 2번 ⓑ)."""
    guard = ToolGuard(rulebook)
    row = rulebook.approval_tool("C-10")
    met = {g: True for g in row["guards"]}
    ok = guard.evaluate("C-10", request_id="REQ-1", now_ms=NOW, guards_met=met, daily_count=0)
    over = guard.evaluate("C-10", request_id="REQ-1", now_ms=NOW, guards_met=met, daily_count=1)
    assert ok.allowed
    assert not over.allowed
    assert over.reason == "daily_cap"


def test_call_counter_counts_per_request(rulebook) -> None:
    guard = ToolGuard(rulebook)
    row = rulebook.approval_tool("R-13")
    met = {g: True for g in row["guards"]}
    for _ in range(3):
        guard.evaluate("R-13", request_id="REQ-1", now_ms=NOW, guards_met=met)
    assert guard.counter.count("REQ-1", "R-13") == 3
    assert guard.counter.count("REQ-2", "R-13") == 0


def test_sieve_stops_at_first_rule_not_a_score_sum(rulebook) -> None:
    """차단은 거름망임 — 다른 지표가 좋아도 한 규칙에 걸리면 막음."""
    guard = ToolGuard(rulebook)
    decision = guard.sieve(
        {"idempotency_key_absent": True, "pg_auto_retry_attempted": True},
        point="tool",
        step_id="S-X4",
    )
    assert decision is not None
    assert decision.rule_id == "B-30"  # 설정 순서대로 첫 규칙. 점수를 합산하지 않음
    assert guard.sieve({"idempotency_key_absent": False}, point="tool", step_id="S-X4") is None
