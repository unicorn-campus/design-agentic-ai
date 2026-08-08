"""도구 호출측 검사와 승인 문 — 기본은 거부임.

**어느 노드에 승인 문을 둘지는 여기서 정하지 않음**(`06-workflow.md` 몫).
여기서는 ⑥ 승인 지점 표를 그대로 읽어 **판정 함수**만 내놓음.

승인 표시(승인 증거)는 참·거짓 한 값이 아님 — **누가 · 언제 · 무엇을** 승인했는지를 담음.
같은 승인 표시를 두 번 쓸 수 없음. 중복 방지 키(같은 요청이 두 번 와도 한 번만 처리되게 하는
표식)와 짝지어 한 번만 통하게 함.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import BlockDecision
from .masking import irreversible_hash
from .rules import HUMAN_GATE_MODES, REGULATED_NO_GATE, RuleBook, get_rulebook

__all__ = [
    "ApprovalEvidence",
    "ApprovalLedger",
    "ToolCallCounter",
    "ToolDecision",
    "ToolGuard",
]


@dataclass(frozen=True, slots=True)
class ApprovalEvidence:
    """승인 표시. 참·거짓 한 값으로 두지 않음."""

    approval_id: str
    approver_ref: str
    """승인한 사람의 **가려진** 참조값. 회원 식별자 원문을 넣지 않음."""
    approved_at_ms: int
    subject: str
    """무엇을 승인했나 — 도구 식별자 + 대상."""
    shown_items: tuple[str, ...] = ()
    """승인 화면에 실제로 보여 준 고지·안내 항목(`O-C8` · `O-C9` 통과 증거)."""
    expires_at_ms: int | None = None
    """비면 만료 판정 기준선이 없음 — `[확인필요: 승인 세션 만료]`(③ 소유)."""

    @property
    def approval_id_hash(self) -> str:
        """기록에 남기는 값. 승인 ID 원문을 남기지 않음(`O-12` 항목 이름과 짝)."""
        return irreversible_hash(self.approval_id)

    def is_expired(self, now_ms: int) -> bool:
        return self.expires_at_ms is not None and now_ms >= self.expires_at_ms

    def covers(self, tool_id: str) -> bool:
        return self.subject.startswith(tool_id)


class ApprovalLedger:
    """같은 승인 표시를 두 번 쓰지 못하게 하는 장부."""

    def __init__(self) -> None:
        self._used: dict[str, str] = {}

    def consume(self, approval_id: str, idempotency_key: str) -> bool:
        """처음이면 True. 이미 쓴 승인이면 False(같은 중복 방지 키여도 두 번은 안 됨)."""
        key = irreversible_hash(f"{approval_id}|{idempotency_key}")
        if approval_id in self._used:
            return False
        self._used[approval_id] = key
        return True

    def used_count(self) -> int:
        return len(self._used)


class ToolCallCounter:
    """같은 요청에서 그 도구를 몇 번 불렀나. 넘으면 막고 기록함."""

    def __init__(self) -> None:
        self._counts: dict[tuple[str, str], int] = {}

    def count(self, request_id: str, tool_id: str) -> int:
        return self._counts.get((request_id, tool_id), 0)

    def bump(self, request_id: str, tool_id: str) -> int:
        key = (request_id, tool_id)
        self._counts[key] = self._counts.get(key, 0) + 1
        return self._counts[key]


@dataclass(frozen=True, slots=True)
class ToolDecision:
    """도구 1건에 대한 판정. 허용이 아니면 무조건 거부임."""

    tool_id: str
    allowed: bool
    mode: str
    """`human_approval` · `human_confirm` · `guarded` · `regulated_no_gate` · `unknown`."""
    reason: str
    decision: BlockDecision | None = None
    missing_guards: tuple[str, ...] = ()
    record: dict[str, Any] = field(default_factory=dict)
    """`O-12` · `O-13`에 남길 값. 이미 가려진 값만 담음."""


class ToolGuard:
    """⑥ 3-1 · 3-2절 승인 지점 표를 판정 함수로 옮긴 것. 표에 없는 도구는 거부함."""

    def __init__(
        self,
        book: RuleBook | None = None,
        ledger: ApprovalLedger | None = None,
        counter: ToolCallCounter | None = None,
    ) -> None:
        self._book = book or get_rulebook()
        self._ledger = ledger or ApprovalLedger()
        self._counter = counter or ToolCallCounter()

    # --- 조회 -------------------------------------------------------------
    @property
    def ledger(self) -> ApprovalLedger:
        return self._ledger

    @property
    def counter(self) -> ToolCallCounter:
        return self._counter

    def human_gate_tool_ids(self) -> tuple[str, ...]:
        """사람 승인·확인 필수로 판정된 도구. 시험이 행 수와 로그 수를 맞춰 보는 대상임."""
        return tuple(str(row["id"]) for row in self._book.human_gate_tools())

    def guarded_tool_ids(self) -> tuple[str, ...]:
        return tuple(str(row["id"]) for row in self._book.guarded_tools())

    def regulated_tool_ids(self) -> tuple[str, ...]:
        return tuple(str(row["id"]) for row in self._book.regulated_tools())

    # --- 판정 -------------------------------------------------------------
    def evaluate(
        self,
        tool_id: str,
        *,
        request_id: str,
        now_ms: int,
        evidence: ApprovalEvidence | None = None,
        guards_met: Mapping[str, bool] | None = None,
        idempotency_key: str | None = None,
        daily_count: int = 0,
    ) -> ToolDecision:
        row = self._book.approval_tool(tool_id)
        if row is None:
            # 기본 거부 — 허용을 적어 두지 않은 것은 일단 못 하게 막음
            return ToolDecision(
                tool_id=tool_id,
                allowed=False,
                mode="unknown",
                reason="승인 지점 표에 없는 도구 — 기본 거부",
                record={"tool": tool_id},
            )

        mode = str(row["mode"])
        met = dict(guards_met or {})
        record: dict[str, Any] = {"도구명": tool_id, "mode": mode}

        if mode == REGULATED_NO_GATE:
            # 승인을 붙이면 규제가 요구한 기록이 막힘(⑥ 3-2절 7 · 15번)
            return ToolDecision(
                tool_id=tool_id,
                allowed=True,
                mode=mode,
                reason="규제가 요구한 기록이라 승인 문을 두지 않음",
                record=record,
            )

        # 호출 상한 — 설정에 있는 도구만 셈. 없는 상한을 지어내지 않음
        cap = row.get("daily_cap")
        if cap is not None and daily_count >= int(cap):
            return self._deny(row, "daily_cap", record, note=f"1일 상한 {cap}회 초과")

        if mode in HUMAN_GATE_MODES:
            if evidence is None:
                return self._deny(row, "approval_evidence_absent", record)
            if not evidence.covers(tool_id):
                return self._deny(row, "approval_subject_mismatch", record)
            if evidence.is_expired(now_ms):
                return self._deny(row, "approval_session_expired", record)
            if not evidence.shown_items:
                # 고지 없는 승인은 승인으로 세지 않음(`B-21` · `B-13`)
                return self._deny(row, "shown_items_absent", record)
            if idempotency_key is None:
                return self._deny(row, "idempotency_key_absent", record)
            if not self._ledger.consume(evidence.approval_id, idempotency_key):
                return self._deny(row, "approval_reused", record)
            record.update(
                {
                    "승인 ID 해시": evidence.approval_id_hash,
                    "표시한 고지·안내 항목 목록": list(evidence.shown_items),
                    "승인 시각": evidence.approved_at_ms,
                    "만료 여부": evidence.is_expired(now_ms),
                    "멱등성 키 해시": irreversible_hash(idempotency_key),
                }
            )

        missing = [g for g in row.get("guards", ()) if not met.get(g, False)]
        # 사람 게이트에서 이미 확인한 항목은 빼고 셈
        if mode in HUMAN_GATE_MODES and evidence is not None:
            already = {"approval_flag", "approval_session_fresh", "confirm_modal_passed"}
            if idempotency_key is not None:
                already.add("idempotency_key")
            missing = [g for g in missing if g not in already]
        if missing:
            return self._deny(row, "guard_absent", record, missing=tuple(missing))

        self._counter.bump(request_id, tool_id)
        record["호출 횟수"] = self._counter.count(request_id, tool_id)
        return ToolDecision(
            tool_id=tool_id,
            allowed=True,
            mode=mode,
            reason="승인·제한 장치 전건 충족",
            record=record,
        )

    # --- 거름망 -----------------------------------------------------------
    def sieve(
        self, signals: Mapping[str, bool], *, point: str | None = None, step_id: str | None = None
    ) -> BlockDecision | None:
        """차단은 거름망임 — 점수를 합산하지 않고 **한 규칙에 걸리면** 막음.

        여러 규칙이 걸리면 설정 파일에 적힌 순서대로 **첫 규칙**을 돌려줌.
        """
        for row in self._book.block_rules:
            if point is not None and str(row["point"]) != point:
                continue
            if step_id is not None and not (
                row.get("all_steps", False) or step_id in row.get("steps", [])
            ):
                continue
            if signals.get(str(row["signal"]), False):
                return BlockDecision(
                    rule_id=str(row["id"]),
                    action=str(row["action"]),
                    point=str(row["point"]),
                    signal=str(row["signal"]),
                    notify=tuple(row.get("notify", ())),
                    step_id=step_id,
                )
        return None

    def _deny(
        self,
        row: Mapping[str, Any],
        reason: str,
        record: dict[str, Any],
        *,
        missing: tuple[str, ...] = (),
        note: str = "",
    ) -> ToolDecision:
        rule_ids = tuple(row.get("block_rules", ()))
        rule_id = str(rule_ids[0]) if rule_ids else str(row["id"])
        action = "deny_tool_call"
        signal = reason
        notify: tuple[str, ...] = ()
        if rule_ids:
            block = self._book.block_rule(rule_id)
            action = str(block["action"])
            signal = str(block["signal"])
            notify = tuple(block.get("notify", ()))
        decision = BlockDecision(
            rule_id=rule_id,
            action=action,
            point="tool",
            signal=signal,
            notify=notify,
            detail={"tool": str(row["id"]), "reason": reason, "note": note},
        )
        record["미승인 종료 사유"] = reason
        return ToolDecision(
            tool_id=str(row["id"]),
            allowed=False,
            mode=str(row["mode"]),
            reason=reason,
            decision=decision,
            missing_guards=missing,
            record=record,
        )
