"""설정 로더. 값은 전부 환경변수에서 옴 — 이 파일에 시간·재시도·모델 값을 박지 않음."""

from __future__ import annotations

import functools
from enum import StrEnum
from typing import Any

from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

__all__ = [
    "Settings",
    "SettingsMissing",
    "CheckpointBackend",
    "CheckpointFailurePolicy",
    "load_settings",
    "get_settings",
    "reset_settings_cache",
]


class SettingsMissing(RuntimeError):
    """필수 설정이 없음. 프로그램이 뜨는 시점에 이걸 던짐."""


class CheckpointBackend(StrEnum):
    MEMORY = "memory"
    POSTGRES = "postgres"


class CheckpointFailurePolicy(StrEnum):
    """PostgreSQL 체크포인터를 열지 못했을 때의 명시적 동작."""

    FAIL_FAST = "fail_fast"
    MEMORY_FALLBACK_FOR_DEVELOPMENT = "memory_fallback_for_development"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LUNCHPICK_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    step_timeout_ms: dict[str, int] = Field(
        description="단계 식별자 → 시간 제한(밀리초). ③ 4절 「타임아웃(상한)」 열",
    )
    step_retry_count: dict[str, int] = Field(
        description="단계 식별자 → 재시도 횟수. ③ 4절 「재시도」 열",
    )
    step_backoff_ms: dict[str, int] = Field(
        default_factory=dict,
        description="단계 식별자 → 재시도 사이 대기(밀리초). ③이 값을 준 단계만 채움",
    )
    step_retry_conditional: frozenset[str] = Field(
        default_factory=frozenset,
        description="마감선까지 남은 시간이 시간 제한만큼 있을 때만 재시도가 발화하는 단계",
    )
    budget_total_ms: dict[str, int] = Field(
        default_factory=dict,
        description="트리거 접두 → 총 예산(밀리초). ③ 9절 대조 2줄",
    )
    budget_landing_ms: dict[str, int] = Field(
        default_factory=dict,
        description="트리거 접두 → 착지 경로 예산(밀리초). 진입선에서 미리 뺌",
    )
    loop_max_iter: dict[str, int] = Field(
        default_factory=dict,
        description="루프 식별자 → 반복 상한. ③ 8-2절",
    )
    cost_limit_krw_per_request: float | None = Field(
        default=None,
        description="요청 1건당 비용 상한(원). ① 3절 단위 환산",
    )
    llm_provider: str = Field(description="모델 벤더 식별자. 어댑터 모듈을 이 값으로 고름")
    llm_model: str = Field(description="모델 이름")
    llm_api_key: str = Field(description="모델 API 열쇠. 환경 파일에서만 읽음")
    llm_thinking: str | None = Field(
        default=None, description="사고 켬/끔. ④ 「사용 모델」이 정한 값"
    )
    llm_effort: str | None = Field(default=None, description="사고 깊이 단계")
    llm_max_output_tokens: int | None = Field(default=None, description="출력 상한 토큰 수")
    llm_base_url: str | None = Field(default=None, description="모델 API 주소를 갈아 끼울 때만 씀")
    embedding_model: str | None = Field(
        default=None,
        description="취향 임베딩 모델 이름. ⑤가 확정하기 전에는 비움",
    )
    checkpoint_backend: CheckpointBackend = Field(
        default=CheckpointBackend.MEMORY,
        description="중간 저장 장치 백엔드",
    )
    checkpoint_db_url: str | None = Field(
        default=None, description="중간 저장 데이터베이스 접속 문자열. 비밀값"
    )
    checkpoint_failure_policy: CheckpointFailurePolicy = Field(
        default=CheckpointFailurePolicy.FAIL_FAST,
        description=(
            "PostgreSQL 연결·초기화 실패 정책. 운영 기본은 즉시 실패이고, "
            "개발에서만 명시적으로 메모리 대체를 선택함"
        ),
    )
    checkpoint_retention_days: int | None = Field(
        default=None,
        description="중간 저장 보관 기간(일). 값이 오기 전에는 비우고 삭제 배치를 돌리지 않음",
    )
    otlp_endpoint: str | None = Field(
        default=None, description="관측 기록 내보내는 곳. 비우면 표준출력으로만 남김"
    )
    dataset_row_cap: dict[str, int] = Field(
        default_factory=dict,
        description="경로 식별자 → 행 수 상한. ⑤ 「정형 접근 경로」가 값의 주인",
    )
    dataset_seed: int = Field(
        default=0,
        description="합성 시드 난수 씨앗. 같은 값이면 같은 데이터가 나옴",
    )
    dataset_seed_rows: dict[str, int] = Field(
        default_factory=dict,
        description="경로 식별자 → 시드로 만들 행 수. 비우면 그 경로의 행 수 상한만큼 만듦",
    )
    dataset_source_db_url: str | None = Field(
        default=None,
        description="관계형 원천 접속 문자열. 값은 커넥니·배포 몫이며 여기서 정하지 않음",
    )
    dataset_vector_index_url: str | None = Field(
        default=None, description="벡터 인덱스 접속 주소. 제품 미확정이라 비어 있음"
    )
    dataset_cache_url: str | None = Field(
        default=None, description="캐시 접속 주소. 제품 미확정이라 비어 있음"
    )
    dataset_physical_query: dict[str, str] = Field(
        default_factory=dict,
        description="경로 식별자 → 미리 짠 조회문. 물리 표·열 이름이 확정되면 채움",
    )
    dataset_snapshot_dir: str | None = Field(
        default=None, description="원천 스냅샷을 두는 곳. 비우면 패키지 안 기본 폴더를 씀"
    )
    dataset_snapshot_retention_days: dict[str, int] = Field(
        default_factory=dict,
        description="경로 식별자 → 스냅샷 보존 기간(일). ⑤ 「보존·삭제」가 값의 주인",
    )
    dataset_quality_threshold: dict[str, float] = Field(
        default_factory=dict,
        description="품질 항목 이름 → 문턱값. ⑤에 문턱이 없으면 비어 있고 검사가 미확정으로 남음",
    )
    dataset_glossary_dir: str | None = Field(
        default=None, description="용어사전 파일을 두는 곳. 비우면 패키지 안 기본 폴더를 씀"
    )
    knowledge_index_name: dict[str, str] = Field(
        default_factory=dict,
        description="색인 자리 이름 → 색인 이름. ⑤ 「채택 방식별 필수 스펙」 K-1 「인덱스명」",
    )
    knowledge_index_build_suffix: str | None = Field(
        default=None,
        description="색인을 다시 만들 때 붙이는 접미. 되묻기 1 — 새 이름으로 만들고 갈아 끼움",
    )
    knowledge_corpus_scope: str | None = Field(
        default=None, description="색인 대상 범위. ⑤ K-1 「대상 범위 · 기준일」"
    )
    knowledge_corpus_as_of: str | None = Field(
        default=None, description="색인 기준일. ⑤ K-1이 확정 불가로 남긴 칸"
    )
    knowledge_chunking: str | None = Field(
        default=None, description="쪼개는 단위 · 크기 · 겹침. ⑤ K-1은 「해당 없음」임"
    )
    knowledge_embedding_model_version: str | None = Field(
        default=None, description="임베딩 모델 버전. 모델 이름은 `embedding_model`이 가짐"
    )
    knowledge_vector_index_product: str | None = Field(
        default=None, description="벡터 색인 제품 이름. 코드에 박지 않고 설정으로만 받음"
    )
    knowledge_search_mode: str | None = Field(
        default=None, description="검색 방식. ⑤ K-1 「검색 방식」"
    )
    knowledge_top_k: int | None = Field(
        default=None, description="가져올 후보 수. ⑤ K-1 「top-k」"
    )
    knowledge_rerank_enabled: bool | None = Field(
        default=None, description="재정렬을 쓰나. ⑤ K-1 「리랭킹 여부」"
    )
    knowledge_rerank_weights: dict[str, float] = Field(
        default_factory=dict,
        description="재정렬 축 → 가중치. ⑤에 값이 없어 비어 있으면 순서를 바꾸지 않음",
    )
    knowledge_rerank_keep: int | None = Field(
        default=None, description="재정렬 뒤 남길 건수. ⑤ K-1 「리랭킹 여부」 칸의 최종 건수"
    )
    knowledge_metadata_filter_keys: tuple[str, ...] = Field(
        default=(),
        description="메타데이터 거르기 키. 이름의 주인은 ④ 「입출력 형식」임",
    )
    knowledge_attribute_axes: dict[str, str] = Field(
        default_factory=dict,
        description="속성 필터 축 → 성립 여부. ⑤ K-2 「필터 축」 · 「성립 여부」",
    )
    knowledge_radius_m: int | None = Field(
        default=None, description="후보 반경(미터). ⑤ K-2 「필터 축」 거리"
    )
    knowledge_sort_primary: str | None = Field(
        default=None, description="기본 정렬 기준. ⑤ K-2 「정렬 기준」"
    )
    knowledge_glossary_apply_points: dict[str, str] = Field(
        default_factory=dict,
        description="사전 자리 → 적용 지점. ⑤ K-3 「적용 지점」",
    )
    knowledge_query_expansion_enabled: bool | None = Field(
        default=None, description="질의 확장을 쓰나. ⑤ K-3 ⓐ 「적용 지점」"
    )
    knowledge_result_merge: str | None = Field(
        default=None, description="경로가 여럿일 때 합치는 규칙. 되묻기 3 — 따로 돌려줌"
    )
    knowledge_result_cache_ttl_s: int | None = Field(
        default=None, description="검색 결과를 잠시 두는 시간(초). 되묻기 4 — 비우면 두지 않음"
    )
    knowledge_low_confidence_signal: str | None = Field(
        default=None, description="낮은 신뢰를 가르는 신호. 되묻기 5 — 후보 수 0건을 씀"
    )

    def knowledge_index_name_for(self, role: str) -> str:
        """색인 이름을 설정에서만 읽음. 없으면 지어내지 않고 실패함."""
        try:
            return self.knowledge_index_name[role]
        except KeyError as exc:
            raise SettingsMissing(f"색인 자리 {role}의 이름이 설정에 없음") from exc

    def knowledge_top_k_value(self) -> int:
        if self.knowledge_top_k is None:
            raise SettingsMissing("가져올 후보 수가 설정에 없음 — ⑤ K-1 top-k를 채워야 함")
        return self.knowledge_top_k

    def dataset_row_cap_for(self, path_id: str) -> int:
        """행 수 상한을 설정에서만 읽음. 없으면 짐작하지 않고 실패함."""
        try:
            return self.dataset_row_cap[path_id]
        except KeyError as exc:
            raise SettingsMissing(f"경로 {path_id}의 행 수 상한이 설정에 없음") from exc

    def dataset_seed_row_count(self, path_id: str) -> int:
        """시드 건수. 따로 주지 않으면 그 경로의 행 수 상한만큼 만듦."""
        return self.dataset_seed_rows.get(path_id, self.dataset_row_cap_for(path_id))

    @model_validator(mode="after")
    def _postgres_needs_url(self) -> Settings:
        if self.checkpoint_backend is CheckpointBackend.POSTGRES and not self.checkpoint_db_url:
            raise ValueError(
                "checkpoint_backend가 postgres면 LUNCHPICK_CHECKPOINT_DB_URL이 있어야 함"
            )
        return self

    def timeout_ms(self, step_id: str) -> int:
        try:
            return self.step_timeout_ms[step_id]
        except KeyError as exc:
            raise SettingsMissing(f"단계 {step_id}의 시간 제한이 설정에 없음") from exc

    def retry_count(self, step_id: str) -> int:
        try:
            return self.step_retry_count[step_id]
        except KeyError as exc:
            raise SettingsMissing(f"단계 {step_id}의 재시도 횟수가 설정에 없음") from exc

    def backoff_ms(self, step_id: str) -> int:
        return self.step_backoff_ms.get(step_id, 0)

    def is_retry_conditional(self, step_id: str) -> bool:
        return step_id in self.step_retry_conditional

    def entry_deadline_span_ms(self, trigger_prefix: str) -> int:
        """진입선까지 쓸 수 있는 시간. 착지 경로를 미리 뺀 값이며 이중 계상하지 않음."""
        try:
            total = self.budget_total_ms[trigger_prefix]
        except KeyError as exc:
            raise SettingsMissing(f"트리거 {trigger_prefix}의 총 예산이 설정에 없음") from exc
        return total - self.budget_landing_ms.get(trigger_prefix, 0)

    def max_iter(self, loop_id: str) -> int:
        try:
            return self.loop_max_iter[loop_id]
        except KeyError as exc:
            raise SettingsMissing(f"루프 {loop_id}의 반복 상한이 설정에 없음") from exc


def load_settings(**overrides: Any) -> Settings:
    """설정을 읽음. 필수 값이 없으면 여기서 바로 실패함."""
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        raise SettingsMissing(str(exc)) from exc


@functools.lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()


if __name__ == "__main__":
    settings = load_settings()
    print(
        "설정 확인 통과 —"
        f" 단계 {len(settings.step_timeout_ms)}개"
        f" · 중간 저장 {settings.checkpoint_backend.value}"
        f" · 모델 벤더 {settings.llm_provider}"
    )
