from __future__ import annotations

from functools import cached_property
from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from .budget import StageBudget


STAGE_IDS = (
    "S_R1", "S_R2", "S_R3", "S_R4", "S_R5",
    "S_R6", "S_R7", "S_R8", "S_R9", "S_R10",
    "S_B1", "S_B2", "S_B3", "S_B4", "S_B5",
    "S_B6", "S_B7", "S_B8", "S_B9", "S_B10",
    "S_E1", "S_E2", "S_E3", "S_E4", "S_E5", "S_E6", "S_E7",
)


class RuntimeSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HELP_DESK_",
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
        case_sensitive=False,
    )

    llm_provider: str
    llm_model: str
    llm_api_key: SecretStr
    llm_reasoning_enabled: bool = True
    llm_temperature: float | None = None
    llm_max_tokens: int | None = None

    checkpoint_backend: Literal["memory", "sqlite"] = "sqlite"
    checkpoint_uri: str
    checkpoint_encryption_key: SecretStr
    checkpoint_w1_retention_ms: int
    checkpoint_w2_retention_ms: int
    checkpoint_w3_retention_ms: int

    analytics_base_url: str | None = None
    analytics_timeout_seconds: float | None = None
    dataset_s_r4_max_rows: int | None = None
    dataset_s_b2_max_rows: int | None = None
    dataset_s_b4_max_rows: int | None = None
    dataset_seed: int | None = None
    dataset_s_r4_seed_rows: int | None = None
    dataset_s_b2_seed_rows: int | None = None
    dataset_s_b4_seed_rows: int | None = None
    dataset_snapshot_dir: str | None = None
    glossary_postgres_dsn: SecretStr | None = None

    w1_total_budget_ms: int
    w2_total_budget_ms: int
    w3_total_budget_ms: int

    s_r1_timeout_ms: int
    s_r1_retry_count: int
    s_r2_timeout_ms: int
    s_r2_retry_count: int
    s_r3_timeout_ms: int
    s_r3_retry_count: int
    s_r4_timeout_ms: int
    s_r4_retry_count: int
    s_r5_timeout_ms: int
    s_r5_retry_count: int
    s_r6_timeout_ms: int
    s_r6_retry_count: int
    s_r7_timeout_ms: int
    s_r7_retry_count: int
    s_r8_timeout_ms: int
    s_r8_retry_count: int
    s_r9_timeout_ms: int
    s_r9_retry_count: int
    s_r10_timeout_ms: int
    s_r10_retry_count: int
    s_b1_timeout_ms: int
    s_b1_retry_count: int
    s_b2_timeout_ms: int
    s_b2_retry_count: int
    s_b3_timeout_ms: int
    s_b3_retry_count: int
    s_b4_timeout_ms: int
    s_b4_retry_count: int
    s_b5_timeout_ms: int
    s_b5_retry_count: int
    s_b6_timeout_ms: int
    s_b6_retry_count: int
    s_b7_timeout_ms: int
    s_b7_retry_count: int
    s_b8_timeout_ms: int
    s_b8_retry_count: int
    s_b9_timeout_ms: int
    s_b9_retry_count: int
    s_b10_timeout_ms: int
    s_b10_retry_count: int
    s_e1_timeout_ms: int
    s_e1_retry_count: int
    s_e2_timeout_ms: int
    s_e2_retry_count: int
    s_e3_timeout_ms: int
    s_e3_retry_count: int
    s_e4_timeout_ms: int
    s_e4_retry_count: int
    s_e5_timeout_ms: int
    s_e5_retry_count: int
    s_e6_timeout_ms: int
    s_e6_retry_count: int
    s_e7_timeout_ms: int
    s_e7_retry_count: int

    @cached_property
    def stage_budgets(self) -> dict[str, StageBudget]:
        return {
            stage_id.replace("_", "-"): StageBudget(
                timeout_ms=getattr(self, f"{stage_id.lower()}_timeout_ms"),
                retry_count=getattr(self, f"{stage_id.lower()}_retry_count"),
            )
            for stage_id in STAGE_IDS
        }
