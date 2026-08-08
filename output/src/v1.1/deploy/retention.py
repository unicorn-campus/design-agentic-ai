"""보존 기간 만료 대상을 계산하는 기본 예행 작업.

실제 저장소 스키마와 운영 승인 방식이 확정되지 않아 이 모듈은 삭제 SQL을 실행하지 않음.
기본 동작은 대상 건수만 보여 주는 예행이며 원문 식별자를 출력하지 않음.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class RetentionCandidate:
    store_id: str
    category: str
    expires_at: datetime | None
    protected: bool = False


@dataclass(frozen=True, slots=True)
class RetentionSummary:
    scanned: int
    expired_by_store: dict[str, int]
    protected: int
    no_policy: int
    deleted: int = 0

    def as_dict(self) -> dict[str, object]:
        return {
            "scanned": self.scanned,
            "expired_by_store": self.expired_by_store,
            "protected": self.protected,
            "no_policy": self.no_policy,
            "deleted": self.deleted,
            "mode": "dry-run",
        }


def plan_retention(
    candidates: Iterable[RetentionCandidate], *, now: datetime | None = None
) -> RetentionSummary:
    """만료 대상 건수만 계산함. 보호 대상과 정책 미확정 항목은 기본 거부함."""
    current = now or datetime.now(UTC)
    rows = list(candidates)
    expired: dict[str, int] = {}
    protected = 0
    no_policy = 0
    for row in rows:
        if row.protected:
            protected += 1
            continue
        if row.expires_at is None:
            no_policy += 1
            continue
        expires_at = row.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        if expires_at <= current:
            expired[row.store_id] = expired.get(row.store_id, 0) + 1
    return RetentionSummary(
        scanned=len(rows),
        expired_by_store=expired,
        protected=protected,
        no_policy=no_policy,
    )


def _load_candidates(path: Path) -> list[RetentionCandidate]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows: list[RetentionCandidate] = []
    for item in payload:
        raw_expiry = item.get("expires_at")
        rows.append(
            RetentionCandidate(
                store_id=str(item["store_id"]),
                category=str(item["category"]),
                expires_at=None if raw_expiry is None else datetime.fromisoformat(raw_expiry),
                protected=bool(item.get("protected", False)),
            )
        )
    return rows


def _example_candidates(now: datetime) -> list[RetentionCandidate]:
    """민감한 원문이 없는 로컬 예행 표본."""
    return [
        RetentionCandidate("S-2", "location", now - timedelta(days=1)),
        RetentionCandidate("S-3", "premium_history", None),
        RetentionCandidate("S-6", "audit", now - timedelta(days=1), protected=True),
        RetentionCandidate("S-7", "payment_failure", now + timedelta(days=1)),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="보존 기간 만료 대상 예행")
    parser.add_argument("--input", type=Path, help="후보 JSON 파일. 생략 시 비식별 표본 사용")
    parser.add_argument("--apply", action="store_true", help="실제 삭제 요청")
    args = parser.parse_args(argv)
    if args.apply:
        parser.error(
            "실제 삭제는 차단됨: 저장소 스키마·승인 토큰·직전 1세대 보관 절차 확정 필요"
        )
    now = datetime.now(UTC)
    candidates = _load_candidates(args.input) if args.input else _example_candidates(now)
    print(json.dumps(plan_retention(candidates, now=now).as_dict(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
