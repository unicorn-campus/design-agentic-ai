"""환경변수 로딩. ⑦ 4-2절 — 비밀값은 **실행 시 환경변수로만** 들어옴.

이미지 레이어에 굽지 않고(⑦ 4-3 위반 1번), 배포 설정 파일에 평문으로 적지
않으며(위반 2번), 로그에 찍지 않음(위반 3번 — masking.py가 담당).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache

from .budget import DEFAULT_MAX_REFRESH_ITER, DEFAULT_MAX_REJECT_ITER


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def _int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    return int(raw) if raw not in (None, "") else default


@dataclass(frozen=True)
class DbAccount:
    """⑦ 4-2절 K-7 ~ K-12 — 이미지별로 다른 계정을 발급함.

    ⑤ 3절 `쓰기 금지 규칙`: 조회 경로는 읽기 전용 계정만 씀.
    """

    user: str
    password: str
    host: str
    port: int
    database: str

    def dsn(self) -> str:
        return (
            f"postgresql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.database}"
        )


@dataclass(frozen=True)
class Settings:
    service: str
    # K-1 ~ K-4 · K-14 외부 서비스 자격증명
    anthropic_api_key: str = field(repr=False, default="")
    llm_model: str = "claude-sonnet-5"
    llm_mode: str = "real"  # real | mock
    weather_mode: str = "mock"
    places_mode: str = "mock"
    push_mode: str = "mock"
    kakao_mode: str = "mock"
    openweather_api_key: str = field(repr=False, default="")
    google_places_api_key: str = field(repr=False, default="")
    # K-5 · K-6 암호화 키 — 서로 다른 키이며 보관 위치도 분리함(⑦ 4-4)
    allergen_key: str = field(repr=False, default="")
    pii_key: str = field(repr=False, default="")
    # K-13 JWT
    jwt_secret: str = field(repr=False, default="")
    jwt_ttl_sec: int = 3600
    # 저장소
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "lunchpick"
    db_rw_user: str = "lp_rw"
    db_rw_password: str = field(repr=False, default="")
    db_ro_user: str = "lp_ro"
    db_ro_password: str = field(repr=False, default="")
    db_obs_user: str = "lp_obs"
    db_obs_password: str = field(repr=False, default="")
    # ④ 10절 반복 상한 — 원문에 값이 없어 태그로 남은 자리(기본값을 밝힘)
    max_reject_iter: int = DEFAULT_MAX_REJECT_ITER
    max_refresh_iter: int = DEFAULT_MAX_REFRESH_ITER
    # ⑥ B-5 확신 스코어 임계값 — `[확인필요: 확신 스코어 임계값]`(원문 부재)
    confidence_threshold: float = 0.35
    # ⑥ G-1 표시명 길이 상한 — `[확인필요: 표시명 길이 상한]`(원문 부재)
    display_name_max_len: int = 60
    # ⑤ `[확인필요: 식당 캐시 갱신 주기]` · ⑦ `[확인필요: 캐시 신선도 상한]`
    cache_freshness_max_sec: int = 86_400
    # 서비스 간 호출
    member_base_url: str = "http://lp-member:8080"
    recommend_base_url: str = "http://lp-recommend:8080"

    def rw(self) -> DbAccount:
        return DbAccount(
            self.db_rw_user, self.db_rw_password, self.db_host, self.db_port, self.db_name
        )

    def ro(self) -> DbAccount:
        return DbAccount(
            self.db_ro_user, self.db_ro_password, self.db_host, self.db_port, self.db_name
        )

    def obs(self) -> DbAccount:
        """DB6 관측 기록 — **쓰기 전용** 계정(⑦ K-12)."""
        return DbAccount(
            self.db_obs_user, self.db_obs_password, self.db_host, self.db_port, self.db_name
        )


@lru_cache(maxsize=None)
def get_settings(service: str = "unknown") -> Settings:
    return Settings(
        service=service,
        anthropic_api_key=_env("ANTHROPIC_API_KEY"),
        llm_model=_env("LP_LLM_MODEL", "claude-sonnet-5"),
        llm_mode=_env("LP_LLM_MODE", "real"),
        weather_mode=_env("LP_WEATHER_MODE", "mock"),
        places_mode=_env("LP_PLACES_MODE", "mock"),
        push_mode=_env("LP_PUSH_MODE", "mock"),
        kakao_mode=_env("LP_KAKAO_MODE", "mock"),
        openweather_api_key=_env("OPENWEATHER_API_KEY"),
        google_places_api_key=_env("GOOGLE_PLACES_API_KEY"),
        allergen_key=_env("LP_ALLERGEN_KEY"),
        pii_key=_env("LP_PII_KEY"),
        jwt_secret=_env("LP_JWT_SECRET", "dev-only"),
        jwt_ttl_sec=_int("LP_JWT_TTL_SEC", 3600),
        db_host=_env("LP_DB_HOST", "localhost"),
        db_port=_int("LP_DB_PORT", 5432),
        db_name=_env("LP_DB_NAME", "lunchpick"),
        db_rw_user=_env("LP_DB_RW_USER", "lp_rw"),
        db_rw_password=_env("LP_DB_RW_PASSWORD", ""),
        db_ro_user=_env("LP_DB_RO_USER", "lp_ro"),
        db_ro_password=_env("LP_DB_RO_PASSWORD", ""),
        db_obs_user=_env("LP_DB_OBS_USER", "lp_obs"),
        db_obs_password=_env("LP_DB_OBS_PASSWORD", ""),
        max_reject_iter=_int("LP_MAX_REJECT_ITER", DEFAULT_MAX_REJECT_ITER),
        max_refresh_iter=_int("LP_MAX_REFRESH_ITER", DEFAULT_MAX_REFRESH_ITER),
        confidence_threshold=float(_env("LP_CONFIDENCE_THRESHOLD", "0.35")),
        display_name_max_len=_int("LP_DISPLAY_NAME_MAX_LEN", 60),
        cache_freshness_max_sec=_int("LP_CACHE_FRESHNESS_MAX_SEC", 86_400),
        member_base_url=_env("LP_MEMBER_BASE_URL", "http://lp-member:8080"),
        recommend_base_url=_env("LP_RECOMMEND_BASE_URL", "http://lp-recommend:8080"),
    )
