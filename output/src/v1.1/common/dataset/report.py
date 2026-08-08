"""원천 품질 리포트를 만듦.

돌리는 법 — `python -m common.dataset.report`
실접속 정보가 없으면 그 경로는 **0행이라고 그대로 적고** 왜 못 읽었는지 함께 적음.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from common.config import Settings, get_settings

from .glossary import GlossaryKind, load_glossary
from .live_reader import LiveSourceReader, missing_inputs_for
from .paths import PATH_IDS, StorageKind, spec_of
from .quality import NOT_MEASURED, PathQuality, check_threshold, measure
from .seed import SeedSourceReader, seed_blocked_reason
from .snapshot import snapshot_dir, write_snapshot
from .source_port import Origin, ReadResult, SourceUnavailable, read_path

__all__ = ["DEFAULT_REPORT_DIR", "build_report", "collect", "main"]

DEFAULT_REPORT_DIR = Path(__file__).resolve().parent / "reports"
_REPORT_NAME = "source-quality-report.md"

# 거르는 조건에 넣을 값. 리포트를 돌리기 위한 것이며 설계서 값이 아님.
_SAMPLE_PARAMS: dict[str, str] = {
    "member_id": "M000000",
    "consent_kind": "위치",
    "recommendation_id": "RC00000000",
    "since_on": "2026-01-01",
    "until_on": "2026-01-31",
    "target_on": "2026-01-01",
    "run_on": "2026-01-01",
    "allowed_since_on": "2026-01-01",
    "free_tier_boundary_on": "2026-01-01",
    "billing_cycle_started_on": "2026-01-01",
}


def _params_for(path_id: str) -> dict[str, object]:
    spec = spec_of(path_id)
    return {
        name: _SAMPLE_PARAMS.get(name)
        for name in spec.filter_params
    }


def _fmt_ratio(value: float | None) -> str:
    return NOT_MEASURED if value is None else f"{value:.4f}"


def _fmt_count(value: int | None) -> str:
    return NOT_MEASURED if value is None else f"{value:,}건"


def collect(
    settings: Settings | None = None, prefer_live: bool = True
) -> tuple[list[tuple[ReadResult, PathQuality]], list[str]]:
    """경로 전건을 읽고 세어 옴. 못 읽은 경로도 0행으로 남김."""
    conf = settings if settings is not None else get_settings()
    live = LiveSourceReader(conf)
    seed = SeedSourceReader(conf)
    collected: list[tuple[ReadResult, PathQuality]] = []
    unread: list[str] = []

    for path_id in PATH_IDS:
        spec = spec_of(path_id)
        notes: list[str] = []
        result: ReadResult | None = None

        if prefer_live and not missing_inputs_for(spec, conf):
            try:
                result = read_path(path_id, live, _params_for(path_id), None, conf)
            except SourceUnavailable as exc:
                notes.append(f"실접속 실패 — {exc}")

        if result is None:
            missing = missing_inputs_for(spec, conf)
            if missing:
                notes.append("실접속 못 함 — " + " · ".join(missing))
            blocked = seed_blocked_reason(path_id)
            if blocked:
                unread.append(f"{path_id}: {blocked}")
            result = read_path(path_id, seed, _params_for(path_id), None, conf)
            notes.extend(seed.notes_by_path.get(path_id, ()))

        collected.append((result, measure(result, notes)))
    return collected, unread


def build_report(
    collected: Sequence[tuple[ReadResult, PathQuality]],
    settings: Settings | None = None,
    generated_at: datetime | None = None,
) -> str:
    conf = settings if settings is not None else get_settings()
    stamp = generated_at if generated_at is not None else datetime.now(UTC)
    live_count = sum(1 for result, _ in collected if result.origin is Origin.LIVE)
    seed_count = len(collected) - live_count

    lines: list[str] = [
        "# 원천 품질 리포트 — 런치픽 v1.1 데이터 준비",
        "",
        f"만든 시각(기준 시점): {stamp.isoformat()}",
        f"경로 {len(collected)}개 — 실접속 {live_count}개 · 합성 시드 {seed_count}개",
        f"난수 씨앗: {conf.dataset_seed}",
        "",
        "> **이 리포트를 읽는 법** — `출처` 칸이 `합성시드`인 행의 숫자는 **원천 실측이 아님.**",
        "> 연습용 데이터를 센 값이므로 원천 품질의 근거로 쓸 수 없음.",
        "> 원천 실측 칸은 설계서 ⑤ 8절과 마찬가지로 아직 `미측정`임.",
        "",
        "## 1. 경로별 품질",
        "",
        "| 경로 | 논리 표 | 출처 | 행 수 | 상한 | 빈 값(최악 열) | 중복 | 형식 어긋남"
        " | 실측 오류율 | ⑤에 적힌 값 | 차이 |",
        "|------|--------|------|------:|-----:|--------------:|-----:|-----------:"
        "|-----------:|------------|------|",
    ]

    for result, quality in collected:
        spec = spec_of(result.path_id)
        diff = (
            "⑤가 아직 미측정이라 견줄 수 없음"
            if quality.design_error_rate.startswith("[확인필요")
            else "견줌 필요"
        )
        lines.append(
            f"| {result.path_id} | `{spec.logical_table}` | {result.origin.value}"
            f" | {quality.row_count:,} | {result.row_cap:,}"
            f" | {_fmt_ratio(quality.worst_empty_ratio)}"
            f" | {_fmt_ratio(quality.duplicate_ratio)}"
            f" | {_fmt_count(quality.format_mismatch_count)}"
            f" | {_fmt_ratio(quality.measured_error_rate)}"
            f" | {quality.design_error_rate} | {diff} |"
        )

    lines += [
        "",
        "## 2. 측정 방법과 측정일",
        "",
        "| 경로 | 측정일 | 측정 방법 | 갱신 지연 |",
        "|------|-------|----------|----------|",
    ]
    for _, quality in collected:
        lines.append(
            f"| {quality.path_id} | {quality.measured_on} | {quality.method}"
            f" | {quality.refresh_lag} |"
        )

    lines += [
        "",
        "## 3. 원천 실측 대비표 — ⑤ 8절과 나란히 둠",
        "",
        "| ⑤ 8절 행 | ⑤에 적힌 값 | 이번 실측 | 어느 쪽이 나쁜가 |",
        "|----------|------------|----------|----------------|",
    ]
    seen: set[str] = set()
    for _, quality in collected:
        row = spec_of(quality.path_id).error_rate_row
        if row in seen:
            continue
        seen.add(row)
        lines.append(
            f"| {row} | {quality.design_error_rate} | {NOT_MEASURED} — 원천에 붙지 못했음"
            " | 견줄 수 없음. ⑤에 되돌려 물음 |"
        )
    lines += [
        "",
        "**⑤에 되돌려 물을 것 1행** — ⑤ 8절 「원천 오류율」의 6경로가 여전히"
        " `[확인필요: 원천 오류율 실측값]`임. 물리 저장소가 서기 전에는 이 값을 채울 수 없으므로,"
        " 저장소가 서는 시점을 실측 일정으로 ⑤에 적어야 함.",
        "",
        "## 4. 품질 문턱 검사",
        "",
        "| 항목 | 문턱 | 실측 | 판정 |",
        "|------|-----|-----|------|",
    ]
    for _, quality in collected:
        verdict = check_threshold(
            f"{quality.path_id}.error_rate", quality.measured_error_rate, conf
        )
        threshold = NOT_MEASURED if verdict.threshold is None else f"{verdict.threshold:.4f}"
        lines.append(
            f"| {verdict.item} | {threshold} | {_fmt_ratio(verdict.measured)}"
            f" | {verdict.verdict} |"
        )

    lines += ["", "## 5. 남길 말", ""]
    any_note = False
    for _, quality in collected:
        for note in quality.notes:
            lines.append(f"- `{quality.path_id}` {note}")
            any_note = True
    if not any_note:
        lines.append("- 없음")

    lines += [
        "",
        "## 6. 용어사전 상태",
        "",
        "| 사전 | 파일 | 쓸 수 있는 대표어 | 아직 비어 있는 행 |",
        "|------|------|----------------:|----------------:|",
    ]
    for kind in GlossaryKind:
        glossary = load_glossary(kind, conf)
        lines.append(
            f"| {kind.value} | `{glossary.source_file.name}`"
            f" | {len(glossary.usable_terms)}건 | {glossary.open_row_count}건 |"
        )

    lines += [
        "",
        "## 7. 아직 붙지 못한 저장소",
        "",
        "| 저장소 | 종류 | 접속 정보 설정 키 | 무엇이 없나 |",
        "|-------|------|-----------------|-----------|",
    ]
    shown: set[str] = set()
    for _, quality in collected:
        spec = spec_of(quality.path_id)
        if spec.storage_id in shown:
            continue
        shown.add(spec.storage_id)
        missing = missing_inputs_for(spec, conf)
        key = {
            StorageKind.RELATIONAL: "LUNCHPICK_DATASET_SOURCE_DB_URL",
            StorageKind.VECTOR: "LUNCHPICK_DATASET_VECTOR_INDEX_URL",
            StorageKind.CACHE: "LUNCHPICK_DATASET_CACHE_URL",
        }[spec.storage_kind]
        lines.append(
            f"| {spec.storage_id} | {spec.storage_kind.value} | `{key}`"
            f" | {' · '.join(missing) if missing else '없음 — 읽을 수 있음'} |"
        )

    lines.append("")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="원천 품질 리포트를 만듦")
    parser.add_argument(
        "--no-snapshot", action="store_true", help="스냅샷 파일을 남기지 않음"
    )
    parser.add_argument(
        "--report-dir", default=None, help="리포트를 둘 폴더. 안 주면 패키지 안 기본 폴더"
    )
    args = parser.parse_args(argv)

    # 콘솔 기본 인코딩이 한글 윈도우 코드페이지면 일부 글자를 못 찍으므로 UTF-8로 맞춤.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    conf = get_settings()
    collected, unread = collect(conf)

    if not args.no_snapshot:
        for result, _ in collected:
            write_snapshot(result, conf)

    report_dir = Path(args.report_dir) if args.report_dir else DEFAULT_REPORT_DIR
    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / _REPORT_NAME
    report_file.write_text(build_report(collected, conf), encoding="utf-8")

    total_rows = sum(quality.row_count for _, quality in collected)
    print(f"리포트: {report_file}")
    print(f"스냅샷 폴더: {snapshot_dir(conf)}")
    print(f"경로 {len(collected)}개 · 읽어 온 행 합계 {total_rows:,}행")
    for result, quality in collected:
        print(f"  {result.path_id}\t{result.origin.value}\t{quality.row_count:,}행")
    for line in unread:
        print(f"  만들지 못한 경로 — {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
