"""Indexer와 Retriever가 바이트 단위로 공유하는 설정 로더."""

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
LAB_ROOT = APP_DIR.parents[1]


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


def _default_chroma_path() -> Path:
    if APP_DIR.name == "indexer":
        return APP_DIR / "data" / "chroma"
    return APP_DIR.parent / "indexer" / "data" / "chroma"


def _default_transform_cache_path() -> Path:
    return APP_DIR / "data" / "transform_cache.json"


# 계획서 1-3절과 1-3-2절의 모든 키를 한 곳에서만 허용함.
_SPECS: dict[str, _Spec] = {
    "CHROMA_PATH": _Spec(_default_chroma_path, _path),
    "CHROMA_COLLECTION": _Spec("card_docs", _text),
    "EMBED_MODEL": _Spec("nlpai-lab/KURE-v2", _text),
    "RERANK_MODEL": _Spec("BAAI/bge-reranker-v2-m3", _text),
    "LLM_PROVIDER": _Spec("groq", _choice("groq", "claude", "openai")),
    "GROQ_API_KEY": _Spec(None, _text, True),
    "GROQ_MODEL": _Spec("openai/gpt-oss-120b", _text),
    "CLAUDE_API_KEY": _Spec(None, _text, True, ("ANTHROPIC_API_KEY",)),
    "CLAUDE_MODEL": _Spec("claude-opus-5", _text),
    "OPENAI_API_KEY": _Spec(None, _text, True),
    "OPENAI_MODEL": _Spec(None, _text),
    "LLM_TIMEOUT_SECONDS": _Spec(60, _positive_float),
    "LLM_MAX_TOKENS_ANSWER": _Spec(2000, _positive_int),
    "MAX_LLM_CALLS_CLI": _Spec(8, _positive_int),
    "MAX_LLM_CALLS_PER_REQUEST": _Spec(2, _positive_int),
    "MAX_LLM_CALLS_TOTAL": _Spec(200, _positive_int),
    "REQUEST_TIMEOUT_SECONDS": _Spec(120, _positive_float),
    "API_HOST": _Spec("127.0.0.1", _text),
    "API_PORT": _Spec(8001, _positive_int),
    "TOP_K_DEFAULT": _Spec(5, _positive_int),
    "CANDIDATE_MULTIPLIER": _Spec(4, _positive_int),
    "HYBRID_WEIGHT_BM25": _Spec(0.4, _non_negative_float),
    "HYBRID_WEIGHT_VECTOR": _Spec(0.6, _non_negative_float),
    "ANSWER_GATE_THRESHOLD": _Spec(0.62, _unit_float),
    "RERANK_MAX_LENGTH": _Spec(512, _positive_int),
    "TRANSFORM_MODE": _Spec("off", _choice("off", "auto")),
    "TRANSFORM_GATE_THRESHOLD": _Spec(0.70, _unit_float),
    "TRANSFORM_RRF_K": _Spec(60, _positive_int),
    "TRANSFORM_ORIGINAL_WEIGHT": _Spec(0.5, _unit_float),
    "TRANSFORM_ORIGINAL_WEIGHT_DECOMPOSITION": _Spec(0.1, _unit_float),
    "TRANSFORM_PER_QUERY_TOP_K": _Spec(3, _positive_int),
    "TRANSFORM_MULTI_COUNT": _Spec(3, _positive_int),
    "TRANSFORM_DECOMPOSITION_MIN": _Spec(2, _positive_int),
    "TRANSFORM_DECOMPOSITION_MAX": _Spec(4, _positive_int),
    "TRANSFORM_CACHE_PATH": _Spec(_default_transform_cache_path, _path),
    "LLM_MAX_TOKENS_ROUTER": _Spec(500, _positive_int),
    "RECURSION_LIMIT": _Spec(25, _positive_int),
    # 3 이상이면 Retriever 최악 경로가 recursion_limit 25를 넘음.
    "MAX_REPAIRS": _Spec(2, _positive_int),
    "EMBED_BATCH_SIZE": _Spec(32, _positive_int),
    "UPSERT_RETRY": _Spec(1, _positive_int),
    "CHUNK_MAX_CHARS": _Spec(600, _positive_int),
    "CHUNK_OVERLAP": _Spec(80, _positive_int),
    "CHUNK_D2_OVERLAP": _Spec(0, _non_negative_int),
    "CHUNK_TURNS_PER_CHUNK": _Spec(4, _positive_int),
    "CHUNK_OVERLAP_TURNS": _Spec(1, _positive_int),
    "MAX_INPUT_TOKENS": _Spec(8192, _positive_int),
    "TIMEOUT_PDF_PER_FILE": _Spec(60, _positive_float),
    "TIMEOUT_CHUNK_PER_DOC": _Spec(30, _positive_float),
    "TIMEOUT_EMBED_BATCH": _Spec(120, _positive_float),
    "TIMEOUT_VECTOR_SEARCH": _Spec(10, _positive_float),
    "TIMEOUT_RERANK": _Spec(60, _positive_float),
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

    if selected["TRANSFORM_DECOMPOSITION_MIN"] > selected["TRANSFORM_DECOMPOSITION_MAX"]:
        raise LLMConfigError(
            "TRANSFORM_DECOMPOSITION_MIN은 TRANSFORM_DECOMPOSITION_MAX 이하여야 함"
        )
    if selected["HYBRID_WEIGHT_BM25"] + selected["HYBRID_WEIGHT_VECTOR"] <= 0:
        raise LLMConfigError("HYBRID_WEIGHT_BM25와 HYBRID_WEIGHT_VECTOR의 합은 양수여야 함")
    if selected["MAX_REPAIRS"] >= 3:
        raise LLMConfigError("MAX_REPAIRS는 RECURSION_LIMIT=25에서 2 이하여야 함")

    return Settings(MappingProxyType(selected), MappingProxyType(sources))
