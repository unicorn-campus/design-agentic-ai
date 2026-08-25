from __future__ import annotations

import logging
from contextvars import ContextVar, Token


_request_id: ContextVar[str] = ContextVar("request_id", default="")
_workflow_id: ContextVar[str] = ContextVar("workflow_id", default="")


def set_execution_context(request_id: str, workflow_id: str) -> tuple[Token[str], Token[str]]:
    return _request_id.set(request_id), _workflow_id.set(workflow_id)


def clear_execution_context(tokens: tuple[Token[str], Token[str]]) -> None:
    request_token, workflow_token = tokens
    _request_id.reset(request_token)
    _workflow_id.reset(workflow_token)


def current_labels() -> dict[str, str]:
    return {"요청ID": _request_id.get(), "워크플로우ID": _workflow_id.get()}


class CommonLabelFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = _request_id.get()
        record.workflow_id = _workflow_id.get()
        return True
