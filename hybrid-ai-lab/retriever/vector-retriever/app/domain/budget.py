"""남은 시간 예산(설계 ⑥-10)과 반복·호출 상한(설계 ④·③)을 계산하는 규칙임."""

from __future__ import annotations

from dataclasses import dataclass, field

# 단계ID 상수. 그래프 노드 이름과 감사 로그 키로 함께 씀.
S_R1, S_R2, S_R3, S_R4, S_R5, S_R6, S_R7, S_R8, S_R9 = (
    "S-R1", "S-R2", "S-R3", "S-R4", "S-R5", "S-R6", "S-R7", "S-R8", "S-R9",
)

# 커넥터ID 상수(설계 ③ 외부시스템 연동 명세)
C_01, C_02, C_03, C_04 = "C-01", "C-02", "C-03", "C-04"

# 단계를 시작할 때 "앞으로 남은" 외부 연동 목록.
# 설계 ⑥-10: 반복 구간 안 연동은 반복 횟수와 상관없이 1회, 분기는 가장 큰 경로로 셈.
# S-R4 ~ S-R6은 L-1 안이라 다시 S-R3(C-02)·S-R6(C-03)을 지날 수 있고, S-R8은 재작성(S-R7, C-04)으로 갈 수 있음.
_REMAINING_CONNECTORS: dict[str, tuple[str, ...]] = {
    S_R1: (C_01, C_02, C_03, C_04),
    S_R2: (C_01, C_02, C_03, C_04),
    S_R3: (C_02, C_03, C_04),
    S_R4: (C_02, C_03, C_04),
    S_R5: (C_02, C_03, C_04),
    S_R6: (C_02, C_03, C_04),
    S_R7: (C_04,),
    S_R8: (C_04,),
    S_R9: (),
}


@dataclass(frozen=True)
class BudgetPolicy:
    """요청 1건의 시간 예산과 반복·호출 상한 값. 설정에서 읽어 bootstrap이 주입함."""

    total_seconds: float = 30.0  # 총 시간 예산(설계 ⑤)
    closing_seconds: float = 1.5  # S-R9 몫으로 떼어 두는 종료 처리 시간(총 예산의 5%, 설계 가정)
    start_threshold_seconds: float = 1.5  # 단계 시작 기준. 남은 시간 예산이 이 값 미만이면 착지(설계 가정)
    max_turns: int = 6  # L-1 회전 상한. S-R3 진입 횟수로 셈(7번째 진입은 LLM 없이 수집 종료)
    max_llm_calls: int = 16  # 요청당 LLM 호출 상한 = C-01 1 + C-02 6 + C-03 6 + C-04 3
    max_rewrites: int = 2  # L-2 답변 재작성 상한(최초 1 + 재작성 2 = 시도 3회)
    max_sub_questions: int = 3  # S-R2 하위 질문 최대 개수
    max_search_fail_streak: int = 2  # 검색 연속 실패가 이 횟수에 닿으면 즉시 수집 종료
    connector_worst_seconds: dict[str, float] = field(
        default_factory=lambda: {C_01: 2.5, C_02: 1.5, C_03: 1.2, C_04: 2.5}
    )  # 커넥터별 최악값 = 타임아웃 × (재시도 0 + 1)


def remaining_connector_worst(policy: BudgetPolicy, step_id: str, *, generate_answer: bool) -> float:
    """단계 시작 시점부터 남은 외부 연동 최악값의 합을 반환함.

    인자: generate_answer가 거짓이면 C-04(답변 생성)는 남은 경로에 없으므로 뺌.
    반환값: 초 단위 합계임. 알 수 없는 단계ID면 0임.
    """

    total = 0.0
    for connector in _REMAINING_CONNECTORS.get(step_id, ()):
        if connector == C_04 and not generate_answer:
            continue
        total += float(policy.connector_worst_seconds.get(connector, 0.0))
    return total


def remaining_budget(
    policy: BudgetPolicy, *, elapsed_seconds: float, step_id: str, generate_answer: bool
) -> float:
    """설계 ⑥-10의 '남은 시간 예산'을 계산함.

    방법: 총 예산 − 사용 시간 − 종료 처리 시간 − 남은 외부 연동 최악값 합.
    예시(기본값 기준): S-R3 진입, 사용 12초, 답변 켬 → 30 − 12 − 1.5 − (1.5 + 1.2 + 2.5) = 11.3초.
    반환값: 음수일 수 있음. 음수·기준 미만이면 그 단계를 시작하지 않고 착지함.
    """

    remaining = policy.total_seconds - float(elapsed_seconds) - policy.closing_seconds
    return remaining - remaining_connector_worst(policy, step_id, generate_answer=generate_answer)


def can_start(policy: BudgetPolicy, *, elapsed_seconds: float, step_id: str, generate_answer: bool) -> bool:
    """남은 시간 예산이 시작 기준(1.5초) 이상인지 반환함. S-R9는 종료 처리 시간으로 확보해 항상 참임."""

    if step_id == S_R9:
        return True
    budget = remaining_budget(
        policy, elapsed_seconds=elapsed_seconds, step_id=step_id, generate_answer=generate_answer
    )
    return budget >= policy.start_threshold_seconds
