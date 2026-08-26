from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .boundary import BoundaryRejected
from .models import ErrorBody


class PublicApiError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def _response(status_code: int, code: str, message: str) -> JSONResponse:
    body = ErrorBody(code=code, message=message)
    return JSONResponse(status_code=status_code, content=body.model_dump())


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(PublicApiError)
    async def public_error_handler(request: Request, error: PublicApiError) -> JSONResponse:
        del request
        return _response(error.status_code, error.code, error.message)

    @app.exception_handler(BoundaryRejected)
    async def boundary_error_handler(request: Request, error: BoundaryRejected) -> JSONResponse:
        del request, error
        return _response(400, "request_blocked", "요청을 안전하게 처리할 수 없음")

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        error: RequestValidationError,
    ) -> JSONResponse:
        del request, error
        return _response(422, "invalid_request", "요청 형식이 올바르지 않음")

    @app.exception_handler(Exception)
    async def internal_error_handler(request: Request, error: Exception) -> JSONResponse:
        del request, error
        return _response(500, "internal_error", "요청 처리에 실패함")
