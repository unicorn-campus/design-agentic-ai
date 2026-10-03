"""문서 검색(W-2)을 HTTP로 여는 얇은 FastAPI 표현 계층임."""

from __future__ import annotations

import logging
import threading
from contextlib import asynccontextmanager
from typing import Annotated, Any, AsyncIterator

from fastapi import FastAPI, Header, Response
from fastapi.responses import JSONResponse

from app.application.models import (
    ERROR_HTTP_STATUS,
    STATUS_ERROR,
    SearchRequest,
    SearchResponse,
)

logger = logging.getLogger(__name__)

# 조립에 실패했을 때 쓰는 오류 코드. 원인(설정·색인·모델)을 가리지 않는 서버측 일반 오류임
ASSEMBLY_ERROR_CODE = "internal_error"
ASSEMBLY_ERROR_MESSAGE = "검색 서비스를 준비하지 못했습니다. 잠시 뒤 다시 시도해 주세요."


class Utf8JSONResponse(JSONResponse):
    """Content-Type에 charset=utf-8을 밝혀 보내는 JSON 응답.

    문자셋이 없으면 Windows PowerShell 5.1의 Invoke-RestMethod가 본문을 UTF-8이 아닌 방식으로 읽어
    한글이 깨짐(2026-10-03 실측: '제6조의2'가 깨져 보임). 응답 본문 바이트는 JSONResponse와 같음.
    """

    media_type = "application/json; charset=utf-8"


def create_app(service: Any = None) -> FastAPI:
    """검색 API 앱을 만듦. service를 주면 그 서비스를 쓰고, 없으면 bootstrap으로 1회 조립함.

    목적: 색인·모델 없이도 표현 계층을 시험할 수 있게 조립 지점을 바깥에서 바꿔 끼울 수 있게 함.
    방법: 주입이 없으면 시작(lifespan) 때 app.bootstrap.create_service()를 1회 부름(지연 import).
    반환값: /search·/health 경로를 가진 FastAPI 앱임.
    부수효과: 조립 시점에 모델·색인을 읽어 메모리에 올림. 모듈을 import하는 것만으로는 올리지 않음.
    """

    state: dict[str, Any] = {"service": service, "error": None}
    lock = threading.Lock()

    def get_service() -> Any:
        """조립된 서비스를 반환함. 아직 없으면 이 호출에서 1회만 조립함. 실패하면 None을 반환함."""

        with lock:
            if state["service"] is None and state["error"] is None:
                try:
                    # 표현 계층은 구현체를 직접 import하지 않음. 조립은 bootstrap 한 곳만 함
                    from app.bootstrap import create_service

                    state["service"] = create_service()
                except Exception as error:  # noqa: BLE001 - 조립 실패를 상태 확인으로 알리고 서버는 계속 띄움
                    logger.exception("검색 서비스 조립에 실패함")
                    state["error"] = type(error).__name__
            return state["service"]

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # 첫 요청이 모델 적재를 기다리지 않게 서버 시작 때 미리 조립함
        get_service()
        yield

    app = FastAPI(title="Vector Retriever", version="1.0.0", lifespan=lifespan,
                  default_response_class=Utf8JSONResponse)

    @app.post("/search", response_model=SearchResponse)
    def search(
        request: SearchRequest,
        response: Response,
        x_user_role: Annotated[str | None, Header(alias="X-User-Role")] = None,
    ) -> SearchResponse:
        """질문을 받아 검색 결과 1건을 돌려줌.

        인자: 역할은 앞단 로그인 게이트웨이가 넣어 준 X-User-Role 헤더에서만 받음(요청 본문 값은 쓰지 않음).
        반환값: SearchResponse. 오류도 예외가 아니라 status=error 응답으로 돌려줌(설계 부록 B).
        부수효과: HTTP 상태를 응답의 error_code로 정함(오류 코드가 없으면 200).
        """

        application = get_service()
        if application is None:
            return _assembly_error_response(response)
        result = application.execute(request, x_user_role)
        # 오류 코드 → HTTP 상태 변환은 표현 계층의 일임. 코드가 없으면 200을 그대로 씀
        if getattr(result, "error_code", None):
            response.status_code = ERROR_HTTP_STATUS.get(result.error_code, 500)
        return result

    @app.get("/health")
    def health() -> Utf8JSONResponse:
        """색인 세대를 쓸 수 있는지 알려 줌. 쓸 수 있으면 200, 아니면 503임."""

        application = get_service()
        if application is None:
            return Utf8JSONResponse(status_code=503, content=_unavailable_health(state["error"]))
        try:
            status = dict(application.health())
        except Exception as error:  # noqa: BLE001 - 상태 확인이 예외로 끊기면 배포 점검이 막힘
            logger.exception("상태 확인에 실패함")
            return Utf8JSONResponse(status_code=503, content=_unavailable_health(type(error).__name__))
        return Utf8JSONResponse(status_code=200 if status.get("ready") else 503, content=status)

    return app


def _assembly_error_response(response: Response) -> SearchResponse:
    """조립 실패 때 돌려줄 표준 오류 응답을 만듦. 원인 문자열은 담지 않음(비밀값·경로 노출 방지)."""

    response.status_code = ERROR_HTTP_STATUS.get(ASSEMBLY_ERROR_CODE, 500)
    return SearchResponse(
        request_id="",
        status=STATUS_ERROR,
        message=ASSEMBLY_ERROR_MESSAGE,
        error_code=ASSEMBLY_ERROR_CODE,
        finish_reason="service_unavailable",
    )


def _unavailable_health(error_name: str | None) -> dict[str, Any]:
    """조립·상태 확인 실패 때의 health 본문을 만듦. 오류 종류 이름만 담고 메시지 원문은 담지 않음."""

    return {
        "ready": False,
        "generation": None,
        "chunk_count": 0,
        "loading": False,
        "last_error": error_name or "unknown",
    }


app = create_app()
