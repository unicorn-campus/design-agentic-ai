from datetime import UTC, datetime, timedelta

import pytest

from deploy.retention import RetentionCandidate, main, plan_retention


def test_dry_run_only_counts_expired_and_never_deletes() -> None:
    now = datetime(2026, 8, 8, tzinfo=UTC)
    summary = plan_retention(
        [
            RetentionCandidate("S-2", "location", now - timedelta(seconds=1)),
            RetentionCandidate("S-3", "free_history", now + timedelta(seconds=1)),
            RetentionCandidate("S-3", "premium_history", None),
            RetentionCandidate("S-6", "audit", now - timedelta(days=1), protected=True),
        ],
        now=now,
    )
    assert summary.expired_by_store == {"S-2": 1}
    assert summary.protected == 1
    assert summary.no_policy == 1
    assert summary.deleted == 0


def test_apply_is_default_denied() -> None:
    with pytest.raises(SystemExit) as caught:
        main(["--apply"])
    assert caught.value.code == 2
