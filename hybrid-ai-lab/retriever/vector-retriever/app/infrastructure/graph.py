"""S-R1 ~ S-R9 단계를 LangGraph StateGraph로 묶어 실행하는 워크플로우 어댑터임.

단계 로직은 application(steps.py)에 있고 여기서는 '어떤 순서로·어디로 갈라지는가'만 조립함.
설계서 ① 흐름 유형의 분기 6곳·반복 2곳은 state.ROUTES 표 하나로만 표현해, 그래프 코드가 설계 표와 1:1로 읽히게 둠.
"""

from __future__ import annotations

from typing import Any, Mapping

from langgraph.errors import GraphRecursionError
from langgraph.graph import END, START, StateGraph

from app.application.ports import RetrieverWorkflowPort
from app.application.state import (
    ALL_NODES,
    NODE_END,
    NODE_S_R1,
    ROUTES,
    RetrieverState,
)
from app.application.steps import RetrieverSteps

# 한 요청이 지날 수 있는 최장 걸음(super-step) 수 = 34걸음. 병렬 구간이 없어 노드 1개 실행 = 1걸음임.
#   S-R1 1 + S-R2 1
#   + L-1 24 = S-R3 진입 6회(회전 상한) × 최악 4걸음(S-R3 → S-R6 → S-R4 → S-R5)
#   + 7번째 S-R3 진입 1(LLM 없이 수집 종료, 설계 ④)
#   + L-2 6 = 답변 시도 3회(최초 1 + 재작성 2) × 2걸음(S-R7 → S-R8)
#   + S-R9 1
# 기본값 60은 34걸음의 약 1.8배 여유임. 설계 ④의 상한 장치가 먼저 걸리므로 이 값에 닿으면 상한 장치 결함으로 봄.
DEFAULT_RECURSION_LIMIT = 60


class LangGraphWorkflow(RetrieverWorkflowPort):
    """RetrieverSteps를 LangGraph StateGraph로 실행하는 어댑터임.

    LangGraph import는 이 계층에만 둠(계층 가이드 §5.5). 단계·규칙은 포트를 통해서만 부름.
    체크포인터를 붙이지 않음 — 동기 요청 1회 응답이라 중단 후 재개가 없고(재개방안 해당없음),
    그 덕에 상태에 색인 객체처럼 직렬화할 수 없는 값을 그대로 담을 수 있음.
    """

    def __init__(self, steps: RetrieverSteps, *, recursion_limit: int = DEFAULT_RECURSION_LIMIT) -> None:
        """단계 묶음을 받아 그래프를 조립하고 컴파일함.

        인자: recursion_limit은 비정상 반복을 끊는 마지막 안전장치이며 기본 60걸음임(위 계산 근거 참조).
        예외: ROUTES 표에 없는 노드가 ALL_NODES에 있으면 KeyError를 발생시킴(조립 시점에 바로 드러냄).
        부수효과: 없음(그래프 조립만 함. 단계 실행은 run에서 함).
        """

        self.steps = steps
        self.recursion_limit = int(recursion_limit)
        self._graph = self._build(steps)

    @staticmethod
    def _build(steps: RetrieverSteps) -> Any:
        """ALL_NODES·ROUTES 표를 그대로 그래프로 옮겨 컴파일한 결과를 반환함.

        방법: 노드마다 steps.node(이름)을 붙이고, 갈 수 있는 다음 노드를 path map으로 제한함.
        path map을 ROUTES로 좁혀 두면 단계가 표에 없는 노드를 route로 내놓는 순간 실행이 바로 실패함(설계와 코드 불일치 조기 발견).
        """

        builder = StateGraph(RetrieverState)
        for name in ALL_NODES:
            builder.add_node(name, steps.node(name))
        builder.add_edge(START, NODE_S_R1)
        for name in ALL_NODES:
            targets = ROUTES[name]
            if targets == (NODE_END,):
                # S-R9 결과 응답은 분기가 없는 유일한 단계임
                builder.add_edge(name, END)
                continue
            builder.add_conditional_edges(name, steps.route, {target: target for target in targets})
        return builder.compile()

    def run(self, state: Mapping[str, Any]) -> dict[str, Any]:
        """초기 상태로 S-R9까지 실행하고 최종 상태를 반환함.

        인자: state는 RetrieverService.initial_state가 만든 초기 RetrieverState임.
        반환값: S-R9가 채운 response 키를 가진 최종 상태 dict임.
        예외: 걸음 수 상한을 넘으면 RuntimeError로 바꿔 올림 — 호출자는 LangGraph 예외 형을 몰라도 됨.
        부수효과: 단계가 부르는 포트의 부수효과(LLM 호출·감사 로그 기록)를 그대로 가짐.
        """

        try:
            final = self._graph.invoke(dict(state), config={"recursion_limit": self.recursion_limit})
        except GraphRecursionError as error:
            raise RuntimeError(
                f"워크플로우 걸음 수가 상한({self.recursion_limit})을 넘었습니다. "
                "설계 ④ 상한 장치(회전 6회·재작성 2회·LLM 16회)가 동작하지 않았습니다."
            ) from error
        return dict(final)
