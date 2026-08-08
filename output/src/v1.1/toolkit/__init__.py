"""도구 계층 공통 뼈대 — 오류 분류 · 인증 · 승인 문 · 중복 방지 키 · 감싸개 호출.

여기에는 **커넥터가 없음.** 커넥터 어댑터는 `services/{서비스}/tools/` 아래에 1개 = 1파일로 있음.
"""

from .approval import CallBudget, NoOpCallBudget, require_approval, require_preconditions
from .auth import (
    CREDENTIAL_ENV_FIELD,
    REQUESTED_SCOPES,
    ApiKeyCredential,
    Credential,
    ModelKeyCredential,
    OnBehalfOf,
    ServiceAccountCredential,
    build_credential,
)
from .base_adapter import HttpConnector, MockConnector, ModelConnector
from .boundary import (
    FORBIDDEN_KEYS_BY_BOUNDARY,
    GLOBAL_FORBIDDEN_KEYS,
    assert_no_forbidden_keys,
    forbidden_keys_for,
)
from .errors import (
    RETRYABLE_CLASSES,
    ApprovalMissing,
    ConnectorCallFailed,
    ConnectorNotConfigured,
    ConnectorRetryable,
    ErrorClass,
    ErrorReport,
    IdempotencyKeyMissing,
    PreconditionNotMet,
)
from .idempotency import (
    InMemoryResultStore,
    ResultStore,
    StoredResult,
    build_result_store,
    connector_idempotency_key,
    key_fingerprint,
)
from .runner import CallContext, ConnectorAdapter, ConnectorResult, ConnectorTool
from .schema import (
    BackendKind,
    CredentialKind,
    SideEffect,
    ToolPayload,
    ToolSpec,
    project_output,
    validate_input,
)
from .settings import (
    ConnectorMode,
    EndpointConfig,
    ToolSettings,
    get_tool_settings,
    load_tool_settings,
    reset_tool_settings_cache,
)
from .transport import (
    HttpTransport,
    NullTransport,
    Transport,
    TransportReply,
    classify_http_status,
    classify_transport_exception,
)

__all__ = [
    "CREDENTIAL_ENV_FIELD",
    "FORBIDDEN_KEYS_BY_BOUNDARY",
    "GLOBAL_FORBIDDEN_KEYS",
    "REQUESTED_SCOPES",
    "RETRYABLE_CLASSES",
    "ApiKeyCredential",
    "ApprovalMissing",
    "BackendKind",
    "CallBudget",
    "CallContext",
    "ConnectorAdapter",
    "ConnectorCallFailed",
    "ConnectorMode",
    "ConnectorNotConfigured",
    "ConnectorResult",
    "ConnectorRetryable",
    "ConnectorTool",
    "Credential",
    "CredentialKind",
    "EndpointConfig",
    "ErrorClass",
    "ErrorReport",
    "HttpConnector",
    "HttpTransport",
    "IdempotencyKeyMissing",
    "InMemoryResultStore",
    "MockConnector",
    "ModelConnector",
    "ModelKeyCredential",
    "NoOpCallBudget",
    "NullTransport",
    "OnBehalfOf",
    "PreconditionNotMet",
    "ResultStore",
    "ServiceAccountCredential",
    "SideEffect",
    "StoredResult",
    "ToolPayload",
    "ToolSettings",
    "ToolSpec",
    "Transport",
    "TransportReply",
    "assert_no_forbidden_keys",
    "build_credential",
    "build_result_store",
    "classify_http_status",
    "classify_transport_exception",
    "connector_idempotency_key",
    "forbidden_keys_for",
    "get_tool_settings",
    "key_fingerprint",
    "load_tool_settings",
    "project_output",
    "require_approval",
    "require_preconditions",
    "reset_tool_settings_cache",
    "validate_input",
]
