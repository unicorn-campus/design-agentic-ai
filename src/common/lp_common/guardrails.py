"""입력측 가드레일 — ⑥ 10절 G-1(ASI01 목표 탈취) · G-2(ASI06 기억·문맥 오염).

**규칙은 한 벌만 둠.** ⑥ 10-1절은 같은 규칙을 두 지점에 건다고 적었음 —
`S-B11` 적재 전(근본 · 주 방어선)과 `S-R5` 읽기 시점(잔여 · 얕게).
규칙을 두 벌 두면 두 지점이 조용히 갈라지므로 공용 패키지에 두고
I-2(추천)와 I-5(동기화 워커)가 같은 함수를 부름.

두 곳에 다 거는 이유 2가지(⑥ 10-1절):
  ① `S-B11` 도입 **전에 이미 적재된 값**이 캐시에 남아 있음 —
     `S-B14` 만료가 한 바퀴 돌기까지는 옛 값이 읽힘
  ② 검사 규칙이 바뀌면 규칙 갱신 전 적재분이 그대로 통과함
"""

from __future__ import annotations

import re
from typing import Any

# G-1 — 외부에서 온 글에 섞인 지시 유도 문구.
# 외부에서 온 글은 **데이터로만 취급하고 지시로 실행하지 않음**(⑥ 10절 G-1).
_INSTRUCTION_PATTERNS = [
    re.compile(r"(?i)\b(system|assistant|user)\s*:"),
    re.compile(r"(?i)(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above)"),
    re.compile(r"이전\s*지시|앞의?\s*지시|무시하[고라]|건너뛰(겠|어|고)"),
    re.compile(r"\[/?(SYSTEM|INST|PROMPT)\]", re.IGNORECASE),
    re.compile(r"(?i)</?(system|instructions?)>"),
]
# 제어문자 — 프롬프트 구조를 깨는 데 쓰임
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def inspect_external_string(value: str, *, max_len: int) -> tuple[str, list[str]]:
    """`S-B11` 적재 전 내용 검사 — ⑥ G-2의 **근본 차단 지점**.

    한 번 걸러 두면 이후 모든 요청이 안전하고 매 요청 검사 비용이 빠짐
    (⑥ 10-1절). 걸리면 적재하지 않고 차단 기록을 남김(B-9).

    Returns:
        (정제된 문자열, 위반 사유 목록). 위반이 있으면 호출 쪽이 **적재 제외**함.
    """
    violations: list[str] = []
    cleaned = value

    if _CONTROL_CHARS.search(cleaned):
        violations.append("G-2:control_char")
        cleaned = _CONTROL_CHARS.sub("", cleaned)
    if "\n" in cleaned or "\r" in cleaned:
        violations.append("G-2:newline")
        cleaned = cleaned.replace("\r", " ").replace("\n", " ")
    if len(cleaned) > max_len:
        # `[확인필요: 표시명 길이 상한]` — 숫자는 원문에 없어 설정값으로 둠
        violations.append("G-1:length_over")
        cleaned = cleaned[:max_len]
    for pattern in _INSTRUCTION_PATTERNS:
        if pattern.search(cleaned):
            violations.append("G-1:instruction_injection")
            break

    return cleaned.strip(), violations


def shallow_read_check(value: str, *, max_len: int) -> tuple[str, bool]:
    """`S-R5` 읽기 시점 **잔여** 검사 — 길이 상한과 제어문자만 얕게 봄.

    문구 검사는 하지 않음. 3초 예산에서 `S-R5` 상한이 400ms뿐이라 깊은
    검사를 넣을 수 없기 때문임(⑥ 10-1절 표).
    """
    changed = False
    out = value
    if _CONTROL_CHARS.search(out) or "\n" in out or "\r" in out:
        out = _CONTROL_CHARS.sub("", out).replace("\r", " ").replace("\n", " ")
        changed = True
    if len(out) > max_len:
        out = out[:max_len]
        changed = True
    return out.strip(), changed


def block_low_confidence(
    picks: list[dict[str, Any]], *, threshold: float
) -> tuple[list[dict[str, Any]], int]:
    """B-5 확신 스코어 임계값 미달 카드 — 노출하지 않음.

    강도는 **권고**임. `ES:02#추천생성`이 "최소 임계값 이상만 노출"을
    요구하나 **임계값 숫자가 원문에 없어**(④ `[확인필요: 확신 스코어 임계값]`)
    필수로 걸 수 없음(⑥ 9절 각주 5).
    """
    kept = [p for p in picks if float(p.get("confidence", 0)) >= threshold]
    return kept, len(picks) - len(kept)


def is_fresh(collected_at: Any, now: Any, *, max_age_sec: int) -> bool:
    """S-B14 신선도 상한 — 초과분은 만료 처리함(⑥ G-2).

    J-6이 만든 새 위험: 요청 경로가 캐시만 읽으므로 **캐시 신선도가 곧
    폐업 오류의 수명**임(⑦ 4-2-1절). 주기 값은 ⑤ `[확인필요]`에 걸려 있음.
    """
    return (now - collected_at).total_seconds() <= max_age_sec
