from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


SRC = Path(__file__).resolve().parents[2]
PROJECT = SRC.parent
DEPLOY = SRC / "deploy"
DESIGN = PROJECT / "output" / "design"


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


entrypoint = load_module("deploy_entrypoint", DEPLOY / "scripts" / "container_entrypoint.py")
retention = load_module("retention_cleanup", DEPLOY / "jobs" / "retention_cleanup.py")


def env_keys(path: Path) -> set[str]:
    keys: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            assert value == ""
            keys.add(key)
    return keys


def inventory() -> dict[str, object]:
    return json.loads((DEPLOY / "secret_inventory.json").read_text(encoding="utf-8"))


def test_image_count_matches_physical_deployment_units() -> None:
    design = (DESIGN / "07-배포설계.md").read_text(encoding="utf-8")
    deployment_units = re.findall(r'^  subgraph P\d+\[', design, re.MULTILINE)
    dockerfiles = sorted((SRC / "services").glob("*/Dockerfile"))
    assert len(deployment_units) == 3
    assert len(dockerfiles) == len(deployment_units)


def test_all_logical_components_are_documented() -> None:
    readme = (DEPLOY / "README.md").read_text(encoding="utf-8")
    components = {
        "Help Desk API", "동기 런타임", "LLM Adapter", "규칙 처리기", "상담 위험 예측 API",
        "02:00 Scheduler", "배치 런타임", "우선순위 예측 API",
        "Event Consumer", "이벤트 런타임", "사후 위험 예측 API",
    }
    assert all(component in readme for component in components)
    assert "미대응 0건" in readme


def test_dockerfiles_pin_digest_and_drop_root() -> None:
    for dockerfile in (SRC / "services").glob("*/Dockerfile"):
        text = dockerfile.read_text(encoding="utf-8")
        assert re.search(r"^FROM python:3\.12-slim@sha256:[0-9a-f]{64}$", text, re.MULTILINE)
        assert "USER 10001:10001" in text
        assert "ARG HELP_DESK" not in text


def test_docker_build_context_excludes_local_secret_files() -> None:
    text = (SRC / ".dockerignore").read_text(encoding="utf-8")
    assert "**/.env" in text
    assert "**/.env.local" in text
    assert "**/*.local.env" in text


def test_secret_examples_equal_inventory_and_have_empty_values() -> None:
    document = inventory()
    items = document["items"]
    paths = {
        "p1": DEPLOY / "secrets" / "p1" / ".env.example",
        "p2": DEPLOY / "secrets" / "p2" / ".env.example",
        "p3": DEPLOY / "secrets" / "p3" / ".env.example",
        "operations": DEPLOY / "secrets" / ".env.example",
    }
    actual_union: set[str] = set()
    for service, path in paths.items():
        actual = env_keys(path)
        expected = {item["key"] for item in items if service in item["services"]}
        assert actual == expected
        actual_union |= actual
    assert actual_union == {item["key"] for item in items}
    assert len(actual_union) == 14


def test_secret_sources_cover_four_required_areas() -> None:
    document = inventory()
    categories = {item["category"] for item in document["items"]}
    assert {"connector", "store", "model"} <= categories
    assert "observability_alerting" in document["coverage"]


def test_image_contains_no_secret_assignment() -> None:
    secret_names = {item["key"] for item in inventory()["items"]}
    image_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (SRC / "services").glob("*/Dockerfile")
    )
    assert not any(name in image_text for name in secret_names)


def test_manifest_contains_no_secret_assignment() -> None:
    secret_names = {item["key"] for item in inventory()["items"]}
    manifest = (SRC / "docker-compose.yml").read_text(encoding="utf-8")
    for name in secret_names:
        assert not re.search(rf"{re.escape(name)}\s*:\s*\S+", manifest)


def test_required_secret_missing_fails_at_startup(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in entrypoint.required_secret_names("p1"):
        monkeypatch.delenv(name, raising=False)
    missing = entrypoint.missing_required_secrets("p1")
    assert set(missing) == set(entrypoint.required_secret_names("p1"))


def test_startup_log_never_contains_secret_value(tmp_path: Path) -> None:
    marker = "runtime-secret-marker"
    env = os.environ.copy()
    for name in entrypoint.required_secret_names("p1"):
        env[name] = marker
    env["HELP_DESK_HTTP_PORT"] = "8080"
    result = subprocess.run(
        [sys.executable, str(DEPLOY / "scripts" / "container_entrypoint.py"), "p1", "--check-only"],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    assert marker not in result.stdout
    assert marker not in result.stderr
    assert "startup-check=ok" in result.stdout


def test_retention_dry_run_shows_targets_without_deleting(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    rows = [
        {
            "thread_id": "expired-thread",
            "workflow_id": "W-1",
            "status": "completed",
            "subject_ref": "subject-a",
            "updated_at": (now - timedelta(minutes=11)).isoformat(),
        },
        {
            "thread_id": "approval-thread",
            "workflow_id": "W-1",
            "status": "approval_wait",
            "subject_ref": "subject-a",
            "updated_at": (now - timedelta(minutes=11)).isoformat(),
        },
    ]
    deleted: list[str] = []
    result = retention.run_checkpoint_cleanup(rows, now, deleted.append)
    assert result == {"mode": "dry-run", "targets": ["expired-thread"], "deleted": 0}
    assert deleted == []


def test_real_deletion_requires_flag_and_human_approval(monkeypatch: pytest.MonkeyPatch) -> None:
    now = datetime.now(timezone.utc)
    rows = [{
        "thread_id": "expired-thread",
        "workflow_id": "W-3",
        "status": "completed",
        "updated_at": (now - timedelta(minutes=2)).isoformat(),
    }]
    monkeypatch.delenv("HELP_DESK_RETENTION_DELETE_ENABLED", raising=False)
    monkeypatch.delenv("HELP_DESK_RETENTION_APPROVAL_REF", raising=False)
    with pytest.raises(PermissionError):
        retention.run_checkpoint_cleanup(rows, now, lambda _: None, execute=True)


def test_compose_manifest_is_valid() -> None:
    subprocess.run(
        ["docker", "compose", "-f", str(SRC / "docker-compose.yml"), "config", "--quiet"],
        check=True,
        cwd=SRC,
    )


def test_rollback_keeps_one_previous_generation_for_irreversible_changes() -> None:
    text = (DEPLOY / "ROLLBACK.md").read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if line.startswith("| ") and "| 예 |" in line]
    assert len(rows) == 4


def test_confirmation_count_matches_readme_rows() -> None:
    text = (DEPLOY / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\| `\[확인필요:", text, re.MULTILINE)
    declared = int(re.search(r"확인필요 (\d+)건임", text).group(1))
    assert len(rows) == declared
