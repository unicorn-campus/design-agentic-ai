"""도구 명세 그릇과 스키마 바탕. 스키마 본문은 커넥터 파일 1개에 1벌만 두고 여기서 가져다 씀.

용어 1줄 — **부작용** = 그 도구가 바깥 상태를 바꾸는지 여부임. 읽기는 안 바꾸고 쓰기는 바꿈.
"""

from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from .boundary import assert_no_forbidden_keys
from .errors import ConnectorCallFailed, ErrorClass, ErrorReport

__all__ = [
    "SideEffect",
    "BackendKind",
    "CredentialKind",
    "ToolPayload",
    "ToolSpec",
    "validate_input",
    "project_output",
]


class SideEffect(StrEnum):
    """④ 「사용 도구」의 3값을 그대로 씀. 공란을 두지 않음."""

    READ = "읽기"
    WRITE_REVERSIBLE = "쓰기(되돌림 가능)"
    WRITE_IRREVERSIBLE = "쓰기(되돌림 불가)"

    @property
    def is_write(self) -> bool:
        return self is not SideEffect.READ


class BackendKind(StrEnum):
    HTTP = "http"
    MODEL = "model"


class CredentialKind(StrEnum):
    """인증 방식. 자격을 어디에 두고 언제 갱신하는지는 어댑터 안에서만 알게 함."""

    API_KEY = "API 키"
    SERVICE_ACCOUNT = "서비스 자격"


class ToolPayload(BaseModel):
    """입출력 스키마의 바탕. 규격에 없는 칸이 오면 거부함(`extra=forbid`).

    가리기로 대신하지 않음 — ② 경계 미통과 항목은 애초에 칸이 없고, 몰래 실려 오면 입력 오류가 됨.
    """

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=False)


class ToolSpec:
    """도구 1개의 명세. 값은 전부 설계서에서 왔고 개발이 새로 지은 것이 없음."""

    __slots__ = (
        "connector_id",
        "display_name",
        "external_service",
        "trust_boundary",
        "side_effect",
        "usage_condition",
        "step_id",
        "owner_role",
        "owning_service",
        "input_model",
        "output_model",
        "credential_kind",
        "requested_scopes",
        "preconditions",
        "strict_order",
        "approval_marks",
        "idempotency_key_field",
        "external_accepts_idempotency_key",
        "unresolved_marker",
        "failure_marker",
        "backend_kind",
        "design_source",
    )

    def __init__(
        self,
        *,
        connector_id: str,
        display_name: str,
        external_service: str,
        trust_boundary: str,
        side_effect: SideEffect,
        usage_condition: str,
        step_id: str,
        owner_role: str,
        owning_service: str,
        input_model: type[ToolPayload],
        output_model: type[ToolPayload] | None,
        credential_kind: CredentialKind,
        requested_scopes: tuple[str, ...],
        preconditions: tuple[str, ...],
        strict_order: bool,
        approval_marks: tuple[str, ...] = (),
        idempotency_key_field: str | None = None,
        external_accepts_idempotency_key: bool = False,
        unresolved_marker: Mapping[str, Any] | None = None,
        failure_marker: Mapping[str, Any] | None = None,
        backend_kind: BackendKind = BackendKind.HTTP,
        design_source: str = "",
    ) -> None:
        self.connector_id = connector_id
        self.display_name = display_name
        self.external_service = external_service
        self.trust_boundary = trust_boundary
        self.side_effect = side_effect
        self.usage_condition = usage_condition
        self.step_id = step_id
        self.owner_role = owner_role
        self.owning_service = owning_service
        self.input_model = input_model
        self.output_model = output_model
        self.credential_kind = credential_kind
        self.requested_scopes = requested_scopes
        self.preconditions = preconditions
        self.strict_order = strict_order
        self.approval_marks = approval_marks
        self.idempotency_key_field = idempotency_key_field
        self.external_accepts_idempotency_key = external_accepts_idempotency_key
        self.unresolved_marker = unresolved_marker
        self.failure_marker = failure_marker
        self.backend_kind = backend_kind
        self.design_source = design_source
        self._check()

    # -- 등록 시점 자가 점검 ------------------------------------------------
    def _check(self) -> None:
        assert_no_forbidden_keys(
            self.connector_id, self.trust_boundary, self.input_key_names
        )
        assert_no_forbidden_keys(
            self.connector_id, self.trust_boundary, self.output_key_names
        )
        if self.side_effect.is_write and not self.idempotency_key_field:
            raise ValueError(
                f"{self.connector_id}: 쓰기 도구인데 중복 방지 키 칸이 없음"
                " — 8단계는 쓰기 전건에 키를 요구함"
            )
        if self.side_effect is SideEffect.READ and self.idempotency_key_field:
            raise ValueError(
                f"{self.connector_id}: 읽기 도구에는 중복 방지 키를 붙이지 않음"
            )
        if self.side_effect is SideEffect.WRITE_IRREVERSIBLE and not self.approval_marks:
            raise ValueError(
                f"{self.connector_id}: 되돌림 불가 쓰기인데 승인 표시 요구가 비어 있음"
                " — 기본은 거부임(9단계)"
            )
        missing = tuple(m for m in self.approval_marks if m not in self.preconditions)
        if missing:
            raise ValueError(
                f"{self.connector_id}: 승인 표시 {missing}가 사전 조건 목록에 없음"
            )

    # -- 키 이름 ----------------------------------------------------------
    @property
    def input_key_names(self) -> tuple[str, ...]:
        return tuple(self.input_model.model_fields)

    @property
    def output_key_names(self) -> tuple[str, ...]:
        if self.output_model is None:
            return ()
        return tuple(self.output_model.model_fields)

    def __repr__(self) -> str:  # pragma: no cover - 사람이 읽는 용도
        return f"<ToolSpec {self.connector_id} {self.display_name} {self.side_effect.value}>"


def _error_locations(exc: ValidationError) -> tuple[str, ...]:
    names: list[str] = []
    for item in exc.errors():
        location = item.get("loc") or ()
        names.append(".".join(str(part) for part in location) or "<본문>")
    return tuple(dict.fromkeys(names))


def validate_input(spec: ToolSpec, payload: Mapping[str, Any]) -> ToolPayload:
    """규격에 안 맞으면 `입력 오류`임 — 재시도하지 않고 어느 키가 문제인지 적어 올림."""
    try:
        return spec.input_model.model_validate(dict(payload))
    except ValidationError as exc:
        raise ConnectorCallFailed(
            ErrorReport(
                connector_id=spec.connector_id,
                step_id=spec.step_id,
                error_class=ErrorClass.INPUT,
                reason="입력 규격 불일치",
                offending_keys=_error_locations(exc),
                attempts=0,
            )
        ) from None


def project_output(spec: ToolSpec, raw: Mapping[str, Any]) -> dict[str, Any]:
    """바깥 응답을 그대로 상태에 올리지 않음. 규격에 적힌 키만 뽑아 담음."""
    if spec.output_model is None:
        return {}
    declared = set(spec.output_model.model_fields)
    picked = {key: value for key, value in raw.items() if key in declared}
    try:
        model = spec.output_model.model_validate(picked)
    except ValidationError as exc:
        raise ConnectorCallFailed(
            ErrorReport(
                connector_id=spec.connector_id,
                step_id=spec.step_id,
                error_class=ErrorClass.INPUT,
                reason="바깥 응답이 출력 규격과 다름",
                offending_keys=_error_locations(exc),
            )
        ) from None
    return model.model_dump()
