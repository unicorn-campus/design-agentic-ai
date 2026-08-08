"""검사 규칙 원본을 읽는 유일한 자리.

규칙 조건은 이 모듈이 읽는 설정 파일 1벌에만 있음. 코드 어디에도 조건을 흩어 놓지 않음.
규칙을 못 읽으면 **프로그램이 뜨는 시점에** 실패함 — 검사 없이 도는 상태를 만들지 않음.
"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

__all__ = [
    "RuleBook",
    "RuleBookInvalid",
    "RULES_PATH_ENV",
    "default_rules_path",
    "load_rulebook",
    "get_rulebook",
    "reset_rulebook_cache",
]

RULES_PATH_ENV = "LUNCHPICK_GUARDRAIL_RULES_FILE"
"""설정 파일 자리를 갈아 끼울 환경변수. 값이 없으면 공통 모듈 루트의 기본 파일을 씀."""

_DEFAULT_FILENAME = "guardrail_rules.toml"

# 설정 파일이 가진 배열 이름 → `counts` 표의 어느 칸과 맞춰야 하나
_ROW_COUNT_KEYS: dict[str, str] = {
    "block_rule": "block_rule",
    "output_check": "output_check",
    "input_check": "input_check",
    "mask_rule": "mask_rule",
    "approval_tool": "approval_tool",
    "record_point": "record_point",
}

# 사람 승인·확인이 필요한 방식 이름. `기본은 거부`의 대상임
HUMAN_GATE_MODES = frozenset({"human_approval", "human_confirm"})
# 승인을 붙이면 규제가 요구한 기록이 막히는 방식(⑥ 3-2절 7 · 15번)
REGULATED_NO_GATE = "regulated_no_gate"


class RuleBookInvalid(RuntimeError):
    """검사 규칙 원본을 못 읽었거나 ⑥과 행 수가 어긋남. 뜨는 시점에 이걸 던짐."""


def default_rules_path() -> Path:
    """공통 모듈 루트(`common/`)에 있는 규칙 파일 자리."""
    return Path(__file__).resolve().parent.parent / _DEFAULT_FILENAME


@dataclass(frozen=True, slots=True)
class RuleBook:
    """설계서 ⑥ 행과 1:1로 대응하는 규칙 묶음. 이 객체가 규칙의 유일한 원본임."""

    path: Path
    raw: dict[str, Any]

    # --- ⑥ 행 묶음 ---------------------------------------------------------
    @property
    def block_rules(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["block_rule"])

    @property
    def output_checks(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["output_check"])

    @property
    def input_checks(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["input_check"])

    @property
    def mask_rules(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["mask_rule"])

    @property
    def approval_tools(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["approval_tool"])

    @property
    def record_points(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["record_point"])

    @property
    def boundary_forbidden(self) -> tuple[dict[str, Any], ...]:
        return tuple(self.raw["boundary_forbidden"])

    # --- 인용값 ------------------------------------------------------------
    @property
    def counts(self) -> dict[str, int]:
        return dict(self.raw["counts"])

    @property
    def pattern_steps(self) -> tuple[str, ...]:
        return tuple(self.raw["pattern"]["steps"])

    @property
    def retry_layers(self) -> tuple[str, ...]:
        return tuple(self.raw["pattern"]["retry_layers"])

    @property
    def external_text(self) -> dict[str, str]:
        return dict(self.raw["external_text"])

    @property
    def cost(self) -> dict[str, Any]:
        return dict(self.raw["cost"])

    @property
    def retention(self) -> dict[str, Any]:
        return dict(self.raw["retention"])

    @property
    def answers(self) -> dict[str, Any]:
        return dict(self.raw["answers"])

    def binding(self, group: str, row_id: str) -> dict[str, Any]:
        """검사 1행이 어느 칸을 보고 어느 차단 규칙으로 되돌아가나. 코드에 박지 않고 설정에서 읽음."""
        return dict(self.raw.get("binding", {}).get(group, {}).get(row_id, {}))

    @property
    def verification_state(self) -> str:
        return str(self.raw["verification_state"])

    # --- 찾아 쓰는 함수 ----------------------------------------------------
    def block_rule(self, rule_id: str) -> dict[str, Any]:
        return self._one(self.block_rules, rule_id, "차단 규칙")

    def output_check(self, check_id: str) -> dict[str, Any]:
        return self._one(self.output_checks, check_id, "출력측 검사")

    def input_check(self, check_id: str) -> dict[str, Any]:
        return self._one(self.input_checks, check_id, "입력측 검사")

    def mask_rule(self, rule_id: str) -> dict[str, Any]:
        return self._one(self.mask_rules, rule_id, "마스킹")

    def approval_tool(self, tool_id: str) -> dict[str, Any] | None:
        """도구 판정 행. **없으면 None** — 부르는 쪽이 기본 거부로 다룸."""
        for row in self.approval_tools:
            if row["id"] == tool_id:
                return row
        return None

    def record_point(self, point_id: str) -> dict[str, Any]:
        return self._one(self.record_points, point_id, "관측 기록 지점")

    def block_rules_by_signal(self, signal: str) -> tuple[dict[str, Any], ...]:
        return tuple(row for row in self.block_rules if row["signal"] == signal)

    def input_checks_for_step(self, step_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(
            row
            for row in self.input_checks
            if row.get("all_steps", False) or step_id in row.get("steps", [])
        )

    def output_checks_for_step(self, step_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(row for row in self.output_checks if step_id in row.get("steps", []))

    def record_points_for_step(self, step_id: str) -> tuple[dict[str, Any], ...]:
        return tuple(row for row in self.record_points if step_id in row.get("steps", []))

    def human_gate_tools(self) -> tuple[dict[str, Any], ...]:
        """사람 승인·확인 필수로 판정된 도구만. ⑥ 3-2절 결론의 3종에 해당함."""
        return tuple(row for row in self.approval_tools if row["mode"] in HUMAN_GATE_MODES)

    def guarded_tools(self) -> tuple[dict[str, Any], ...]:
        return tuple(row for row in self.approval_tools if row["mode"] == "guarded")

    def regulated_tools(self) -> tuple[dict[str, Any], ...]:
        return tuple(row for row in self.approval_tools if row["mode"] == REGULATED_NO_GATE)

    def unconfirmed_rows(self) -> tuple[tuple[str, str], tuple[str, str], ...] | tuple:
        """`unconfirmed` 칸이 채워진 행 전부. README `[확인필요]` 목록과 대조하는 데 씀."""
        found: list[tuple[str, str]] = []
        for group in (
            self.input_checks,
            self.output_checks,
            self.mask_rules,
            self.approval_tools,
            self.block_rules,
        ):
            for row in group:
                if row.get("unconfirmed"):
                    found.append((str(row["id"]), str(row["unconfirmed"])))
        for name, table in (("cost", self.cost), ("retention", self.retention)):
            for key, value in table.items():
                if isinstance(value, str) and ("[확인필요" in value or key == "unconfirmed"):
                    found.append((f"{name}.{key}", value))
        return tuple(found)

    @staticmethod
    def _one(rows: tuple[dict[str, Any], ...], row_id: str, kind: str) -> dict[str, Any]:
        for row in rows:
            if row["id"] == row_id:
                return row
        raise RuleBookInvalid(f"{kind} 행 {row_id}이 검사 규칙 원본에 없음")


def _validate(raw: dict[str, Any], path: Path) -> None:
    counts = raw.get("counts")
    if not isinstance(counts, dict):
        raise RuleBookInvalid(f"{path}에 `[counts]` 대조표가 없음")

    for array_key, count_key in _ROW_COUNT_KEYS.items():
        rows = raw.get(array_key)
        if not isinstance(rows, list) or not rows:
            raise RuleBookInvalid(f"{path}의 `{array_key}` 배열이 없거나 비었음")
        expected = counts.get(count_key)
        if expected is None:
            raise RuleBookInvalid(f"`counts.{count_key}`가 없어 ⑥과 행 수를 대조할 수 없음")
        if len(rows) != expected:
            raise RuleBookInvalid(
                f"`{array_key}` 행 수 {len(rows)}개가 `counts.{count_key}` {expected}개와 다름 —"
                " ⑥과 1:1 대응이 깨졌으므로 시작하지 않음"
            )
        ids = [row.get("id") for row in rows]
        if len(set(ids)) != len(ids):
            raise RuleBookInvalid(f"`{array_key}`에 같은 식별자가 두 번 있음 — 규칙 원본이 두 벌이 됨")
        if any(not isinstance(row_id, str) or not row_id for row_id in ids):
            raise RuleBookInvalid(f"`{array_key}`에 식별자가 빈 행이 있음")

    steps = raw.get("pattern", {}).get("steps")
    if not isinstance(steps, list):
        raise RuleBookInvalid(f"{path}에 `[pattern].steps`(③ 단계 목록)가 없음")
    if len(set(steps)) != len(steps):
        raise RuleBookInvalid("③ 단계 목록에 같은 단계가 두 번 있음")
    if len(steps) != counts.get("pattern_step"):
        raise RuleBookInvalid(
            f"③ 단계 목록 {len(steps)}개가 `counts.pattern_step` {counts.get('pattern_step')}개와 다름"
        )

    human = [row for row in raw["approval_tool"] if row.get("mode") in HUMAN_GATE_MODES]
    if len(human) != counts.get("human_gate_tool"):
        raise RuleBookInvalid(
            f"사람 승인·확인 필수 도구 {len(human)}종이"
            f" `counts.human_gate_tool` {counts.get('human_gate_tool')}종과 다름"
        )

    design_rows = raw.get("boundary_forbidden_design_rows")
    if not isinstance(design_rows, list) or len(design_rows) != counts.get("boundary_forbidden"):
        raise RuleBookInvalid("② 경계 미통과 항목의 원표 행 수가 `counts.boundary_forbidden`과 다름")

    # 규칙 원본이 두 벌이 되지 않게 — 차단 규칙의 `signal`은 규칙마다 1개씩만 씀
    signals = [row["signal"] for row in raw["block_rule"]]
    if len(set(signals)) != len(signals):
        dupes = sorted({s for s in signals if signals.count(s) > 1})
        raise RuleBookInvalid(f"같은 조건이 두 차단 규칙에 정의됨: {dupes}")

    for row in raw["mask_rule"]:
        if not row.get("paths"):
            raise RuleBookInvalid(f"마스킹 {row['id']}에 적용 경로가 없음")

    for row in raw["output_check"]:
        kinds = row.get("kinds") or []
        if not kinds:
            raise RuleBookInvalid(f"출력측 검사 {row['id']}에 검사 방식이 없음")


def load_rulebook(path: str | os.PathLike[str] | None = None) -> RuleBook:
    """규칙 원본을 읽음. 못 읽거나 ⑥과 행 수가 어긋나면 여기서 바로 실패함."""
    target = Path(path) if path is not None else Path(os.environ.get(RULES_PATH_ENV) or default_rules_path())
    try:
        raw = tomllib.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuleBookInvalid(f"검사 규칙 원본을 찾지 못했음: {target}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise RuleBookInvalid(f"검사 규칙 원본을 해석하지 못했음: {target} — {exc}") from exc
    _validate(raw, target)
    return RuleBook(path=target, raw=raw)


@lru_cache(maxsize=1)
def get_rulebook() -> RuleBook:
    return load_rulebook()


def reset_rulebook_cache() -> None:
    get_rulebook.cache_clear()


if __name__ == "__main__":
    book = load_rulebook()
    print(
        f"검사 규칙 원본 확인 통과 — {book.path.name}"
        f" · 차단 {len(book.block_rules)}행"
        f" · 출력검사 {len(book.output_checks)}행"
        f" · 입력검사 {len(book.input_checks)}행"
        f" · 마스킹 {len(book.mask_rules)}행"
        f" · 승인 지점 {len(book.approval_tools)}행(사람 게이트 {len(book.human_gate_tools())}종)"
        f" · 기록 지점 {len(book.record_points)}행"
        f" · ③ 단계 {len(book.pattern_steps)}개"
    )
