"""④ 9절 타임아웃·재시도 표를 코드로 옮긴 것. **값의 단일 출처는 ④임.**

⑥은 이 값을 참조만 하고 고치지 않음(④ 9절 머리말 · G-4).
`p95 배정값`과 `타임아웃(상한)`을 두 열로 나눈 3판 구조를 그대로 유지함(D-9).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StepBudget:
    """한 단계의 예산. ④ 9-1절 표의 한 행."""

    step: str
    p95_ms: int
    timeout_ms: int
    retries: int
    parallel: bool = False

    @property
    def worst_ms(self) -> int:
        """최악값 = 타임아웃 × (1 + 재시도) — ④ 9절 머리말."""
        return self.timeout_ms * (1 + self.retries)


# ── S-R 동기 요청: 총 예산 3,000ms (① 4절 Q-1 · US:NFR-SYS-010) ──────────────
SR_TOTAL_BUDGET_MS = 3_000

SR: dict[str, StepBudget] = {
    "S-R1": StepBudget("S-R1 게이트웨이 수신·인증", 50, 100, 0),
    "S-R2": StepBudget("S-R2 동의 상태 확인", 20, 50, 0),
    "S-R3": StepBudget("S-R3 회원·취향·식이제한 조회", 100, 200, 0),
    "S-R4": StepBudget("S-R4 이력 조회", 150, 300, 0),
    # S-R5는 J-6으로 캐시(DB4) 조회가 됨 → 재시도 0회(D-4)
    "S-R5": StepBudget("S-R5 반경 후보 조회(캐시 DB4)", 200, 400, 0, parallel=True),
    "S-R6": StepBudget("S-R6 날씨 조회(C-3)", 200, 400, 1, parallel=True),
    "S-R7": StepBudget("S-R7 낱말 코드 고정", 50, 100, 0),
    "S-R8": StepBudget("S-R8 하드필터 적용", 150, 300, 0),
    "S-R9": StepBudget("S-R9 사전 조건 확인", 10, 20, 0),
    # S-R10 재시도 0회 — 재시도 대신 폴백으로 감(④ 9-1절 주석)
    # ⚠️ 이 칸이 ④ 9-1절의 `[확인필요: 실측]`이며 **실측 결과 배정값이 틀렸음**.
    #    아래 `SR10_MEASURED_MS` 참조. 값은 ④ 소유이므로 여기서 고치지 않고
    #    실측치를 나란히 두고 환경변수로만 덮어쓸 수 있게 함(G-4).
    "S-R10": StepBudget("S-R10 근거·스코어 생성(C-1)", 900, 1_200, 0),
    "S-R11": StepBudget("S-R11 확신 스코어 임계값 검증", 20, 50, 0),
    "S-R12": StepBudget("S-R12 추천 이력·원시 컨텍스트 저장", 100, 200, 0),
    "S-R13": StepBudget("S-R13 응답 직렬화·전송", 50, 100, 0),
}

# 폴백 조립 시간 — `[확인필요: C-1 폴백 조립 시간 실측]`. 0으로 두지 않음(D-2)
FALLBACK_ASSEMBLE_MS = 150

# ── S-B 배치 · S-E 이벤트 (④ 9-2절) ─────────────────────────────────────────
SB: dict[str, StepBudget] = {
    "S-B1": StepBudget("S-B1 배치 기동", 0, 10_000, 0),
    "S-B2": StepBudget("S-B2 전일 피드백 조회", 0, 300_000, 1),
    "S-B3": StepBudget("S-B3 취향 벡터 갱신(회원 1명)", 0, 200, 0),
    "S-B4": StepBudget("S-B4 선호 점수 배열 적재", 0, 100, 0),
    "S-B5": StepBudget("S-B5 추천 품질 자가 검증", 0, 100, 0),
    "S-B6": StepBudget("S-B6 학습 반영 메시지 조립", 0, 50, 0),
    "S-B7": StepBudget("S-B7 콜드스타트 안전망 유지 판정", 0, 50, 0),
    "S-B8": StepBudget("S-B8 완료 보고", 0, 10_000, 0),
    "S-B9": StepBudget("S-B9 동기화 기동", 0, 10_000, 0),
    "S-B10": StepBudget("S-B10 대상 지역 식당 조회(C-2)", 0, 10_000, 1),
    "S-B11": StepBudget("S-B11 적재 전 내용 검사", 0, 100, 0),
    "S-B12": StepBudget("S-B12 폐업·영업 상태 필터", 0, 50, 0),
    "S-B13": StepBudget("S-B13 캐시 적재", 0, 200, 1),
    "S-B14": StepBudget("S-B14 신선도 상한 초과 만료", 0, 300_000, 0),
    "S-B15": StepBudget("S-B15 동기화 완료 보고", 0, 10_000, 0),
}

SE: dict[str, StepBudget] = {
    "S-E1": StepBudget("S-E1 원탭 기록", 0, 200, 0),
    "S-E2": StepBudget("S-E2 중복·시간대 검증", 0, 50, 0),
    "S-E3": StepBudget("S-E3 피드백 요청 표시", 0, 100, 0),
    "S-E4": StepBudget("S-E4 피드백 제출·검증", 0, 200, 0),
    "S-E5": StepBudget("S-E5 피드백·스냅샷 적재", 0, 300, 1),
    # 원문이 "리마인더 1회만(강제 아님)"으로 못 박아 재시도 0회(④ 9-2절)
    "S-E6": StepBudget("S-E6 리마인더 푸시(C-6)", 0, 3_000, 0),
}


def sr_p95_total_ms() -> int:
    """① p95 처리 합계 — 병렬 구간은 최댓값 1건만 셈(가이드 4절)."""
    serial = sum(b.p95_ms for b in SR.values() if not b.parallel)
    parallel_max = max(b.p95_ms for b in SR.values() if b.parallel)
    return serial + parallel_max


def sr_worst_total_ms() -> int:
    """② 최악값 합계 — 타임아웃 × (1+재시도), 병렬은 최댓값 1건만."""
    serial = sum(b.worst_ms for b in SR.values() if not b.parallel)
    parallel_max = max(b.worst_ms for b in SR.values() if b.parallel)
    return serial + parallel_max


# ── `[확인필요: 실측]`에 대한 실측 결과 (2026-08-06 · 로컬 컨테이너 → Claude API) ──
# 측정 조건: claude-sonnet-5 · thinking=disabled · effort=low · max_tokens=1024 ·
#            후보 12건 · 입력 819토큰 / 출력 약 230토큰 · 5회 반복
# 결과: 최소 4,955ms · 중앙 5,022ms · 최대 5,222ms
#
# **④ 9-1절 배정값(p95 900ms · 타임아웃 1,200ms)이 실측과 4 ~ 5배 어긋남.**
# 배정값을 그대로 두면 C-1이 매번 타임아웃해 L-2 경로 폴백이 **항상** 발동함
# (= 근거 문장이 늘 거리·평점 기본 문구가 됨 → ① Q-2 설명가능성이 무너짐).
# 반대로 실측치를 그대로 쓰면 p95 합계가 1,800 → 약 5,900ms가 되어
# **① Q-1 `p95 3초`가 성립하지 않음.**
#
# 이 파일은 값을 고치지 않음 — 타임아웃 값의 주인은 ④임(④ 9절 머리말 · G-4).
# 실측치를 기록하고, 로컬에서 실물 경로를 태워 보려면 환경변수로만 덮게 함.
SR10_MEASURED_MS = 5_222
SR10_MEASUREMENT_NOTE = (
    "2026-08-06 실측 p95 약 5.2초. ④ 9-1절 배정값 1,200ms의 4배 이상이며 "
    "① Q-1 p95 3초와 양립하지 않음. ④·①로 되돌려야 하는 값임."
)


def timeout_sec(step: str) -> float:
    """단계 식별자로 타임아웃 상한을 초 단위로 가져옴.

    `S-R10`만 `LP_SR10_TIMEOUT_MS`로 덮을 수 있음. 기본값은 **④ 설계값**이며,
    덮어쓰면 ① Q-1이 깨진다는 사실이 로그로 드러나게 해 둠.
    """
    import os

    if step == "S-R10":
        override = os.environ.get("LP_SR10_TIMEOUT_MS")
        if override:
            return int(override) / 1000.0
    for table in (SR, SB, SE):
        if step in table:
            return table[step].timeout_ms / 1000.0
    raise KeyError(f"④ 9절 타임아웃 표에 없는 단계임: {step}")


def sr10_override_ms() -> int | None:
    """설계값을 덮어썼는지 알려 줌. 관측 기록에 남겨 사실을 숨기지 않음."""
    import os

    raw = os.environ.get("LP_SR10_TIMEOUT_MS")
    return int(raw) if raw else None


# ── ④ 10절 반복 상한 ────────────────────────────────────────────────────────
# 상한 숫자는 원문에 없음 → `[확인필요: 개별 거절 반복 상한]` ·
# `[확인필요: 전체 새로고침 상한]`. 지어내지 않고 환경변수로 빼고 기본값을 밝힘.
DEFAULT_MAX_REJECT_ITER = 3  # L-1 · 임시 기본값(원문 부재)
DEFAULT_MAX_REFRESH_ITER = 2  # L-2 · 임시 기본값(원문 부재) — 요청당 모델 호출 = 1 + 이 값

# ⑥ G-3 요청당 모델 호출 상한 — L-2 상한에서 파생됨
def llm_call_cap(max_refresh_iter: int) -> int:
    return 1 + max_refresh_iter
