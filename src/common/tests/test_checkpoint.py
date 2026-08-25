import asyncio

from help_desk_runtime.checkpoint import (
    IdempotencyRegistry,
    build_thread_id,
    create_checkpointer,
    sanitize_checkpoint_state,
)


class PrefixEncryptor:
    def encrypt(self, value: object) -> str:
        return f"encrypted:{value!r}"


def test_thread_id_uses_design_component_order() -> None:
    assert build_thread_id("W-1", customer_ref="customer", request_id="request") == (
        "W-1:customer:request"
    )


def test_checkpoint_excludes_and_encrypts_sensitive_fields() -> None:
    state = {
        "request_id": "request",
        "auth_session_ref": "excluded",
        "customer_ref": "encrypted",
    }
    sanitized = sanitize_checkpoint_state("W-1", state, PrefixEncryptor())
    assert "auth_session_ref" not in sanitized
    assert sanitized["request_id"] == "request"
    assert sanitized["customer_ref"].startswith("encrypted:")


def test_idempotency_key_is_claimed_once() -> None:
    registry = IdempotencyRegistry()
    assert registry.claim("key") is True
    assert registry.claim("key") is False


def test_sqlite_checkpointer_adapter_opens() -> None:
    async def open_checkpointer() -> None:
        async with create_checkpointer("sqlite", ":memory:") as checkpointer:
            assert checkpointer is not None

    asyncio.run(open_checkpointer())
