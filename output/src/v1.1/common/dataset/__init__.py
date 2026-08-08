"""데이터 준비 묶음 — 지식 경로가 읽을 데이터를 손에 넣는 자리.

여기서 하지 않는 일 — 색인 만들기 · 검색기 · 재정렬(검색 프롬프트 몫) ·
바깥 시스템 연결과 권한(도구 연동 프롬프트 몫) · 가리기와 기록(가드레일 프롬프트 몫) ·
답변 품질 재기(평가 프롬프트 몫).
"""

from .forbidden import (
    BOUNDARY_SCOPED_FIELDS,
    FORBIDDEN_FIELDS,
    FORBIDDEN_TABLES,
    ForbiddenFieldFound,
    assert_no_forbidden_field,
    forbidden_fields_in,
)
from .glossary import (
    AllergenMapping,
    CanonicalResult,
    Glossary,
    GlossaryKind,
    GlossaryTerm,
    UnmappedTerm,
    allergen_codes_for,
    load_glossary,
    to_canonical,
    unmapped_report,
)
from .live_reader import LiveSourceReader, connection_setting_name, missing_inputs_for
from .paths import PATH_IDS, PATHS, PathSpec, StorageKind, UnknownPath, spec_of
from .quality import NOT_MEASURED, PathQuality, ThresholdVerdict, check_threshold, measure
from .readers import READ_FUNCTIONS
from .seed import SEED_MARK, SeedSourceReader, seed_blocked_reason, seed_rows_for
from .snapshot import SnapshotHandle, read_snapshot, retention_days_for, write_snapshot
from .source_port import (
    Origin,
    ReadResult,
    SourceReader,
    SourceUnavailable,
    read_path,
)
from .write_guard import NotReadOnly, ensure_read_only_query

__all__ = [
    "BOUNDARY_SCOPED_FIELDS",
    "FORBIDDEN_FIELDS",
    "FORBIDDEN_TABLES",
    "NOT_MEASURED",
    "PATHS",
    "PATH_IDS",
    "READ_FUNCTIONS",
    "SEED_MARK",
    "AllergenMapping",
    "CanonicalResult",
    "ForbiddenFieldFound",
    "Glossary",
    "GlossaryKind",
    "GlossaryTerm",
    "LiveSourceReader",
    "NotReadOnly",
    "Origin",
    "PathQuality",
    "PathSpec",
    "ReadResult",
    "SeedSourceReader",
    "SnapshotHandle",
    "SourceReader",
    "SourceUnavailable",
    "StorageKind",
    "ThresholdVerdict",
    "UnknownPath",
    "UnmappedTerm",
    "allergen_codes_for",
    "assert_no_forbidden_field",
    "check_threshold",
    "connection_setting_name",
    "ensure_read_only_query",
    "forbidden_fields_in",
    "load_glossary",
    "measure",
    "missing_inputs_for",
    "read_path",
    "read_snapshot",
    "retention_days_for",
    "seed_blocked_reason",
    "seed_rows_for",
    "spec_of",
    "to_canonical",
    "unmapped_report",
    "write_snapshot",
]
