from __future__ import annotations

from help_desk_guardrails import SensitiveDataMasker, load_policy
from help_desk_runtime.settings import RuntimeSettings

from .boundary import GuardrailBoundary


def build_boundary(settings: RuntimeSettings) -> GuardrailBoundary:
    return GuardrailBoundary(
        load_policy(),
        SensitiveDataMasker(settings.masking_salt.get_secret_value()),
    )
