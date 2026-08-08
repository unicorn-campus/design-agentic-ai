"""출력측 검사 — 밖으로 나가기 직전에 걸러냄.

밖으로 나가는 **모든 경로**가 이 검사를 지남. 부분 전송(스트리밍) 경로도 예외로 두지 않음.
검사 조건은 설정 파일에서 읽고 코드에 박지 않음. 걸렸을 때 무엇을 하는지도 설정이 정함.
검사에 걸린 건은 **낮춰 보고하지 않고** 판정 그대로 남김.

**방식이 3종인 이유** — ⑥ 5절은 방식을 문서 단위로 1개 고른 것이 아니라 **행마다 1개씩** 골랐고,
11행에 `패턴`·`필드 지정`·`라벨 목록`이 모두 나타남(⑥ 5절 「검사 방식 3종 확인」).
그래서 판정기 3종을 두되 **한 행에는 그 행이 고른 방식만** 돌림. ⑥이 안 고른 방식은 어느 행에도
붙지 않음.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .errors import BlockDecision
from .masking import MaskPath, Masker, get_masker
from .rules import RuleBook, get_rulebook

__all__ = ["OutputFinding", "OutputVerdict", "OutputGuard"]


@dataclass(frozen=True, slots=True)
class OutputFinding:
    """검사 1건의 결과."""

    check_id: str
    kind: str
    """`pattern` · `field_spec` · `label_list` 중 그 행이 고른 방식."""
    passed: bool
    action: str
    target_field: str | None = None
    decision: BlockDecision | None = None


@dataclass(frozen=True, slots=True)
class OutputVerdict:
    step_id: str
    passed: bool
    payload: dict[str, Any] = field(default_factory=dict)
    """가리기까지 지난 뒤 밖으로 나갈 값. 폐기된 칸은 빠져 있음."""
    findings: tuple[OutputFinding, ...] = ()
    discarded_fields: tuple[str, ...] = ()
    checks_run: tuple[str, ...] = ()
    checks_disabled: tuple[str, ...] = ()
    audit_required: bool = False
    """감사 기록을 남겨야 하는 적중이 있었나(`B-5` · `B-20` 계열)."""

    def failed_checks(self) -> tuple[str, ...]:
        return tuple(f.check_id for f in self.findings if not f.passed)


# 걸렸을 때 그 칸을 지워야 하는 행동 이름 — 설정의 `action` 값을 코드가 읽는 이름
_DISCARDING_ACTIONS = frozenset(
    {
        "discard_sentence",
        "discard_sentence_and_audit",
        "hide_message",
        "hide_mismatched_items",
        "exclude_candidate",
        "leave_field_empty",
    }
)
_AUDIT_ACTIONS = frozenset({"discard_sentence_and_audit", "discard_now_and_audit"})
_HALT_ACTIONS = frozenset({"safe_exit", "block_send"})


class OutputGuard:
    """⑥ 5절 O-C1 ~ O-C11을 한 자리에서 판정하고, 통과분만 가리기까지 지나게 함."""

    def __init__(self, book: RuleBook | None = None, masker: Masker | None = None) -> None:
        self._book = book or get_rulebook()
        self._masker = masker or get_masker(self._book)
        self._patterns: dict[str, tuple[re.Pattern[str], ...]] = {
            str(row["id"]): tuple(re.compile(p) for p in (row.get("patterns") or []))
            for row in self._book.output_checks
        }
        self._audit_patterns: dict[str, tuple[re.Pattern[str], ...]] = {
            str(row["id"]): tuple(re.compile(p) for p in (row.get("audit_patterns") or []))
            for row in self._book.output_checks
        }

    # --- 공개 -------------------------------------------------------------
    def redact(
        self,
        step_id: str,
        payload: Mapping[str, Any],
        *,
        labels: Mapping[str, Sequence[str]] | None = None,
        truth: Mapping[str, Any] | None = None,
        path: MaskPath = MaskPath.RESPONSE,
    ) -> OutputVerdict:
        """`common.guardrail_hooks.OutputRedactor` 계약과 짝지음(hooks 모듈이 감쌈).

        `labels`는 설정에 `labels_from`이 적힌 행에 부르는 쪽이 넣어 주는 값임(지어내지 않음).
        `truth`는 `필드 지정` 대조가 볼 **원천 집계값**임.
        """
        working = dict(payload)
        findings: list[OutputFinding] = []
        discarded: list[str] = []
        ran: list[str] = []
        disabled: list[str] = []
        audit = False

        for row in self._checks_for(step_id):
            check_id = str(row["id"])
            bind = self._book.binding("output", check_id)
            if not row.get("enabled", True):
                disabled.append(check_id)
                findings.append(
                    OutputFinding(
                        check_id=check_id,
                        kind=",".join(row.get("kinds", ())),
                        passed=False,
                        action="not_running",
                    )
                )
                continue
            ran.append(check_id)
            for kind in row.get("kinds", ()):
                # 판정은 **들어온 원래 값**을 봄. 앞 행이 이미 그 칸을 지웠어도
                # 이 행이 걸린 사실을 낮춰 보고하지 않고 그대로 남김
                hits = self._run_kind(kind, row, bind, payload, labels, truth)
                for target in hits:
                    decision = self._decision(row, bind, step_id, target)
                    findings.append(
                        OutputFinding(
                            check_id=check_id,
                            kind=kind,
                            passed=False,
                            action=str(row["action"]),
                            target_field=target,
                            decision=decision,
                        )
                    )
                    if str(row["action"]) in _DISCARDING_ACTIONS:
                        working.pop(target, None)
                        discarded.append(target)
                    elif str(row["action"]) == "mask_then_release" and target in working:
                        mask_row = self._book.mask_rule(str(row["mask_rule"]))
                        working[target] = self._apply_named_mask(mask_row, working[target])
                    if str(row["action"]) in _AUDIT_ACTIONS:
                        audit = True
                    if self._audit_patterns[check_id] and target in payload:
                        value = payload[target]
                        if isinstance(value, str) and any(
                            p.search(value) for p in self._audit_patterns[check_id]
                        ):
                            working.pop(target, None)
                            discarded.append(target)
                            audit = True
                if not hits:
                    findings.append(
                        OutputFinding(
                            check_id=check_id, kind=kind, passed=True, action="pass"
                        )
                    )

        halted = any(
            f.action in _HALT_ACTIONS and not f.passed for f in findings
        )
        masked = self._masker.mask_mapping(working, path)
        return OutputVerdict(
            step_id=step_id,
            passed=not any(not f.passed for f in findings),
            payload={} if halted else masked,
            findings=tuple(findings),
            discarded_fields=tuple(dict.fromkeys(discarded)),
            checks_run=tuple(dict.fromkeys(ran)),
            checks_disabled=tuple(dict.fromkeys(disabled)),
            audit_required=audit,
        )

    def checks_for_step(self, step_id: str) -> tuple[str, ...]:
        return tuple(str(row["id"]) for row in self._checks_for(step_id))

    # --- 방식 3종 ----------------------------------------------------------
    def _run_kind(
        self,
        kind: str,
        row: Mapping[str, Any],
        bind: Mapping[str, Any],
        working: Mapping[str, Any],
        labels: Mapping[str, Sequence[str]] | None,
        truth: Mapping[str, Any] | None,
    ) -> tuple[str, ...]:
        targets = tuple(bind.get("target_fields") or ())
        if kind == "pattern":
            return self._pattern_hits(row, targets, working)
        if kind == "label_list":
            return self._label_hits(row, targets, working, labels)
        if kind == "field_spec":
            return self._field_spec_hits(row, targets, working, truth)
        return ()

    def _pattern_hits(
        self, row: Mapping[str, Any], targets: Sequence[str], working: Mapping[str, Any]
    ) -> tuple[str, ...]:
        patterns = self._patterns[str(row["id"])] or self._reused_patterns(row)
        hits: list[str] = []
        for key in targets:
            value = working.get(key)
            if isinstance(value, str) and any(p.search(value) for p in patterns):
                hits.append(key)
        return tuple(hits)

    def _label_hits(
        self,
        row: Mapping[str, Any],
        targets: Sequence[str],
        working: Mapping[str, Any],
        labels: Mapping[str, Sequence[str]] | None,
    ) -> tuple[str, ...]:
        banned = self._resolve_labels(row, labels)
        if row.get("require_all"):
            # 있어야 하는 항목이 하나라도 없으면 걸림(사전 고지 3항목)
            for key in targets:
                present = working.get(key) or ()
                if not isinstance(present, (list, tuple, set)):
                    present = (present,)
                missing = [lbl for lbl in row.get("labels", ()) if lbl not in present]
                if missing:
                    return (key,)
            return ()
        if not banned:
            return ()
        hits: list[str] = []
        for key in targets:
            value = working.get(key)
            if isinstance(value, str) and any(lbl in value for lbl in banned):
                hits.append(key)
        return tuple(hits)

    def _field_spec_hits(
        self,
        row: Mapping[str, Any],
        targets: Sequence[str],
        working: Mapping[str, Any],
        truth: Mapping[str, Any] | None,
    ) -> tuple[str, ...]:
        hits: list[str] = []
        reject = tuple(row.get("reject_values") or ())
        for key in targets:
            value = working.get(key)
            if reject and value in reject:
                hits.append(key)
                continue
            if row.get("require_non_empty") and not value:
                hits.append(key)
                continue
            if truth is not None and key in truth and value != truth[key]:
                hits.append(key)
        return tuple(hits)

    # --- 도우미 -----------------------------------------------------------
    def _checks_for(self, step_id: str) -> tuple[dict[str, Any], ...]:
        return self._book.output_checks_for_step(step_id)

    def _reused_patterns(self, row: Mapping[str, Any]) -> tuple[re.Pattern[str], ...]:
        """`reuse`가 적힌 행은 다른 행의 조건을 **가져다 씀** — 같은 조건을 두 번 적지 않음."""
        out: list[re.Pattern[str]] = []
        for other in row.get("reuse", ()):
            out.extend(self._patterns.get(str(other), ()))
        return tuple(out)

    def _resolve_labels(
        self, row: Mapping[str, Any], labels: Mapping[str, Sequence[str]] | None
    ) -> tuple[str, ...]:
        if row.get("labels"):
            return tuple(row["labels"])
        source = row.get("labels_from")
        if source and labels:
            return tuple(labels.get(str(source), ()))
        for other in row.get("reuse", ()):
            other_row = self._book.output_check(str(other))
            resolved = self._resolve_labels(other_row, labels)
            if resolved:
                return resolved
        return ()

    def _apply_named_mask(self, mask_row: Mapping[str, Any], value: Any) -> Any:
        from .masking import MASK_METHODS

        return MASK_METHODS[str(mask_row["method"])](value, self._masker.params)

    def _decision(
        self,
        row: Mapping[str, Any],
        bind: Mapping[str, Any],
        step_id: str,
        target: str,
    ) -> BlockDecision:
        rule_id = str(bind.get("block_rule") or "")
        if rule_id:
            block = self._book.block_rule(rule_id)
            return BlockDecision(
                rule_id=rule_id,
                action=str(row["action"]),
                point="output",
                signal=str(block["signal"]),
                notify=tuple(block.get("notify", ())),
                step_id=step_id,
                detail={"field": target, "check": str(row["id"])},
            )
        return BlockDecision(
            rule_id=str(row["id"]),
            action=str(row["action"]),
            point="output",
            signal=str(row["action"]),
            step_id=step_id,
            detail={"field": target, "check": str(row["id"])},
        )
