"""Retriever의 FastAPI·SSE 표현 계층."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sse_starlette import EventSourceResponse, JSONServerSentEvent

from app.application.errors import (
    IndexUnavailableError,
    LLMAuthError,
    LLMCallLimitError,
    LLMConfigError,
    LLMRequestError,
    LLMRetryableError,
)
from app.application.llm_budget import LLMCallCounter
from app.application.retriever_service import RetrieverService, is_known_role
from app.application.state import HealthResult, Mode, RetrieverRequest, SearchResult


DEFAULT_MAX_LLM_CALLS_TOTAL = 200  # 서비스 준비에 실패했을 때 쓰는 누적 호출 상한 기본값


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    mode: Mode = "hybrid_rerank"
    transform: Literal["off", "auto"] = "off"


class SearchResponse(SearchResult):
    request_id: str


class HealthResponse(HealthResult):
    pass


class ErrorResponse(BaseModel):
    error_code: Literal[
        "invalid_request",
        "invalid_role",
        "llm_call_limit",
        "index_unavailable",
        "timeout",
        "internal_error",
    ]
    message: str
    detail: Any = None


class InvalidRoleError(ValueError):
    pass


def get_service(request: Request) -> RetrieverService:
    """lifespan에서 준비한 응용 서비스를 꺼냄. 준비 실패 시 503으로 응답함."""

    service = getattr(request.app.state, "service", None)
    if service is None:
        cause = getattr(request.app.state, "startup_error", None)
        raise IndexUnavailableError("Retriever 자원을 준비하지 못함") from cause
    return service


def require_role(
    x_role: Annotated[
        str | None,
        Header(alias="X-Role", description="필수 역할: agent 또는 auditor"),
    ] = None,
) -> Literal["agent", "auditor"]:
    if x_role is None or not is_known_role(x_role):
        raise InvalidRoleError("X-Role 헤더가 없거나 허용되지 않은 역할임")
    return x_role


def _error(status_code: int, error_code: str, message: str, detail: Any) -> JSONResponse:
    body = ErrorResponse(error_code=error_code, message=message, detail=detail)
    return JSONResponse(status_code=status_code, content=body.model_dump(mode="json"))


async def validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error(400, "invalid_request", "요청 형식이 올바르지 않음", exc.errors())


async def invalid_role_handler(_request: Request, _exc: InvalidRoleError) -> JSONResponse:
    return _error(400, "invalid_role", "X-Role 헤더가 올바르지 않음", None)


async def llm_limit_handler(_request: Request, exc: LLMCallLimitError) -> JSONResponse:
    return _error(429, "llm_call_limit", "LLM 호출 상한에 도달함", exc.detail)


async def index_unavailable_handler(_request: Request, exc: IndexUnavailableError) -> JSONResponse:
    return _error(503, "index_unavailable", "검색 인덱스를 사용할 수 없음", type(exc).__name__)


async def timeout_handler(_request: Request, exc: TimeoutError) -> JSONResponse:
    return _error(504, "timeout", "요청 제한 시간을 초과함", type(exc).__name__)


async def llm_request_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _error(400, "invalid_request", "LLM 설정 또는 요청을 확인해야 함", type(exc).__name__)


async def llm_retryable_handler(_request: Request, exc: LLMRetryableError) -> JSONResponse:
    if exc.status_code == 429:
        return _error(429, "llm_call_limit", "상류 LLM 호출 제한에 도달함", None)
    return _error(500, "internal_error", "상류 LLM 요청을 완료하지 못함", type(exc).__name__)


async def internal_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    return _error(500, "internal_error", "요청 처리 중 오류가 발생함", type(exc).__name__)


def _register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(InvalidRoleError, invalid_role_handler)
    app.add_exception_handler(LLMCallLimitError, llm_limit_handler)
    app.add_exception_handler(IndexUnavailableError, index_unavailable_handler)
    app.add_exception_handler(TimeoutError, timeout_handler)
    app.add_exception_handler(LLMAuthError, llm_request_handler)
    app.add_exception_handler(LLMRequestError, llm_request_handler)
    app.add_exception_handler(LLMConfigError, llm_request_handler)
    app.add_exception_handler(LLMRetryableError, llm_retryable_handler)
    app.add_exception_handler(Exception, internal_error_handler)


def _counter(request: Request) -> LLMCallCounter:
    return request.app.state.llm_counter


def _request_budget(request: Request, service: RetrieverService) -> int:
    counter = _counter(request)
    if counter.remaining <= 0:
        raise LLMCallLimitError(scope="total", limit=counter.limit, used=counter.used)
    per_request = int(service.limits.max_llm_calls_per_request)
    return min(per_request, counter.remaining)


def _application_request(
    value: SearchRequest,
    role: Literal["agent", "auditor"],
    request_id: str,
    max_llm_calls: int,
) -> RetrieverRequest:
    return RetrieverRequest(
        **value.model_dump(),
        role=role,
        thread_id=f"api-{request_id[:8]}",
        max_llm_calls=max_llm_calls,
    )


def _record_calls(counter: LLMCallCounter, value: SearchResult | BaseException) -> None:
    attempts = getattr(value, "llm_calls", None)
    if attempts is None:
        attempts = getattr(value, "attempts", 0)
    if isinstance(attempts, int) and not isinstance(attempts, bool) and attempts:
        counter.add(attempts)


async def _invoke(
    request: Request,
    function: Callable[[RetrieverRequest], SearchResult],
    value: RetrieverRequest,
    service: RetrieverService,
    *,
    require_answer: bool = False,
) -> SearchResult:
    timeout = float(service.limits.request_timeout_seconds)
    try:
        result = await asyncio.wait_for(
            asyncio.to_thread(function, value),
            timeout=timeout,
        )
    except Exception as error:
        _record_calls(_counter(request), error)
        raise
    _record_calls(_counter(request), result)
    if require_answer and result.status == "halted_by_limit" and result.answer is None:
        raise LLMCallLimitError(
            scope="request",
            limit=value.max_llm_calls,
            used=result.llm_calls,
        )
    return result


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health(
    _role: Annotated[Literal["agent", "auditor"], Depends(require_role)],
    service: Annotated[RetrieverService, Depends(get_service)],
) -> HealthResponse:
    result = await asyncio.to_thread(service.health)
    if not result.index_connected:
        raise IndexUnavailableError("컬렉션이 비어 있거나 서명이 일치하지 않음")
    return HealthResponse.model_validate(result.model_dump())


@router.post("/search", response_model=SearchResponse)
async def search(
    request: Request,
    body: SearchRequest,
    role: Annotated[Literal["agent", "auditor"], Depends(require_role)],
    service: Annotated[RetrieverService, Depends(get_service)],
) -> SearchResponse:
    request_id = uuid4().hex
    value = _application_request(body, role, request_id, _request_budget(request, service))
    result = await _invoke(request, service.search, value, service)
    return SearchResponse(**result.model_dump(), request_id=request_id)


@router.post("/answer", response_model=SearchResponse)
async def answer(
    request: Request,
    body: SearchRequest,
    role: Annotated[Literal["agent", "auditor"], Depends(require_role)],
    service: Annotated[RetrieverService, Depends(get_service)],
) -> SearchResponse:
    request_id = uuid4().hex
    value = _application_request(body, role, request_id, _request_budget(request, service))
    result = await _invoke(
        request,
        service.answer,
        value,
        service,
        require_answer=True,
    )
    return SearchResponse(**result.model_dump(), request_id=request_id)


def _stream_error(error: BaseException) -> tuple[str, str, Any]:
    if isinstance(error, LLMCallLimitError):
        return "llm_call_limit", "LLM 호출 상한에 도달함", error.detail
    if isinstance(error, IndexUnavailableError):
        return "index_unavailable", "검색 인덱스를 사용할 수 없음", type(error).__name__
    if isinstance(error, TimeoutError):
        return "timeout", "요청 제한 시간을 초과함", type(error).__name__
    return "internal_error", "스트림 처리 중 오류가 발생함", type(error).__name__


@router.get("/answer/stream")
async def answer_stream(
    request: Request,
    query: Annotated[str, Query(min_length=1)],
    role: Annotated[Literal["agent", "auditor"], Depends(require_role)],
    service: Annotated[RetrieverService, Depends(get_service)],
    top_k: Annotated[int, Query(ge=1, le=50)] = 5,
    mode: Annotated[
        Mode,
        Query(),
    ] = "hybrid_rerank",
    transform: Annotated[Literal["off", "auto"], Query()] = "off",
) -> EventSourceResponse:
    health_result = await asyncio.to_thread(service.health)
    if not health_result.index_connected:
        raise IndexUnavailableError("컬렉션이 비어 있거나 서명이 일치하지 않음")
    request_id = uuid4().hex
    body = SearchRequest(query=query, top_k=top_k, mode=mode, transform=transform)

    async def events() -> AsyncIterator[JSONServerSentEvent]:
        try:
            budget = _request_budget(request, service)
            value = _application_request(body, role, request_id, budget)
            timeout = float(service.limits.request_timeout_seconds)
            async with asyncio.timeout(timeout):
                async for item in service.stream(value):
                    if await request.is_disconnected():
                        break
                    event, data = item["event"], item["data"]
                    if event == "final":
                        result = SearchResult.model_validate(data)
                        _record_calls(_counter(request), result)
                        if result.status == "halted_by_limit" and result.answer is None:
                            raise LLMCallLimitError(
                                scope="request",
                                limit=value.max_llm_calls,
                                used=result.llm_calls,
                            )
                        data = {**result.model_dump(mode="json"), "request_id": request_id}
                    yield JSONServerSentEvent(event=event, data=data)
        except asyncio.CancelledError:
            raise
        except Exception as error:
            code, message, detail = _stream_error(error)
            yield JSONServerSentEvent(
                event="error",
                data={"error_code": code, "message": message, "detail": detail},
            )

    return EventSourceResponse(events(), ping=15, send_timeout=30)


def create_app(service: RetrieverService | None = None) -> FastAPI:
    """FastAPI 앱을 만듦.

    service를 넘기면 그대로 쓰고(시험용 주입 지점), 없으면 시작 시 bootstrap으로 조립함.
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.service = service
        app.state.startup_error = None
        if app.state.service is None:
            try:
                from app.bootstrap import create_service

                app.state.service = await asyncio.to_thread(create_service)
            except Exception as error:
                app.state.startup_error = error
        limit = (
            int(app.state.service.limits.max_llm_calls_total)
            if app.state.service is not None
            else DEFAULT_MAX_LLM_CALLS_TOTAL
        )
        app.state.llm_counter = LLMCallCounter(limit)
        yield

    app = FastAPI(title="Vector Retriever API", version="0.1.0", lifespan=lifespan)
    _register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()
