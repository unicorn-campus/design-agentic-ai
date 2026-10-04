"""검색 요청 1건을 워크플로우로 실행하고 표준 응답으로 돌려주는 응용 서비스임."""

from __future__ import annotations

from typing import Any
import uuid

from .models import STATUS_ERROR, SearchRequest, SearchResponse
from .ports import AuditLogPort, ClockPort, IndexProviderPort, RetrieverWorkflowPort
from .state import NODE_S_R1, RetrieverState


class RetrieverService:
    """검색 실행·상태 확인 기능을 제공함.

    실제 단계 실행은 생성자로 주입받은 워크플로우 실행 포트(RetrieverWorkflowPort)에 맡김.
    구현체 생성은 하지 않으며, 조립은 app/bootstrap.py가 담당함.
    """

    def __init__(
        self,
        *,
        workflow: RetrieverWorkflowPort,
        index_provider: IndexProviderPort,
        clock: ClockPort,
        audit_log: AuditLogPort,
    ) -> None:
        """포트를 보관함. 부수효과 없음."""

        self.workflow = workflow
        self.index_provider = index_provider
        self.clock = clock
        self.audit_log = audit_log

    def initial_state(self, request: SearchRequest, role: str | None) -> RetrieverState:
        """요청을 S-R1이 받을 초기 상태로 바꿈.

        인자: role은 표현 계층이 로그인 정보(게이트웨이 헤더·CLI 인자)에서 꺼낸 값임. 본문 값이 아님.
        반환값: 요청ID·시작 시각·기준일을 채운 상태. 값 범위 검사는 S-R1이 함.
        """

        return {
            "request_id": uuid.uuid4().hex,
            "started_at": self.clock.now(),
            "today": self.clock.today().isoformat(),
            "query": request.query,
            "role": role,
            "generate_answer": request.generate_answer,
            "top_k": request.top_k,
            "member_id": request.member_id,
            "llm_calls": 0,
            "turn": 0,
            "timings": {},
            "trace": [],
            "warnings": [],
            "route": NODE_S_R1,
        }

    def execute(self, request: SearchRequest, role: str | None) -> SearchResponse:
        """질문 1건을 처리해 결과 응답 1건을 돌려줌.

        반환값: SearchResponse. 입력·권한·세대 오류도 예외 대신 status=error 응답으로 돌려줌.
        예외: 없음. 예상하지 못한 오류는 internal_error 응답으로 바꾸고 감사 로그에 남김.
        부수효과: LLM 호출(최대 16회)·감사 로그 기록.
        """

        state = self.initial_state(request, role)
        try:
            final = self.workflow.run(state)
            return SearchResponse.model_validate(final["response"])
        except Exception as error:
            # 내부 오류 내용(경로·키 등)은 응답에 싣지 않고 감사 로그에만 오류 종류를 남김
            self.audit_log.write({"type": "internal_error", "request_id": state["request_id"],
                                  "error": type(error).__name__})
            return SearchResponse(
                request_id=str(state["request_id"]),
                status=STATUS_ERROR,
                message="요청을 처리하는 중 내부 오류가 발생했습니다.",
                finish_reason="오류: internal_error",
                error_code="internal_error",
            )

    def health(self) -> dict[str, Any]:
        """상태 확인용 정보를 돌려줌.

        반환값: ready·generation·chunk_count·loading·last_error 키를 가진 dict임.
        """

        return dict(self.index_provider.status())
