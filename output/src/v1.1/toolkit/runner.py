"""커넥터 호출 파이프라인 — 재시도가 걸리는 **단 하나의 계층**임.

되묻기로 확정한 값 3건이 이 파일에 반영돼 있음.

1. **재시도 계층** — 커넥터 1계층만. 실제 재시도 루프는
   `common.external_call.call_with_limits` 하나뿐이고 이 파일은 그것을 **한 번만** 부름.
   노드 안 · 흐름 프레임워크에 재시도를 또 붙이면 횟수가 곱해짐 → `06-workflow.md`에 같은 값을 알림.
2. **시간 상한을 넘겼을 때의 뜻** — 되돌릴 수 없는 도구는 **취소를 성공으로 보고하지 않음.**
   결과를 `확인 중`으로 두고 사람 확인으로 올림(③ `S-S9` · `S-C10` 「초과 시 처리」와 같음).
3. **중복 방지 키 보관** — 저장소와 보관 기간은 설정에서 읽음.

순서 — 승인 문 → 사전 조건(호출 순서) → 입력 규격 → 중복 방지 키 → 호출 상한 자리 →
바깥 호출(감싸개 1겹) → 출력 규격(⑤ 키만) → 입력측 검사 훅 → 감사 기록.
승인·순서·규격에서 걸리면 **바깥 호출이 0건**임.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Protocol, runtime_checkable

from common.budget import now_ms
from common.config import Settings
from common.external_call import CallOutcome, StepExhausted, call_with_limits
from common.guardrail_hooks import HookSet, PassThroughHooks

from .approval import CallBudget, NoOpCallBudget, require_approval, require_preconditions
from .auth import Credential, OnBehalfOf
from .errors import (
    ConnectorRetryable,
    ErrorClass,
    ErrorReport,
    IdempotencyKeyMissing,
)
from .idempotency import ResultStore, StoredResult, key_fingerprint
from .schema import SideEffect, ToolSpec, project_output, validate_input
from .settings import ConnectorMode
from .transport import (
    Transport,
    TransportReply,
    classify_http_status,
    classify_transport_exception,
)

__all__ = [
    "CallContext",
    "ConnectorResult",
    "ConnectorAdapter",
    "ConnectorTool",
]

_EMPTY: Mapping[str, Any] = MappingProxyType({})
_OK_STATUS = range(200, 300)


@dataclass(frozen=True, slots=True)
class CallContext:
    """호출 1건이 들고 오는 바깥 사정. 승인 표시와 끝난 단계 목록이 여기 담김."""

    deadline_at: int
    completed_steps: tuple[str, ...] = ()
    approval_evidence: Mapping[str, Any] = _EMPTY
    on_behalf_of: OnBehalfOf | None = None
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class ConnectorResult:
    """상태에 얹을 수 있는 모양. 바깥 응답 원문은 들어가지 않음."""

    connector_id: str
    step_id: str
    ok: bool
    output: Mapping[str, Any]
    attempts: int
    outward_calls: int
    replayed: bool = False
    unresolved: bool = False
    escalate_to_human: bool = False
    error_report: ErrorReport | None = None
    audit: Mapping[str, Any] = _EMPTY

    @property
    def error_class(self) -> ErrorClass | None:
        return None if self.error_report is None else self.error_report.error_class


@runtime_checkable
class ConnectorAdapter(Protocol):
    """커넥터 어댑터 1개. 실물과 대역이 **같은 인터페이스**를 가짐."""

    spec: ToolSpec
    transport: Transport
    credential: Credential
    mode: ConnectorMode

    async def call(self, payload: Mapping[str, Any]) -> TransportReply: ...

    def translate(self, reply: TransportReply) -> Mapping[str, Any]: ...

    async def aclose(self) -> None: ...


@dataclass(slots=True)
class _Halt:
    """재시도하지 않을 실패. 감싸개가 잡아 다시 부르지 않게 **예외가 아니라 값으로** 돌려줌."""

    report: ErrorReport


@dataclass(slots=True)
class _AttemptTally:
    outward_calls: int = 0
    auth_failures: int = 0
    refreshed_at_ms: int | None = None


@dataclass(slots=True)
class ConnectorTool:
    """호출자가 보는 도구 1개. `06-workflow.md`가 노드에서 이걸 부름(배치는 06 몫)."""

    adapter: ConnectorAdapter
    settings: Settings
    result_store: ResultStore
    hooks: HookSet = field(default_factory=PassThroughHooks)
    call_budget: CallBudget = field(default_factory=NoOpCallBudget)
    max_calls: int | None = None

    @property
    def spec(self) -> ToolSpec:
        return self.adapter.spec

    @property
    def connector_id(self) -> str:
        return self.adapter.spec.connector_id

    async def aclose(self) -> None:
        await self.adapter.aclose()

    # -- 본체 --------------------------------------------------------------
    async def call(
        self, payload: Mapping[str, Any], context: CallContext
    ) -> ConnectorResult:
        spec = self.adapter.spec

        # 1) 승인 문 — 표시가 없으면 여기서 끝. 바깥 호출 0건.
        require_approval(spec, context.approval_evidence)

        # 2) 사전 조건(⑤ 「커넥터 검증 기준」의 호출 순서)
        require_preconditions(spec, context.completed_steps)

        # 3) 입력 규격 — 안 맞으면 `입력 오류`로 즉시 올림(재시도 0회)
        validated = validate_input(spec, payload)
        body = validated.model_dump()

        # 4) 중복 방지 키 — 쓰기 전건 필수. 같은 키면 바깥을 부르지 않음.
        idempotency_key = self._read_idempotency_key(spec, body)
        if idempotency_key is not None:
            stored = await self.result_store.get(idempotency_key)
            if stored is not None:
                return self._replayed_result(spec, context, idempotency_key, stored)

        # 5) 호출 상한 자리 — 실제로 세는 코드는 `05-guardrail.md` 몫임
        self.call_budget.check(spec.connector_id, context.request_id, self.max_calls)

        tally = _AttemptTally()
        outcome, exhausted = await self._send_with_limits(body, context, tally)

        if exhausted is not None:
            report = self._report_from_exhausted(spec, exhausted, tally)
            return self._failure_result(spec, context, idempotency_key, report, tally)

        assert outcome is not None
        if isinstance(outcome.value, _Halt):
            report = self._with_counts(outcome.value.report, outcome, tally)
            return self._failure_result(spec, context, idempotency_key, report, tally)

        # 6) 출력 규격 — ⑤ 키만 뽑아 담음. 바깥 응답을 그대로 상태에 올리지 않음.
        raw = self.adapter.translate(outcome.value)
        output = project_output(spec, raw)

        # 7) 입력측 검사 훅 — 바깥에서 온 글은 **데이터일 뿐**임.
        #    프롬프트로 넘기기 전에 `05-guardrail.md`의 검사 자리를 반드시 지나게 함.
        output = dict(self.hooks.inspector.inspect(spec.step_id, output))

        if idempotency_key is not None:
            await self.result_store.put(
                idempotency_key, StoredResult(output=output, stored_at_ms=now_ms())
            )

        audit = self._audit(
            spec, context, idempotency_key, outcome.attempts, tally, ok=True
        )
        self.hooks.recorder.record(spec.step_id, dict(audit))
        return ConnectorResult(
            connector_id=spec.connector_id,
            step_id=spec.step_id,
            ok=True,
            output=output,
            attempts=outcome.attempts,
            outward_calls=tally.outward_calls,
            audit=audit,
        )

    # -- 조각 --------------------------------------------------------------
    def _read_idempotency_key(
        self, spec: ToolSpec, body: Mapping[str, Any]
    ) -> str | None:
        if spec.idempotency_key_field is None:
            return None
        value = body.get(spec.idempotency_key_field)
        if not value:
            raise IdempotencyKeyMissing(
                ErrorReport(
                    connector_id=spec.connector_id,
                    step_id=spec.step_id,
                    error_class=ErrorClass.INPUT,
                    reason="쓰기 도구인데 중복 방지 키가 비어 있음",
                    offending_keys=(spec.idempotency_key_field,),
                    attempts=0,
                )
            )
        return str(value)

    async def _send_with_limits(
        self,
        body: Mapping[str, Any],
        context: CallContext,
        tally: _AttemptTally,
    ) -> tuple[CallOutcome | None, StepExhausted | None]:
        """재시도 루프는 여기 한 곳뿐임. `call_with_limits`를 **한 번만** 부름.

        시간 상한과 재시도 횟수는 `settings`(=③ 4절 값)에서만 옴 — 여기서 숫자를 정하지 않음.
        마감선까지 남은 시간이 모자라면 `common.budget.DeadlineTooTight`가 그대로 위로 올라감
        (상한 초과 처리는 ③ 소유 · `06-workflow.md` 몫이라 여기서 삼키지 않음).
        """
        spec = self.adapter.spec

        async def attempt() -> Any:
            tally.outward_calls += 1
            try:
                reply = await self.adapter.call(body)
            except Exception as exc:  # 연결 실패 · 늦음 등
                return self._decide(
                    classify_transport_exception(exc), "바깥 호출이 실패함", tally
                )
            status = reply.status_code
            if status is None or status in _OK_STATUS:
                return reply
            return self._decide(
                classify_http_status(status), f"바깥이 거절함(상태 {status})", tally
            )

        try:
            outcome = await call_with_limits(
                spec.step_id,
                attempt,
                self.settings,
                context.deadline_at,
            )
        except StepExhausted as exhausted:
            return None, exhausted
        return outcome, None

    def _decide(
        self, error_class: ErrorClass, reason: str, tally: _AttemptTally
    ) -> _Halt:
        """분류 먼저, 처리 나중.

        재시도해도 되는 실패만 **예외로 올려** 감싸개가 다시 부르게 함.
        재시도하면 안 되는 실패는 **값으로 돌려줘** 감싸개의 재시도 루프에 아예 들어가지 않게 함
        (그래서 입력 오류 · 권한 부족의 재시도는 구조적으로 0회임).
        """
        spec = self.adapter.spec
        report = ErrorReport(
            connector_id=spec.connector_id,
            step_id=spec.step_id,
            error_class=error_class,
            reason=reason,
            requested_scopes=spec.requested_scopes,
            last_backoff_ms=self.settings.backoff_ms(spec.step_id),
        )
        if error_class is ErrorClass.AUTH:
            tally.auth_failures += 1
            self.adapter.credential.invalidate()
            tally.refreshed_at_ms = now_ms()
            if tally.auth_failures >= 2:
                # 갱신 후에도 거절됨 — 즉시 멈추고 사람에게 알림
                return _Halt(
                    ErrorReport(
                        connector_id=spec.connector_id,
                        step_id=spec.step_id,
                        error_class=ErrorClass.AUTH,
                        reason="자격을 갱신했는데도 거절됨 — 사람 확인 필요",
                        requested_scopes=spec.requested_scopes,
                        credential_refreshed_at_ms=tally.refreshed_at_ms,
                    )
                )
            raise ConnectorRetryable(report)
        if error_class is ErrorClass.TRANSIENT:
            raise ConnectorRetryable(report)
        # 입력 오류 · 권한 부족 · 분류 불가 — 다시 때리지 않음
        return _Halt(report)

    def _report_from_exhausted(
        self, spec: ToolSpec, exhausted: StepExhausted, tally: _AttemptTally
    ) -> ErrorReport:
        last = exhausted.last_error
        if isinstance(last, ConnectorRetryable):
            base = last.report
        else:
            base = ErrorReport(
                connector_id=spec.connector_id,
                step_id=spec.step_id,
                error_class=classify_transport_exception(last),
                reason="시간 상한을 넘겼음"
                if isinstance(last, TimeoutError)
                else "바깥 호출이 실패함",
                requested_scopes=spec.requested_scopes,
            )
        timed_out = isinstance(last, TimeoutError)
        return ErrorReport(
            connector_id=base.connector_id,
            step_id=base.step_id,
            error_class=base.error_class,
            reason="시간 상한을 넘겼음" if timed_out else base.reason,
            offending_keys=base.offending_keys,
            requested_scopes=base.requested_scopes,
            attempts=exhausted.attempts,
            last_backoff_ms=self.settings.backoff_ms(spec.step_id),
            credential_refreshed_at_ms=tally.refreshed_at_ms,
            extra={"timed_out": timed_out},
        )

    def _with_counts(
        self, report: ErrorReport, outcome: CallOutcome, tally: _AttemptTally
    ) -> ErrorReport:
        return ErrorReport(
            connector_id=report.connector_id,
            step_id=report.step_id,
            error_class=report.error_class,
            reason=report.reason,
            offending_keys=report.offending_keys,
            requested_scopes=report.requested_scopes,
            attempts=outcome.attempts,
            last_backoff_ms=report.last_backoff_ms,
            credential_refreshed_at_ms=tally.refreshed_at_ms,
            extra=report.extra,
        )

    def _failure_result(
        self,
        spec: ToolSpec,
        context: CallContext,
        idempotency_key: str | None,
        report: ErrorReport,
        tally: _AttemptTally,
    ) -> ConnectorResult:
        """되돌릴 수 없는 도구는 **취소·실패를 성공으로 보고하지 않음.**"""
        timed_out = bool(report.extra.get("timed_out"))
        unresolved = False
        output: Mapping[str, Any] = {}
        escalate = spec.side_effect is SideEffect.WRITE_IRREVERSIBLE

        if spec.side_effect is SideEffect.WRITE_IRREVERSIBLE:
            if timed_out and spec.unresolved_marker is not None:
                unresolved = True
                output = dict(spec.unresolved_marker)
            elif spec.failure_marker is not None:
                output = dict(spec.failure_marker)
            elif spec.unresolved_marker is not None:
                unresolved = True
                output = dict(spec.unresolved_marker)

        audit = self._audit(
            spec, context, idempotency_key, report.attempts, tally, ok=False, report=report
        )
        self.hooks.recorder.record(spec.step_id, dict(audit))
        return ConnectorResult(
            connector_id=spec.connector_id,
            step_id=spec.step_id,
            ok=False,
            output=output,
            attempts=report.attempts,
            outward_calls=tally.outward_calls,
            unresolved=unresolved,
            escalate_to_human=escalate,
            error_report=report,
            audit=audit,
        )

    def _replayed_result(
        self,
        spec: ToolSpec,
        context: CallContext,
        idempotency_key: str,
        stored: StoredResult,
    ) -> ConnectorResult:
        audit = self._audit(spec, context, idempotency_key, 0, _AttemptTally(), ok=True)
        self.hooks.recorder.record(spec.step_id, {**audit, "replayed": True})
        return ConnectorResult(
            connector_id=spec.connector_id,
            step_id=spec.step_id,
            ok=True,
            output=dict(stored.output),
            attempts=0,
            outward_calls=0,
            replayed=True,
            unresolved=stored.unresolved,
            audit={**audit, "replayed": True},
        )

    def _audit(
        self,
        spec: ToolSpec,
        context: CallContext,
        idempotency_key: str | None,
        attempts: int,
        tally: _AttemptTally,
        *,
        ok: bool,
        report: ErrorReport | None = None,
    ) -> Mapping[str, Any]:
        """감사 기록 항목. **주소 · 자격 · 응답 본문이 들어갈 칸이 없음.**"""
        record: dict[str, Any] = {
            "connector_id": spec.connector_id,
            "step_id": spec.step_id,
            "side_effect": spec.side_effect.value,
            "mode": self.adapter.mode.value,
            "transport": self.adapter.transport.label,
            "credential_kind": spec.credential_kind.value,
            "requested_scopes": list(spec.requested_scopes),
            "attempts": attempts,
            "outward_calls": tally.outward_calls,
            "ok": ok,
            "request_id": context.request_id,
        }
        if idempotency_key is not None:
            record["idempotency_key_fingerprint"] = key_fingerprint(idempotency_key)
        if context.on_behalf_of is not None:
            record.update(context.on_behalf_of.as_record())
        if report is not None:
            record["error_class"] = report.error_class.value
            record["error_reason"] = report.reason
        return record
