from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Protocol


THREAD_COMPONENTS = {
    "W-1": ("customer_ref", "request_id"),
    "W-2": ("batch_date", "data_version"),
    "W-3": ("event_id", "job_type"),
}

EXCLUDED_FIELDS = {
    "W-1": frozenset({"auth_session_ref", "safe_inquiry_text"}),
    "W-2": frozenset(),
    "W-3": frozenset({"masked_transcript"}),
}

ENCRYPTED_FIELDS = {
    "W-1": frozenset({"customer_ref", "answer_draft", "approval_result"}),
    "W-2": frozenset({"masked_consultation_refs", "faq_candidates", "review_decision"}),
    "W-3": frozenset({
        "consultation_ref", "summary_draft", "review_decision", "crm_result",
        "survey_consent_ref", "survey_result",
    }),
}


class Encryptor(Protocol):
    def encrypt(self, value: Any) -> Any: ...


def build_thread_id(workflow_id: str, **components: object) -> str:
    names = THREAD_COMPONENTS[workflow_id]
    missing = [name for name in names if name not in components]
    if missing:
        raise ValueError(f"세션 격리 키 성분 누락: {', '.join(missing)}")
    return ":".join((workflow_id, *(str(components[name]) for name in names)))


def sanitize_checkpoint_state(
    workflow_id: str,
    state: dict[str, Any],
    encryptor: Encryptor,
) -> dict[str, Any]:
    excluded = EXCLUDED_FIELDS[workflow_id]
    encrypted = ENCRYPTED_FIELDS[workflow_id]
    return {
        key: encryptor.encrypt(value) if key in encrypted else value
        for key, value in state.items()
        if key not in excluded
    }


class IdempotencyRegistry:
    def __init__(self) -> None:
        self._completed: set[str] = set()

    def claim(self, key: str) -> bool:
        if key in self._completed:
            return False
        self._completed.add(key)
        return True


@asynccontextmanager
async def create_checkpointer(backend: str, uri: str) -> AsyncIterator[Any]:
    if backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver

        yield InMemorySaver()
        return
    if backend != "sqlite":
        raise ValueError(f"지원하지 않는 체크포인터 백엔드: {backend}")

    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

    async with AsyncSqliteSaver.from_conn_string(uri) as checkpointer:
        yield checkpointer
