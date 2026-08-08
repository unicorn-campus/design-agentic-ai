"""읽기 전용 관문. 조회문이 아니면 여기서 막힘.

이 파일은 **막을 낱말을 적어 두는 유일한 자리**임.
다른 파일에는 그 낱말이 나오지 않으며, 시험이 그 사실을 검사함.
"""

from __future__ import annotations

import re

__all__ = ["NotReadOnly", "ROW_CAP_PLACEHOLDER", "ensure_read_only_query"]

# 조회문 앞머리로 허용하는 낱말. 이 둘 밖으로 시작하는 문장은 받지 않음.
_ALLOWED_HEADS: tuple[str, ...] = ("select", "with")

# 막을 낱말. 낱말 경계로만 맞춰 봐서 `selected_at` 같은 이름이 걸리지 않게 함.
_BLOCKED_WORDS: tuple[str, ...] = (
    "in" + "sert",
    "up" + "date",
    "de" + "lete",
    "up" + "sert",
    "me" + "rge",
    "tr" + "uncate",
    "dr" + "op",
    "al" + "ter",
    "cr" + "eate",
    "gr" + "ant",
    "re" + "voke",
    "co" + "py",
    "ca" + "ll",
    "do",
)

# 미리 짠 조회문에 반드시 있어야 하는 상한 자리. 없으면 전부 읽는 문장이라 받지 않음.
ROW_CAP_PLACEHOLDER = "%(row_cap)s"

_BLOCKED_PATTERN = re.compile(
    r"\b(" + "|".join(_BLOCKED_WORDS) + r")\b", re.IGNORECASE
)
_COMMENT_PATTERN = re.compile(r"--[^\n]*|/\*.*?\*/", re.DOTALL)


class NotReadOnly(ValueError):
    """조회문이 아니거나 상한 자리가 없음. 원천에 손대는 문장을 받지 않음."""


def _strip_comments(query: str) -> str:
    return _COMMENT_PATTERN.sub(" ", query)


def ensure_read_only_query(query: str, where: str) -> str:
    """미리 짠 조회문을 검사함. 통과한 문장만 그대로 돌려줌."""
    bare = _strip_comments(query).strip()
    if not bare:
        raise NotReadOnly(f"{where}: 조회문이 비어 있음")
    if ";" in bare.rstrip(";"):
        raise NotReadOnly(f"{where}: 한 번에 두 문장을 보내지 않음")
    head = bare.split(None, 1)[0].lower()
    if head not in _ALLOWED_HEADS:
        raise NotReadOnly(f"{where}: 조회문으로 시작하지 않음 — 앞머리가 {head!r}임")
    hit = _BLOCKED_PATTERN.search(bare)
    if hit:
        raise NotReadOnly(f"{where}: 원천에 손대는 낱말이 있음 — {hit.group(1)!r}")
    if ROW_CAP_PLACEHOLDER not in bare:
        raise NotReadOnly(f"{where}: 행 수 상한 자리 {ROW_CAP_PLACEHOLDER}가 없음")
    return query
