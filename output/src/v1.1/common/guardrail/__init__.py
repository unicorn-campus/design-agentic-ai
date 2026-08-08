"""검사 계층 — 입력측 · 도구 호출측 · 출력측 3지점 검사와 가리기 매핑.

규칙 원본은 `common/guardrail_rules.toml` **1벌**뿐임. 조건을 코드에 흩어 놓지 않음.
자세한 설명과 ⑥ 대응표는 이 폴더의 `README.md`에 있음.
"""

from __future__ import annotations

from .errors import BlockDecision, GuardrailBlocked, RETRYABLE_CLASSES, ToolErrorClass
from .hooks import (
    GuardrailAuditRecorder,
    GuardrailInspector,
    GuardrailRedactor,
    build_guardrail_hooks,
)
from .input_guard import InputGuard, InputVerdict, neutralize_tag_lookalikes, wrap_external_text
from .masking import (
    MASK_METHODS,
    RECORD_PATHS,
    MaskParams,
    MaskPath,
    Masker,
    get_masker,
    irreversible_hash,
)
from .output_guard import OutputFinding, OutputGuard, OutputVerdict
from .rules import (
    HUMAN_GATE_MODES,
    REGULATED_NO_GATE,
    RULES_PATH_ENV,
    RuleBook,
    RuleBookInvalid,
    default_rules_path,
    get_rulebook,
    load_rulebook,
    reset_rulebook_cache,
)
from .tool_guard import (
    ApprovalEvidence,
    ApprovalLedger,
    ToolCallCounter,
    ToolDecision,
    ToolGuard,
)

__all__ = [
    "HUMAN_GATE_MODES",
    "MASK_METHODS",
    "RECORD_PATHS",
    "REGULATED_NO_GATE",
    "RETRYABLE_CLASSES",
    "RULES_PATH_ENV",
    "ApprovalEvidence",
    "ApprovalLedger",
    "BlockDecision",
    "GuardrailAuditRecorder",
    "GuardrailBlocked",
    "GuardrailInspector",
    "GuardrailRedactor",
    "InputGuard",
    "InputVerdict",
    "MaskParams",
    "MaskPath",
    "Masker",
    "OutputFinding",
    "OutputGuard",
    "OutputVerdict",
    "RuleBook",
    "RuleBookInvalid",
    "ToolCallCounter",
    "ToolDecision",
    "ToolErrorClass",
    "ToolGuard",
    "build_guardrail_hooks",
    "default_rules_path",
    "get_masker",
    "get_rulebook",
    "irreversible_hash",
    "load_rulebook",
    "neutralize_tag_lookalikes",
    "reset_rulebook_cache",
    "wrap_external_text",
]
