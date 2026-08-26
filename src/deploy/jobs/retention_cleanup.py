from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class RetentionPolicy:
    target: str
    retention: str
    schedule: str
    source: str


POLICIES = (
    RetentionPolicy("masked_transaction_analysis_v", "0일", "요청 종료 즉시", "⑤ 보존·삭제"),
    RetentionPolicy("masked_consultation_analysis_v", "0일", "배치 종료 즉시", "⑤ 보존·삭제"),
    RetentionPolicy("consultation_event_inbox", "7일", "일 1회", "⑤ 보존·삭제"),
    RetentionPolicy("faq_improvement_queue", "30일", "일 1회", "⑤ 보존·삭제"),
    RetentionPolicy("S-1", "원천 승인 만료 후 최대 1일", "일 1회", "⑤ 보존·삭제"),
    RetentionPolicy("S-2", "원천 삭제 후 최대 1일", "일 1회", "⑤ 보존·삭제"),
    RetentionPolicy("glossary_term", "현재 승인 세대와 직전 1세대, 최대 7일", "주 1회", "⑤ 보존·삭제"),
    RetentionPolicy("external_search_cache", "웹 60분, 영상 1440분", "10분마다", "⑤ 보존·삭제"),
    RetentionPolicy("checkpoint", "W-1 600000ms, W-2 3600000ms, W-3 60000ms", "기간 경과 즉시", "⑤ 보존·삭제"),
)

CHECKPOINT_RETENTION = {
    "W-1": timedelta(milliseconds=600000),
    "W-2": timedelta(milliseconds=3600000),
    "W-3": timedelta(milliseconds=60000),
}
PROTECTED_STATUSES = frozenset({"approval_wait", "resume_pending", "in_progress"})


def expired_checkpoint_ids(
    rows: Iterable[dict[str, Any]],
    now: datetime,
    subject_ref: str | None = None,
) -> list[str]:
    expired: list[str] = []
    for row in rows:
        if subject_ref is not None and row.get("subject_ref") != subject_ref:
            continue
        if row.get("status") in PROTECTED_STATUSES:
            continue
        workflow_id = str(row["workflow_id"])
        minimum_age = CHECKPOINT_RETENTION[workflow_id]
        updated_at = datetime.fromisoformat(str(row["updated_at"]))
        if updated_at.tzinfo is None:
            updated_at = updated_at.replace(tzinfo=timezone.utc)
        if now - updated_at >= minimum_age:
            expired.append(str(row["thread_id"]))
    return expired


def run_checkpoint_cleanup(
    rows: Iterable[dict[str, Any]],
    now: datetime,
    delete: Callable[[str], None],
    execute: bool = False,
    subject_ref: str | None = None,
) -> dict[str, Any]:
    targets = expired_checkpoint_ids(rows, now, subject_ref)
    deleted = 0
    if execute:
        if os.environ.get("HELP_DESK_RETENTION_DELETE_ENABLED") != "true":
            raise PermissionError("실제 삭제 설정과 사람 승인이 필요함")
        if not os.environ.get("HELP_DESK_RETENTION_APPROVAL_REF"):
            raise PermissionError("삭제 승인 참조값이 필요함")
        for thread_id in targets:
            delete(thread_id)
            deleted += 1
    return {"mode": "execute" if execute else "dry-run", "targets": targets, "deleted": deleted}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint-records", type=Path)
    parser.add_argument("--subject-ref")
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    if args.execute:
        raise SystemExit("실제 저장소 삭제는 01 저장 계층 어댑터 연결 뒤에만 허용함")
    rows = []
    if args.checkpoint_records:
        rows = json.loads(args.checkpoint_records.read_text(encoding="utf-8"))
    result = run_checkpoint_cleanup(
        rows,
        datetime.now(timezone.utc),
        lambda _: None,
        subject_ref=args.subject_ref,
    )
    print(json.dumps({
        "policies": [asdict(policy) for policy in POLICIES],
        "checkpoint": result,
        "actual_deletions": 0,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
