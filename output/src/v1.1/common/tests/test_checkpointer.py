"""중간 저장 장치 시험. 실제 데이터베이스를 부르는 시험은 `live_call` 표식으로 갈라 둠."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from langgraph.checkpoint.memory import InMemorySaver

from common.checkpointer import (
    CheckpointUnavailable,
    CheckpointerHandle,
    InMemoryIdempotencyStore,
    build_idempotency_key,
    build_thread_id,
    invocation_config,
    open_checkpointer,
    resume_scope_for,
    thread_config,
)
from common.config import CheckpointBackend, Settings, load_settings
from common.state import TriggerKind

REQUESTED_AT = datetime(2026, 8, 8, 3, 14, 15, 926_000, tzinfo=timezone.utc)


def test_thread_id_uses_member_workflow_and_second_level_utc() -> None:
    assert (
        build_thread_id("mbr_001", "recommend", REQUESTED_AT)
        == "mbr_001:recommend:2026-08-08T03:14:15Z"
    )


def test_thread_id_normalises_other_timezones_to_utc() -> None:
    kst = timezone(timedelta(hours=9))
    assert build_thread_id(
        "mbr_001", "recommend", REQUESTED_AT.astimezone(kst)
    ) == build_thread_id("mbr_001", "recommend", REQUESTED_AT)


@pytest.mark.parametrize(
    ("member_id", "workflow"),
    [("", "recommend"), ("mbr:001", "recommend"), ("mbr_001", ""), ("mbr_001", "a:b")],
)
def test_thread_id_rejects_pieces_that_break_the_format(
    member_id: str, workflow: str
) -> None:
    with pytest.raises(ValueError):
        build_thread_id(member_id, workflow, REQUESTED_AT)


def test_thread_config_shape_matches_framework_expectation() -> None:
    config = thread_config("mbr_001:recommend:2026-08-08T03:14:15Z")
    assert config == {
        "configurable": {"thread_id": "mbr_001:recommend:2026-08-08T03:14:15Z"}
    }


def test_invocation_config_places_recursion_limit_at_the_top_level() -> None:
    config = invocation_config(
        "thread-1", recursion_limit=19, checkpoint_id="checkpoint-1"
    )
    assert config == {
        "configurable": {
            "thread_id": "thread-1",
            "checkpoint_id": "checkpoint-1",
        },
        "recursion_limit": 19,
    }


def test_invocation_config_rejects_non_positive_recursion_limit() -> None:
    with pytest.raises(ValueError):
        invocation_config("thread-1", recursion_limit=0)


def test_idempotency_key_joins_scope_and_parts() -> None:
    key = build_idempotency_key("member_and_target_date", "mbr_001", "2026-08-07")
    assert key == "member_and_target_date:mbr_001:2026-08-07"


def test_idempotency_key_rejects_empty_and_separator() -> None:
    with pytest.raises(ValueError):
        build_idempotency_key("scope")
    with pytest.raises(ValueError):
        build_idempotency_key("scope", "a:b")


async def test_same_request_is_claimed_only_once() -> None:
    store = InMemoryIdempotencyStore()
    key = build_idempotency_key("payment_id", "pay_001")
    assert await store.claim(key) is True
    assert await store.claim(key) is False
    await store.release(key)
    assert await store.claim(key) is True


def test_resume_scope_exists_for_every_trigger_that_has_side_effects() -> None:
    for kind in (
        TriggerKind.BATCH_PREFERENCE_LEARNING,
        TriggerKind.EVENT_PIPELINE,
        TriggerKind.SYNC_SUBSCRIBE,
        TriggerKind.SYNC_CANCEL,
        TriggerKind.EVENT_SUBSCRIPTION_PROPAGATION,
        TriggerKind.BATCH_CANCEL_EXPIRY,
    ):
        assert resume_scope_for(kind)


@pytest.mark.parametrize(
    "kind", [TriggerKind.SYNC_RECOMMEND, TriggerKind.SYNC_INSIGHT]
)
def test_read_only_triggers_have_no_resume_scope(kind: TriggerKind) -> None:
    with pytest.raises(ValueError):
        resume_scope_for(kind)


async def test_memory_backend_opens_and_reports_unset_retention(
    settings: Settings,
) -> None:
    async with open_checkpointer(settings) as handle:
        assert isinstance(handle, CheckpointerHandle)
        assert isinstance(handle.saver, InMemorySaver)
        assert handle.backend is CheckpointBackend.MEMORY
        assert handle.retention_configured is False


async def test_checkpointer_round_trips_state_through_the_saver(
    settings: Settings,
) -> None:
    async with open_checkpointer(settings) as handle:
        thread = thread_config(build_thread_id("mbr_001", "recommend", REQUESTED_AT))
        assert await handle.saver.aget(thread) is None


class _BrokenPostgresContext:
    async def __aenter__(self):
        raise OSError("database unavailable")

    async def __aexit__(self, exc_type, exc, traceback):
        return False


def _postgres_settings(
    monkeypatch: pytest.MonkeyPatch,
    env_ready: None,
    *,
    failure_policy: str,
) -> Settings:
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_BACKEND", "postgres")
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_DB_URL", "postgresql://localhost/test")
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_FAILURE_POLICY", failure_policy)
    return load_settings()


async def test_postgres_failure_is_fail_fast_by_default(
    monkeypatch: pytest.MonkeyPatch, env_ready: None
) -> None:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    monkeypatch.setattr(
        AsyncPostgresSaver,
        "from_conn_string",
        lambda _db_url: _BrokenPostgresContext(),
    )
    settings = _postgres_settings(
        monkeypatch, env_ready, failure_policy="fail_fast"
    )
    with pytest.raises(CheckpointUnavailable, match="자동 전환하지 않음"):
        async with open_checkpointer(settings):
            pytest.fail("PostgreSQL 연결 실패 뒤 본문에 진입하면 안 됨")


async def test_postgres_failure_uses_memory_only_when_development_fallback_is_explicit(
    monkeypatch: pytest.MonkeyPatch, env_ready: None
) -> None:
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    monkeypatch.setattr(
        AsyncPostgresSaver,
        "from_conn_string",
        lambda _db_url: _BrokenPostgresContext(),
    )
    settings = _postgres_settings(
        monkeypatch,
        env_ready,
        failure_policy="memory_fallback_for_development",
    )
    async with open_checkpointer(settings) as handle:
        assert isinstance(handle.saver, InMemorySaver)
        assert handle.requested_backend is CheckpointBackend.POSTGRES
        assert handle.backend is CheckpointBackend.MEMORY
        assert handle.degraded is True
        assert "database unavailable" in str(handle.fallback_reason)


@pytest.mark.live_call
async def test_postgres_backend_sets_up_tables(
    monkeypatch: pytest.MonkeyPatch, env_ready: None
) -> None:
    """실제 PostgreSQL을 부름. `-m live_call`로만 돎(D-07).

    Windows에서는 이 시험을 돌리기 전에 `configure_event_loop_for_async_db()`를
    부른 상태여야 함(`common/runtime.py` 참고).
    """
    monkeypatch.setenv("LUNCHPICK_CHECKPOINT_BACKEND", "postgres")
    settings = load_settings()
    async with open_checkpointer(settings) as handle:
        assert handle.backend is CheckpointBackend.POSTGRES
        thread = thread_config(build_thread_id("mbr_001", "recommend", REQUESTED_AT))
        assert await handle.saver.aget(thread) is None
