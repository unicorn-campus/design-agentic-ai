"""Indexer 실행에 필요한 설정을 읽고 검증하는 로더."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping

from dotenv import dotenv_values
from pydantic import SecretStr


APP_DIR = Path(__file__).resolve().parents[1]
LAB_ROOT = APP_DIR.parents[1]   # hybrid-ai-lab


class LLMConfigError(ValueError):
    """설정값이 없거나 안전하게 변환할 수 없을 때 발생함."""


@dataclass(frozen=True)
class Settings:
    """허용된 설정값과 각 값의 출처를 보관하는 불변 객체."""

    values: Mapping[str, Any]
    sources: Mapping[str, str]

    def __getattr__(self, name: str) -> Any:
        try:
            return self.values[name]
        except KeyError as error:
            raise AttributeError(name) from error

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)


@dataclass(frozen=True)
class _Spec:
    default: Any | Callable[[], Any]
    parser: Callable[[str, Any], Any]
    secret: bool = False
    aliases: tuple[str, ...] = ()


def _text(name: str, value: Any) -> str:
    del name
    return str(value).strip()


def _positive_int(name: str, value: Any) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise LLMConfigError(f"{name}은 양의 정수여야 함") from error
    if parsed <= 0:
        raise LLMConfigError(f"{name}은 양의 정수여야 함")
    return parsed


def _non_negative_int(name: str, value: Any) -> int:
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError) as error:
        raise LLMConfigError(f"{name}은 0 이상의 정수여야 함") from error
    if parsed < 0:
        raise LLMConfigError(f"{name}은 0 이상의 정수여야 함")
    return parsed


def _positive_float(name: str, value: Any) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as error:
        raise LLMConfigError(f"{name}은 양수여야 함") from error
    if not math.isfinite(parsed) or parsed <= 0:
        raise LLMConfigError(f"{name}은 양수여야 함")
    return parsed


def _non_negative_float(name: str, value: Any) -> float:
    try:
        parsed = float(str(value).strip())
    except (TypeError, ValueError) as error:
        raise LLMConfigError(f"{name}은 0 이상의 수여야 함") from error
    if not math.isfinite(parsed) or parsed < 0:
        raise LLMConfigError(f"{name}은 0 이상의 수여야 함")
    return parsed


def _unit_float(name: str, value: Any) -> float:
    parsed = _positive_float(name, value)
    if parsed > 1:
        raise LLMConfigError(f"{name}은 0 초과 1 이하여야 함")
    return parsed


def _path(name: str, value: Any) -> Path:
    del name
    path = Path(str(value).strip()).expanduser()
    return path if path.is_absolute() else APP_DIR / path


def _choice(*allowed: str) -> Callable[[str, Any], str]:
    def parse(name: str, value: Any) -> str:
        parsed = str(value).strip().lower()
        if parsed not in allowed:
            raise LLMConfigError(f"{name}은 다음 중 하나여야 함: {', '.join(allowed)}")
        return parsed

    return parse


# Indexer 산출물 경로. 두 서비스가 같은 곳을 가리켜야 하므로 lab 루트에서 내려가는
# 절대 경로로 적음. 예전에는 APP_DIR.name으로 "내가 Indexer인가"를 판별했으나,
# 폴더가 옮겨질 때마다 이름과 깊이가 함께 바뀌어 조용히 어긋났음.
def _default_chroma_path() -> Path:
    return LAB_ROOT / "indexer" / "vector-bm25" / "data" / "chroma"


def _default_search_index_root() -> Path:
    return LAB_ROOT / "indexer" / "vector-bm25" / "data" / "search_indexes"


# 계획서 1-3절과 1-3-2절의 모든 키를 한 곳에서만 허용함.
_SPECS: dict[str, _Spec] = {
    "VECTOR_STORE_BACKEND": _Spec("chroma", _choice("chroma", "memory")),  # 벡터 저장소 어댑터
    "CHROMA_PATH": _Spec(_default_chroma_path, _path),  # Chroma 벡터 DB가 저장된 디렉터리
    "CHROMA_COLLECTION": _Spec("card_docs", _text),  # 검색할 Chroma 컬렉션 이름
    "EMBED_MODEL": _Spec("nlpai-lab/KURE-v2", _text),  # 질문을 벡터로 변환할 임베딩 모델
    "SEARCH_INDEX_ROOT": _Spec(_default_search_index_root, _path),  # 활성 corpus·BM25S 세대 루트
    "KOREAN_USER_DICTIONARY": _Spec(None, _path),  # 카드명·상품명 한국어 사용자 사전
    "KOREAN_TOKENIZER_WORKERS": _Spec(1, _positive_int),  # Kiwi 색인 배치 작업자 수
    "KOREAN_OOV_MIN_COUNT": _Spec(10, _positive_int),  # 사용자 사전 후보의 최소 corpus 빈도
    "KOREAN_OOV_MIN_SCORE": _Spec(0.25, _non_negative_float),  # 사용자 사전 후보의 최소 Kiwi 점수
    "BM25_K1": _Spec(1.5, _positive_float),  # BM25 단어 빈도 포화 계수
    "BM25_B": _Spec(0.75, _unit_float),  # BM25 문서 길이 보정 계수
    "RECURSION_LIMIT": _Spec(25, _positive_int),  # LangGraph 한 실행에서 허용할 최대 진행 단계 수
    "EMBED_BATCH_SIZE": _Spec(32, _positive_int),  # 임베딩·벡터 저장에서 한 번에 처리할 청크 수
    "CHUNK_MAX_CHARS": _Spec(600, _positive_int),  # 청크 하나의 최대 글자 수
    "CHUNK_OVERLAP": _Spec(80, _positive_int),  # 일반 청크 사이에 겹쳐 넣을 글자 수
    "CHUNK_D2_OVERLAP": _Spec(0, _non_negative_int),  # D2 청크 사이에 겹쳐 넣을 글자 수
    "CHUNK_TURNS_PER_CHUNK": _Spec(4, _positive_int),  # 상담 청크 하나에 넣을 대화 턴 수
    "CHUNK_OVERLAP_TURNS": _Spec(1, _positive_int),  # 상담 청크 사이에 겹쳐 넣을 대화 턴 수
    "MAX_INPUT_TOKENS": _Spec(8192, _positive_int),  # 청크 하나에 허용할 최대 입력 토큰 수
    "TIMEOUT_PDF_PER_FILE": _Spec(60, _positive_float),  # PDF 파일 하나의 추출 제한 시간(초)
    "TIMEOUT_CHUNK_PER_DOC": _Spec(30, _positive_float),  # 입력 문서 하나의 청킹 제한 시간(초)
    "TIMEOUT_EMBED_BATCH": _Spec(120, _positive_float),  # 임베딩·벡터 저장 배치의 제한 시간(초)
}


def _present(value: Any) -> bool:
    return value is not None and (not isinstance(value, str) or bool(value.strip()))


def _cli_value(overrides: Mapping[str, Any], name: str) -> Any:
    for candidate in (name, name.lower(), name.lower().replace("_", "-")):
        value = overrides.get(candidate)
        if _present(value):
            return value
    return None


def _source_value(values: Mapping[str, Any], name: str, aliases: tuple[str, ...]) -> tuple[Any, str]:
    for candidate in (name, *aliases):
        value = values.get(candidate)
        if _present(value):
            return value, candidate
    return None, name


def load_settings(cli_overrides: Mapping[str, Any] | None = None) -> Settings:
    """CLI → 환경변수 → 앱 .env → Lab .env → 기본값 순으로 값을 선택함."""

    overrides = cli_overrides or {}
    app_env = dotenv_values(APP_DIR / ".env")
    lab_env = dotenv_values(LAB_ROOT / ".env")
    selected: dict[str, Any] = {}
    sources: dict[str, str] = {}

    for name, spec in _SPECS.items():
        raw = _cli_value(overrides, name)
        source, source_name = "cli", name
        if not _present(raw):
            raw, source_name = _source_value(os.environ, name, spec.aliases)
            source = "environment"
        if not _present(raw):
            raw, source_name = _source_value(app_env, name, spec.aliases)
            source = "app_env"
        if not _present(raw):
            raw, source_name = _source_value(lab_env, name, spec.aliases)
            source = "lab_env"
        if not _present(raw):
            raw = spec.default() if callable(spec.default) else spec.default
            source, source_name = "default", name

        parsed = None if raw is None else spec.parser(name, raw)
        selected[name] = SecretStr(parsed) if parsed is not None and spec.secret else parsed
        sources[name] = source if source_name == name else f"{source}:{source_name}"

    return Settings(MappingProxyType(selected), MappingProxyType(sources))
