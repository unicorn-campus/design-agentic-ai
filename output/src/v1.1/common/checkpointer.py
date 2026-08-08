"""중간 저장 장치 = 흐름이 끊겨도 이어서 할 수 있게 상태를 저장해 두는 장치임.

백엔드를 한 겹 감싸 두어 개발할 때는 메모리, 확인할 때는 데이터베이스로 갈아 끼움.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver

from .config import CheckpointBackend, Settings
from .config import CheckpointFailurePolicy
from .state import TriggerKind

__all__ = [
    "SESSION_ID_SEPARATOR",
    "build_thread_id",
    "build_idempotency_key",
    "thread_config",
    "invocation_config",
    "IdempotencyStore",
    "InMemoryIdempotencyStore",
    "open_checkpointer",
    "CheckpointerHandle",
    "CheckpointUnavailable",
]

SESSION_ID_SEPARATOR = ":"


def build_thread_id(
    member_id: str,
    workflow_name: str,
    requested_at: datetime,
) -> str:
    """세션 식별자를 만드는 단 하나의 자리. 문자열을 다른 곳에서 조립하지 않음."""
    if not member_id or SESSION_ID_SEPARATOR in member_id:
        raise ValueError(f"회원 식별자에 구분자를 넣을 수 없음: {member_id!r}")
    if not workflow_name or SESSION_ID_SEPARATOR in workflow_name:
        raise ValueError(f"워크플로우 이름에 구분자를 넣을 수 없음: {workflow_name!r}")
    stamped = requested_at.astimezone(timezone.utc).replace(microsecond=0)
    return SESSION_ID_SEPARATOR.join(
        (member_id, workflow_name, stamped.strftime("%Y-%m-%dT%H:%M:%SZ"))
    )


def build_idempotency_key(scope: str, *parts: str) -> str:
    """같은 요청이 두 번 와도 한 번만 처리되게 하는 중복 방지 키."""
    if not parts:
        raise ValueError("중복 방지 키에는 값이 한 개 이상 있어야 함")
    for part in parts:
        if not part or SESSION_ID_SEPARATOR in part:
            raise ValueError(f"중복 방지 키 조각에 구분자를 넣을 수 없음: {part!r}")
    return SESSION_ID_SEPARATOR.join((scope, *parts))


def thread_config(thread_id: str, **extra: object) -> dict[str, object]:
    """체크포인트 식별 값만 `configurable` 아래에 둠."""
    return {"configurable": {"thread_id": thread_id, **extra}}


def invocation_config(
    thread_id: str,
    *,
    recursion_limit: int,
    checkpoint_id: str | None = None,
) -> dict[str, object]:
    """LangGraph 호출 설정을 올바른 계층으로 조립함.

    `thread_id`와 `checkpoint_id`는 `configurable` 아래, `recursion_limit`은
    호출 설정의 최상위에 있어야 함.
    """
    if recursion_limit < 1:
        raise ValueError("흐름 전체 단계 상한은 1 이상이어야 함")
    configurable: dict[str, object] = {"thread_id": thread_id}
    if checkpoint_id is not None:
        configurable["checkpoint_id"] = checkpoint_id
    return {"configurable": configurable, "recursion_limit": recursion_limit}


class IdempotencyStore:
    """중복 방지 키를 저장하는 자리. 실제 저장소 연결은 뒤 프롬프트 몫임."""

    async def claim(self, key: str) -> bool:
        raise NotImplementedError

    async def release(self, key: str) -> None:
        raise NotImplementedError


@dataclass(slots=True)
class InMemoryIdempotencyStore(IdempotencyStore):
    _claimed: set[str] = field(default_factory=set)

    async def claim(self, key: str) -> bool:
        if key in self._claimed:
            return False
        self._claimed.add(key)
        return True

    async def release(self, key: str) -> None:
        self._claimed.discard(key)


class CheckpointUnavailable(RuntimeError):
    """선택한 PostgreSQL 체크포인터를 열거나 초기화하지 못함."""


@dataclass(frozen=True, slots=True)
class CheckpointerHandle:
    saver: BaseCheckpointSaver
    backend: CheckpointBackend
    requested_backend: CheckpointBackend
    retention_days: int | None
    idempotency: IdempotencyStore
    fallback_reason: str | None = None

    @property
    def retention_configured(self) -> bool:
        return self.retention_days is not None

    @property
    def degraded(self) -> bool:
        return self.backend is not self.requested_backend


@asynccontextmanager
async def open_checkpointer(
    settings: Settings,
    *,
    idempotency: IdempotencyStore | None = None,
) -> AsyncIterator[CheckpointerHandle]:
    """설정이 정한 백엔드로 중간 저장 장치를 열고 닫음."""
    store = idempotency if idempotency is not None else InMemoryIdempotencyStore()

    if settings.checkpoint_backend is CheckpointBackend.MEMORY:
        yield CheckpointerHandle(
            saver=InMemorySaver(),
            backend=CheckpointBackend.MEMORY,
            requested_backend=CheckpointBackend.MEMORY,
            retention_days=settings.checkpoint_retention_days,
            idempotency=store,
        )
        return

    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    db_url = settings.checkpoint_db_url
    if not db_url:
        raise ValueError("postgres 백엔드인데 접속 문자열이 없음")

    postgres_context = AsyncPostgresSaver.from_conn_string(db_url)
    saver = None
    try:
        saver = await postgres_context.__aenter__()
        await saver.setup()
    except Exception as exc:
        if saver is not None:
            await postgres_context.__aexit__(type(exc), exc, exc.__traceback__)
        if (
            settings.checkpoint_failure_policy
            is CheckpointFailurePolicy.MEMORY_FALLBACK_FOR_DEVELOPMENT
        ):
            yield CheckpointerHandle(
                saver=InMemorySaver(),
                backend=CheckpointBackend.MEMORY,
                requested_backend=CheckpointBackend.POSTGRES,
                retention_days=settings.checkpoint_retention_days,
                idempotency=store,
                fallback_reason=f"{type(exc).__name__}: {exc}",
            )
            return
        raise CheckpointUnavailable(
            "PostgreSQL 체크포인터 연결·setup 실패 — 메모리로 자동 전환하지 않음"
        ) from exc

    try:
        yield CheckpointerHandle(
            saver=saver,
            backend=CheckpointBackend.POSTGRES,
            requested_backend=CheckpointBackend.POSTGRES,
            retention_days=settings.checkpoint_retention_days,
            idempotency=store,
        )
    finally:
        await postgres_context.__aexit__(None, None, None)


def resume_scope_for(trigger_kind: TriggerKind) -> str:
    """③ 11절이 정한 재개 단위 이름. 중복 방지 키의 앞자리로 씀."""
    scopes: Mapping[TriggerKind, str] = {
        TriggerKind.BATCH_PREFERENCE_LEARNING: "member_and_target_date",
        TriggerKind.EVENT_PIPELINE: "record_and_member",
        TriggerKind.SYNC_SUBSCRIBE: "member_plan_and_payment_idempotency",
        TriggerKind.SYNC_CANCEL: "member_and_scheduled_downgrade_on",
        TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION: "payment_id",
        TriggerKind.BATCH_CANCEL_EXPIRY: "member_and_scheduled_downgrade_on",
    }
    try:
        return scopes[trigger_kind]
    except KeyError as exc:
        raise ValueError(f"{trigger_kind.value}는 재개 단위를 두지 않는 트리거임") from exc
