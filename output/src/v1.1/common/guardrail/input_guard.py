"""입력측 검사 — 바깥에서 온 글은 데이터일 뿐임.

바깥에서 받은 문자열(사용자 입력 · 커넥터 응답 · 저장해 둔 값 전부)은 **데이터로만** 다룸.
프롬프트에 넣을 때 `wrap_external_text()` **1개 함수만** 씀. 경로마다 따로 조립하지 않음.
태그 흉내를 내는 문자열이 들어와도 경계가 깨지지 않게 먼저 무력화함.

검사 조건·보는 칸·되돌아갈 차단 규칙은 전부 설정 파일에서 읽음. 이 파일에 조건이 없음.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from .errors import BlockDecision, GuardrailBlocked
from .masking import MaskPath, Masker, get_masker
from .rules import RuleBook, get_rulebook

__all__ = [
    "wrap_external_text",
    "neutralize_tag_lookalikes",
    "InputVerdict",
    "InputGuard",
]

# 꺾쇠를 닮은 글자로 바꿔 태그 흉내를 못 내게 함. 바꾼 뒤에 우리 태그를 붙이므로 경계가 깨지지 않음
_ANGLE_OPEN = "‹"
_ANGLE_CLOSE = "›"


def neutralize_tag_lookalikes(text: str) -> str:
    """꺾쇠를 바꿔 태그 흉내를 무력화함. 글자 수는 그대로 둠(원문 길이를 속이지 않음)."""
    return str(text).replace("<", _ANGLE_OPEN).replace(">", _ANGLE_CLOSE)


def wrap_external_text(source: str, text: str, *, book: RuleBook | None = None) -> str:
    """바깥에서 받은 글을 프롬프트에 넣는 **유일한** 방법.

    태그로 감싸고 지시로 실행하지 않는다는 문구를 병기함. 태그 이름과 문구는 설정 파일이 가짐.
    """
    rules = (book or get_rulebook()).external_text
    tag = rules["tag"]
    return (
        f'<{tag} source="{neutralize_tag_lookalikes(source)}">\n'
        f"{neutralize_tag_lookalikes(text)}\n"
        f"</{tag}>\n"
        f"{rules['notice']}"
    )


@dataclass(frozen=True, slots=True)
class InputVerdict:
    """입력측 판정 1건."""

    step_id: str
    passed: bool
    kept: dict[str, Any] = field(default_factory=dict)
    dropped_fields: tuple[str, ...] = ()
    """② 경계 미통과 항목이거나 화이트리스트 밖이어서 **받지 않고 버린** 칸."""
    tripped: tuple[BlockDecision, ...] = ()
    checks_run: tuple[str, ...] = ()
    checks_disabled: tuple[str, ...] = ()
    """`[확인필요]`로 목록·패턴이 비어 미가동인 검사."""


class InputGuard:
    """⑥ 4절 I-1 ~ I-14와 ② 경계 미통과 항목을 한 자리에서 판정함."""

    def __init__(self, book: RuleBook | None = None, masker: Masker | None = None) -> None:
        self._book = book or get_rulebook()
        self._masker = masker or get_masker(self._book)
        self._patterns: dict[str, tuple[re.Pattern[str], ...]] = {
            str(row["id"]): tuple(re.compile(p) for p in (row.get("patterns") or []))
            for row in self._book.input_checks
        }

    # --- ② 경계 미통과 항목 -------------------------------------------------
    def forbidden_fields(self, boundary: str | None = None) -> frozenset[str]:
        rows = self._book.boundary_forbidden
        if boundary is None:
            return frozenset(str(row["field"]) for row in rows)
        return frozenset(str(row["field"]) for row in rows if boundary in row.get("boundary", []))

    def drop_boundary_forbidden(
        self, payload: Mapping[str, Any], boundary: str
    ) -> tuple[dict[str, Any], tuple[str, ...]]:
        """경계를 넘기지 않기로 한 칸은 **가려서 넘기지 않고 버림**."""
        banned = self.forbidden_fields(boundary) | self.forbidden_fields("internal")
        kept = {k: v for k, v in payload.items() if k not in banned}
        dropped = tuple(sorted(k for k in payload if k in banned))
        return kept, dropped

    # --- I-n 검사 ----------------------------------------------------------
    def inspect(
        self,
        step_id: str,
        payload: Mapping[str, Any],
        *,
        boundary: str | None = None,
        raise_on_block: bool = False,
    ) -> InputVerdict:
        working = dict(payload)
        dropped: list[str] = []
        if boundary is not None:
            working, boundary_dropped = self.drop_boundary_forbidden(working, boundary)
            dropped.extend(boundary_dropped)

        tripped: list[BlockDecision] = []
        ran: list[str] = []
        disabled: list[str] = []

        rows = self._book.input_checks_for_step(step_id)
        # 방식 순서를 못 박음 — **패턴 → 라벨 목록 → 필드 지정**.
        # 화이트리스트로 칸을 버리는 것이 먼저 돌면 카드번호 같은 적중을 감사 기록에 남기지 못함
        # (`B-20`은 폐기 **+ 감사 기록**을 함께 요구함). 그래서 적중 판정을 앞에 둠.
        for kind in ("pattern", "label_list", "field_spec"):
            for row in rows:
                check_id = str(row["id"])
                if kind not in (row.get("kinds") or []):
                    continue
                if not row.get("enabled", True):
                    disabled.append(check_id)
                    continue
                ran.append(check_id)
                bind = self._book.binding("input", check_id)
                if kind == "pattern":
                    if not self._patterns[check_id]:
                        disabled.append(check_id)
                    else:
                        self._run_pattern(row, bind, working, tripped, step_id)
                elif kind == "label_list":
                    if not (row.get("labels") or row.get("labels_from")):
                        disabled.append(check_id)
                    else:
                        self._run_label_list(row, bind, working, tripped, step_id)
                else:
                    self._run_field_spec(row, bind, working, dropped, tripped, step_id)

        verdict = InputVerdict(
            step_id=step_id,
            passed=not tripped,
            kept=working,
            dropped_fields=tuple(dict.fromkeys(dropped)),
            tripped=tuple(tripped),
            checks_run=tuple(dict.fromkeys(ran)),
            checks_disabled=tuple(dict.fromkeys(disabled)),
        )
        if raise_on_block and tripped:
            raise GuardrailBlocked(tripped[0])
        return verdict

    # --- 방식 3종 ----------------------------------------------------------
    def _run_field_spec(
        self,
        row: Mapping[str, Any],
        bind: Mapping[str, Any],
        working: dict[str, Any],
        dropped: list[str],
        tripped: list[BlockDecision],
        step_id: str,
    ) -> None:
        allowed = set(row.get("allowed_fields") or ())
        # 칸 자체를 만들지 않는 칸이 들어와 있으면 버림
        for key in bind.get("no_slot_fields", ()):
            if key in working:
                working.pop(key)
                dropped.append(key)
        # 화이트리스트 밖 칸은 버림 — 버릴 범위는 설정의 `sibling_fields`가 정함
        for key in bind.get("sibling_fields", ()):
            if key in working and key not in allowed:
                working.pop(key)
                dropped.append(key)
        # 열거값 밖이면 걸림
        enum_values = row.get("enum_values") or ()
        for key in bind.get("enum_fields", ()):
            if key in working and enum_values and working[key] not in enum_values:
                tripped.append(self._decision(row, bind, step_id, key))
        # 비면 중단하는 칸
        for key in bind.get("required_fields", ()):
            if not working.get(key):
                tripped.append(self._decision(row, bind, step_id, key))

    def _run_label_list(
        self,
        row: Mapping[str, Any],
        bind: Mapping[str, Any],
        working: dict[str, Any],
        tripped: list[BlockDecision],
        step_id: str,
    ) -> None:
        labels = row.get("labels") or ()
        if not labels:
            return  # `labels_from`은 부르는 쪽이 값을 넣어 줘야 함 — 지어내지 않음
        for key in bind.get("label_fields", ()):
            value = working.get(key)
            if isinstance(value, str) and value and value not in labels:
                tripped.append(self._decision(row, bind, step_id, key))

    def _run_pattern(
        self,
        row: Mapping[str, Any],
        bind: Mapping[str, Any],
        working: dict[str, Any],
        tripped: list[BlockDecision],
        step_id: str,
    ) -> None:
        patterns = self._patterns[str(row["id"])]
        targets = bind.get("pattern_fields") or [
            k for k, v in working.items() if isinstance(v, str)
        ]
        must_match = bind.get("pattern_mode") == "must_match"  # 형식 검증 — 맞아야 통과함
        for key in targets:
            value = working.get(key)
            if not isinstance(value, str):
                continue
            hit = any(p.search(value) for p in patterns)
            if (must_match and not hit) or (not must_match and hit):
                tripped.append(self._decision(row, bind, step_id, key))
                if row.get("action") == "discard_now_and_audit":
                    working[key] = "[가려짐]"

    # --- 도우미 -----------------------------------------------------------
    def masked_for_record(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        """검사에 걸린 입력을 기록할 때 씀 — 원문은 가려서 기록함."""
        return self._masker.mask_mapping(payload, MaskPath.OBSERVABILITY)

    def _decision(
        self,
        row: Mapping[str, Any],
        bind: Mapping[str, Any],
        step_id: str,
        key: str,
    ) -> BlockDecision:
        rule_id = str(bind.get("block_rule") or "")
        if rule_id:
            block = self._book.block_rule(rule_id)
            return BlockDecision(
                rule_id=rule_id,
                action=str(block["action"]),
                point="input",
                signal=str(block["signal"]),
                notify=tuple(block.get("notify", ())),
                step_id=step_id,
                detail={"field": key, "check": str(row["id"])},
            )
        return BlockDecision(
            rule_id=str(row["id"]),
            action=str(row.get("action", "")),
            point="input",
            signal=str(row.get("action", "")),
            step_id=step_id,
            detail={"field": key, "check": str(row["id"])},
        )
