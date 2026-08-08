"""가리기(마스킹) 매핑 1벌.

가리기(마스킹) = 민감한 값을 별표나 뒤 4자리만 남기는 식으로 바꿔 남기는 일임.

**출력 직전 1회만 가리지 않음.** 기록 4경로(관측 기록 · 오류 스택 · 감사 · 접근 기록)와
사용자 응답 경로가 **같은 매핑 1벌**을 지남. 경로마다 따로 만들지 않음.

되돌릴 수 있게 만들지 않음(3단계 되묻기 기본값) — 해시는 한 방향이고 되돌릴 표를 두지 않음.
되돌릴 수 있게 하면 열쇠가 또 하나 생김.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from .rules import RuleBook, RuleBookInvalid, get_rulebook

__all__ = [
    "MaskParams",
    "MaskPath",
    "RECORD_PATHS",
    "MASK_METHODS",
    "Masker",
    "get_masker",
    "irreversible_hash",
]


class MaskPath(StrEnum):
    """가리기가 걸리는 자리. 앞 4개가 8단계가 요구한 기록 4경로임."""

    OBSERVABILITY = "observability"   # 관측 기록의 입력 요약 · 스팬 속성
    ERROR_STACK = "error_stack"       # 오류 메시지 · 예외 스택
    AUDIT = "audit"                   # 감사 기록의 변경 전후 값
    ACCESS_LOG = "access_log"         # 개인정보 접근 기록
    RESPONSE = "response"             # 화면 · 응답 · 발송 본문


RECORD_PATHS: tuple[MaskPath, ...] = (
    MaskPath.OBSERVABILITY,
    MaskPath.ERROR_STACK,
    MaskPath.AUDIT,
    MaskPath.ACCESS_LOG,
)
"""8단계가 하나라도 빠지면 시험을 실패로 처리하라고 한 4경로."""


@dataclass(frozen=True, slots=True)
class MaskParams:
    """가리는 방법의 자릿수. ⑥ 9절 방법 글에 적힌 숫자를 설정에서 읽어 옴 — 코드에 박지 않음."""

    last_n: int
    hash_prefix_len: int
    email_local_keep: int
    stars: str
    substitute_text: str

    @classmethod
    def from_rulebook(cls, book: RuleBook) -> MaskParams:
        params = book.raw["mask_params"]
        return cls(
            last_n=int(params["last_n"]),
            hash_prefix_len=int(params["hash_prefix_len"]),
            email_local_keep=int(params["email_local_keep"]),
            stars=str(params["stars"]),
            substitute_text=str(params["substitute_text"]),
        )


def irreversible_hash(value: Any) -> str:
    """되돌릴 수 없는 표식. 되돌릴 표를 두지 않으므로 원문을 되살릴 수단이 없음."""
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


# --- 가리는 방법 -----------------------------------------------------------
# 이 함수 이름이 이 산출물이 소유하는 `가리기 방법 이름`임.
# 반환값이 `None`이면 그 칸을 아예 지움(칸을 만들지 않음).


def _all_stars(value: Any, p: MaskParams) -> Any:
    return p.stars


def _token_id_only(value: Any, p: MaskParams) -> Any:
    return {"token_id": irreversible_hash(value)[: p.hash_prefix_len]}


def _email_local2_or_hash12(value: Any, p: MaskParams) -> Any:
    text = str(value)
    if "@" in text:
        local, _, domain = text.partition("@")
        return f"{local[: p.email_local_keep]}{p.stars}@{domain}"
    return irreversible_hash(text)[: p.hash_prefix_len]


def _region_label_only(value: Any, p: MaskParams) -> Any:
    return {"region_label": "[확인필요: 좌표 로그 정밀도 규칙]"}


def _count_only(value: Any, p: MaskParams) -> Any:
    if isinstance(value, (list, tuple, set, dict)):
        return {"count": len(value)}
    if value in (None, ""):
        return {"count": 0}
    return {"count": 1}


def _bool_only(value: Any, p: MaskParams) -> Any:
    return {"applied": bool(value)}


def _drop_field(value: Any, p: MaskParams) -> Any:
    return None


def _last4(value: Any, p: MaskParams) -> Any:
    text = str(value)
    return f"{p.stars}{text[-p.last_n :]}" if len(text) > p.last_n else p.stars


def _count_and_category(value: Any, p: MaskParams) -> Any:
    if isinstance(value, list):
        codes = sorted(
            {
                str(item.get("category_code"))
                for item in value
                if isinstance(item, Mapping) and item.get("category_code") is not None
            }
        )
        return {"count": len(value), "category_codes": codes}
    return {"count": _count_only(value, p)["count"], "category_codes": []}


def _dim_and_time(value: Any, p: MaskParams) -> Any:
    dim = len(value) if isinstance(value, (list, tuple)) else None
    return {"dimensions": dim, "updated_at": "[기록 시각으로 채움]"}


def _separate_store(value: Any, p: MaskParams) -> Any:
    return {
        "stored_separately": True,
        "correlation_key": irreversible_hash(value)[: p.hash_prefix_len],
    }


def _first_char_stars(value: Any, p: MaskParams) -> Any:
    text = str(value)
    return f"{text[:1]}{p.stars}" if text else p.stars


def _allow_value(value: Any, p: MaskParams) -> Any:
    """⑥이 값 기록을 명시로 허용한 자리(감사 필수 항목)."""
    return value


def _not_recorded(value: Any, p: MaskParams) -> Any:
    return None


def _hash_only(value: Any, p: MaskParams) -> Any:
    return irreversible_hash(value)


def _sentence_or_discard(value: Any, p: MaskParams) -> Any:
    """문장 원문 기록은 허용함. 폐기는 출력측 검사가 판정하며 여기서 문장을 지우지 않음."""
    return value


def _field_whitelist(value: Any, p: MaskParams) -> Any:
    if isinstance(value, Mapping):
        return {"recorded_keys": sorted(str(k) for k in value)}
    return {"recorded_keys": []}


def _summary_only(value: Any, p: MaskParams) -> Any:
    if isinstance(value, Mapping):
        keys = sorted(str(k) for k in value)
    elif isinstance(value, list):
        keys = [f"[{i}]" for i in range(len(value))]
    else:
        keys = []
    return {"key_list": keys, "char_len": len(str(value))}


def _substitute(value: Any, p: MaskParams) -> Any:
    return p.substitute_text


def _len_hash_count(value: Any, p: MaskParams) -> Any:
    return {
        "len": len(str(value)),
        "hash": irreversible_hash(value)[: p.hash_prefix_len],
        "count": _count_only(value, p)["count"],
    }


def _field_and_hash_diff(value: Any, p: MaskParams) -> Any:
    if isinstance(value, Mapping):
        return {
            "changed_fields": sorted(str(k) for k in value),
            "hashes": {
                str(k): irreversible_hash(v)[: p.hash_prefix_len] for k, v in value.items()
            },
        }
    return {
        "changed_fields": [],
        "hashes": {"value": irreversible_hash(value)[: p.hash_prefix_len]},
    }


def _hash_and_purpose(value: Any, p: MaskParams) -> Any:
    return {"ref": irreversible_hash(value)[: p.hash_prefix_len]}


MASK_METHODS: dict[str, Any] = {
    "all_stars": _all_stars,
    "token_id_only": _token_id_only,
    "email_local2_or_hash12": _email_local2_or_hash12,
    "region_label_only": _region_label_only,
    "count_only": _count_only,
    "bool_only": _bool_only,
    "drop_field": _drop_field,
    "last4": _last4,
    "count_and_category": _count_and_category,
    "dim_and_time": _dim_and_time,
    "separate_store": _separate_store,
    "first_char_stars": _first_char_stars,
    "allow_value": _allow_value,
    "not_recorded": _not_recorded,
    "hash_only": _hash_only,
    "sentence_or_discard": _sentence_or_discard,
    "field_whitelist": _field_whitelist,
    "summary_only": _summary_only,
    "substitute": _substitute,
    "len_hash_count": _len_hash_count,
    "field_and_hash_diff": _field_and_hash_diff,
    "hash_and_purpose": _hash_and_purpose,
}

_VALUE_RECORDED_METHODS = frozenset({"allow_value", "sentence_or_discard"})
"""⑥이 값 기록을 허용한 방법. 기록 전수 검색 시험에서 예외로 세는 대상임."""


@dataclass(frozen=True, slots=True)
class MaskHit:
    """가리기가 실제로 걸린 1건. 시험이 `4경로 전부 적용`을 세는 데 씀."""

    mask_id: str
    field_id: str
    field: str
    path: MaskPath
    method: str


class Masker:
    """가리기 매핑 1벌. 5경로가 같은 이 객체를 지남."""

    def __init__(self, book: RuleBook | None = None) -> None:
        self._book = book or get_rulebook()
        self._params = MaskParams.from_rulebook(self._book)
        self._by_field: dict[str, list[dict[str, Any]]] = {}
        for row in self._book.mask_rules:
            method = row["method"]
            if method not in MASK_METHODS:
                raise RuleBookInvalid(f"마스킹 {row['id']}의 방법 `{method}`을 구현이 모르는 이름임")
            for override in (row.get("path_overrides") or {}).values():
                if override not in MASK_METHODS:
                    raise RuleBookInvalid(
                        f"마스킹 {row['id']}의 경로별 방법 `{override}`을 구현이 모르는 이름임"
                    )
            for field_name in row["fields"]:
                self._by_field.setdefault(field_name, []).append(row)
        self._hits: list[MaskHit] = []

    # --- 조회 -------------------------------------------------------------
    @property
    def rulebook(self) -> RuleBook:
        return self._book

    @property
    def params(self) -> MaskParams:
        return self._params

    def rules_for_field(self, field: str) -> tuple[dict[str, Any], ...]:
        return tuple(self._by_field.get(field, ()))

    def covered_fields(self) -> frozenset[str]:
        return frozenset(self._by_field)

    def hits(self) -> tuple[MaskHit, ...]:
        return tuple(self._hits)

    def reset_hits(self) -> None:
        self._hits.clear()

    def paths_covered(self) -> frozenset[MaskPath]:
        return frozenset(hit.path for hit in self._hits)

    def value_recorded_exceptions(self) -> tuple[tuple[str, str, str], ...]:
        """⑥이 값 기록을 명시 허용한 (마스킹 ID · 필드 ID · 경로) 목록."""
        out: list[tuple[str, str, str]] = []
        for row in self._book.mask_rules:
            for path in MaskPath:
                method = self._method_for(row, path)
                if method in _VALUE_RECORDED_METHODS:
                    out.append((str(row["id"]), str(row["field_id"]), path.value))
        return tuple(out)

    # --- 가리기 -----------------------------------------------------------
    def mask_value(self, field: str, value: Any, path: MaskPath) -> tuple[bool, Any]:
        """(가렸나, 가린 값). 규칙이 없으면 `(False, 원래 값)`."""
        rows = self._by_field.get(field)
        if not rows:
            return False, value
        masked = value
        applied = False
        for row in rows:
            method = self._method_for(row, path)
            if method is None:
                continue
            masked = MASK_METHODS[method](masked, self._params)
            applied = True
            self._hits.append(
                MaskHit(
                    mask_id=str(row["id"]),
                    field_id=str(row["field_id"]),
                    field=field,
                    path=path,
                    method=method,
                )
            )
            if masked is None:
                break
        return applied, masked

    def mask_mapping(self, payload: Mapping[str, Any], path: MaskPath) -> dict[str, Any]:
        """중첩된 칸까지 훑어 가림. `None`으로 바뀐 칸은 아예 지움."""
        out: dict[str, Any] = {}
        for key, value in payload.items():
            applied, masked = self.mask_value(key, value, path)
            if applied:
                if masked is not None:
                    out[key] = masked
                continue
            if isinstance(value, Mapping):
                out[key] = self.mask_mapping(value, path)
            elif isinstance(value, list):
                out[key] = [
                    self.mask_mapping(item, path) if isinstance(item, Mapping) else item
                    for item in value
                ]
            else:
                out[key] = value
        return out

    # --- 기록 전수 검색용 -------------------------------------------------
    def sensitive_value_probes(self) -> tuple[tuple[str, str], ...]:
        """(필드 이름, 원문 표본) — 시험이 기록에서 이 표본이 남았는지 훑는 데 씀."""
        probes: list[tuple[str, str]] = []
        for field in sorted(self._by_field):
            probes.append((field, f"원문표본-{field}-DO-NOT-LOG"))
        return tuple(probes)

    def _method_for(self, row: Mapping[str, Any], path: MaskPath) -> str | None:
        overrides = row.get("path_overrides") or {}
        if path.value in overrides:
            return str(overrides[path.value])
        if path.value in row.get("paths", []):
            return str(row["method"])
        return None


_CACHED: Masker | None = None


def get_masker(book: RuleBook | None = None) -> Masker:
    """설정을 다시 읽지 않고 쓰는 매핑 1벌. 시험은 새 인스턴스를 만들어 씀."""
    global _CACHED
    if book is not None:
        return Masker(book)
    if _CACHED is None:
        _CACHED = Masker()
    return _CACHED
