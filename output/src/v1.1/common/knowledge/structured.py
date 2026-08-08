"""조회 계층 — ⑤ 3절 「정형 접근 경로」 **행 1개당 조회 함수 1개**임.

원천에 붙는 일은 데이터 준비 묶음(`common.dataset`)이 이미 함. 여기서 다시 만들지 않고
그 읽기 함수를 **가져다 씀**. 이 계층이 더하는 것은 3가지뿐임.

1. 차단 목록(⑤ 4절)에 걸리면 **조회를 만들다 말고 실패**함
2. 허용 목록(④ 「접근 가능한 정보 항목」) 밖 열을 조회문에 넣지 않고, 결과도 그 열만 남김
3. 결과마다 **내용 · 출처 · 점수**를 붙이고, 0건이면 **빈 결과 + 사유**를 돌려줌

행 수 상한은 데이터 준비 묶음의 관문이 설정에서 읽어 호출마다 붙임 — 여기에 숫자가 없음.
**읽기 전용만 있음.** 넣기 · 바꾸기 · 지우기 함수를 이 계층에 두지 않음.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from common.config import Settings
from common.dataset import PATH_IDS, ReadResult, SourceReader, read_path, spec_of
from common.dataset.readers import READ_FUNCTIONS

from .column_policy import project, resolve_columns
from .result import (
    Candidate,
    Provenance,
    RetrievalKind,
    RetrievalResult,
    ScoreKind,
)
from .routes import route_of

__all__ = [
    "LOOKUP_FUNCTIONS",
    "lookup",
    "lookup_result_of",
]

_ROUTE_ID = "T-1~T-18"


def _provenance(path_id: str, read: ReadResult, index: int) -> Provenance:
    spec = spec_of(path_id)
    return Provenance(
        route_id=path_id,
        locator=f"{spec.logical_table}#{index}",
        design_row=spec.design_row,
        origin=read.origin.value,
        read_at=read.read_at,
    )


def lookup(
    path_id: str,
    agent_id: str,
    reader: SourceReader,
    params: Mapping[str, Any] | None = None,
    columns: tuple[str, ...] | None = None,
    limit: int | None = None,
    settings: Settings | None = None,
) -> RetrievalResult:
    """경로 1개를 담당자 1명의 자격으로 조회함.

    차단 목록 검사 → 허용 목록으로 열 정하기 → 상한 붙여 읽기 → 사영 → 결과 담기 순서임.
    차단·허용에 걸리면 읽기 함수를 **부르지 않고** 예외로 멈춤.
    """
    route_of(_ROUTE_ID)
    spec = spec_of(path_id)
    chosen = resolve_columns(agent_id, path_id, spec.logical_table, spec.columns, columns)

    read = read_path(path_id, reader, params=params, limit=limit, settings=settings)
    rows = [
        Candidate(
            payload=project(row, chosen),
            source=_provenance(path_id, read, index),
            score=None,
            score_kind=ScoreKind.NONE,
        )
        for index, row in enumerate(read.rows)
    ]

    notes = [f"행 수 상한 {read.row_cap}행이 붙어서 읽었음", f"허용 열 {len(chosen)}개만 담았음"]
    if read.truncated:
        notes.append("상한에 걸려 뒷부분을 잘랐음")
    return RetrievalResult.of(
        route_id=path_id,
        kind=RetrievalKind.STRUCTURED,
        candidates=rows,
        reason_when_empty=(
            f"{path_id} 조회 결과가 0건임 — 지어낸 근거를 채우지 않음"
            f"(거르는 조건 {sorted(dict(params or {}))} · 출처 {read.origin.value})"
        ),
        notes=notes,
    )


def _make_lookup(path_id: str):
    """경로 1개에 붙는 조회 함수를 만듦. 이름과 설명을 ⑤ 3절 행에서 가져옴."""
    spec = spec_of(path_id)

    def _lookup(
        agent_id: str,
        reader: SourceReader,
        params: Mapping[str, Any] | None = None,
        columns: tuple[str, ...] | None = None,
        limit: int | None = None,
        settings: Settings | None = None,
    ) -> RetrievalResult:
        return lookup(
            path_id,
            agent_id,
            reader,
            params=params,
            columns=columns,
            limit=limit,
            settings=settings,
        )

    _lookup.__name__ = f"lookup_{path_id.replace('-', '').lower()}"
    _lookup.__qualname__ = _lookup.__name__
    _lookup.__doc__ = f"{spec.design_row} — {spec.gets} (논리 표 `{spec.logical_table}`)"
    return _lookup


# ⑤ 3절 행 1개 = 조회 함수 1개. 행 수와 함수 수가 같아야 함(시험이 검사함).
LOOKUP_FUNCTIONS: dict[str, Any] = {path_id: _make_lookup(path_id) for path_id in PATH_IDS}

for _name, _fn in LOOKUP_FUNCTIONS.items():
    globals()[_fn.__name__] = _fn
    __all__.append(_fn.__name__)
del _name, _fn


def lookup_result_of(path_id: str) -> Any:
    """경로 이름으로 조회 함수를 찾음. 데이터 준비 묶음의 읽기 함수와 짝임."""
    if path_id not in READ_FUNCTIONS:
        raise KeyError(f"데이터 준비 묶음에 읽기 함수가 없는 경로임: {path_id}")
    return LOOKUP_FUNCTIONS[path_id]
