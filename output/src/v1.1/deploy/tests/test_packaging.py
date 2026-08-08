from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]


def test_five_packaging_units_have_image_builds() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    images = set(re.findall(r"image: lunchpick/([^:$]+)", compose))
    assert images == {
        "member-service",
        "recommendation-history-service",
        "payment-service",
        "daily-learning-batch",
        "frontend",
    }


def test_secret_example_has_fifteen_design_keys_and_blank_values() -> None:
    lines = (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
    design_lines = [
        line for line in lines
        if line.startswith("LUNCHPICK_")
        and not line.startswith("LUNCHPICK_POSTGRES_PASSWORD")
        and not line.startswith("LUNCHPICK_CONNECTOR_MODE")
        and not line.startswith("LUNCHPICK_IDEMPOTENCY_TTL_HOURS")
        and not line.startswith("LUNCHPICK_OTLP_ENDPOINT=")
    ]
    assert len(design_lines) == 15
    assert all(line.endswith("=") for line in design_lines)


def test_no_secret_is_baked_into_dockerfiles() -> None:
    dockerfiles = [ROOT / "deploy" / "Dockerfile.backend", ROOT / "frontend" / "Dockerfile"]
    source = "\n".join(path.read_text(encoding="utf-8") for path in dockerfiles)
    forbidden = ("API_KEY=", "PASSWORD=", "TOKEN=", "SECRET=", "DATABASE_URL=")
    assert not any(item in source for item in forbidden)
    assert "ARG LUNCHPICK_" not in source


def test_runtime_is_non_root_and_read_only_in_compose() -> None:
    backend = (ROOT / "deploy" / "Dockerfile.backend").read_text(encoding="utf-8")
    frontend = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "USER 10001:10001" in backend
    assert "USER nginx" in frontend
    assert compose.count("read_only: true") >= 2


def test_retention_apply_has_no_delete_implementation() -> None:
    source = (ROOT / "deploy" / "retention.py").read_text(encoding="utf-8").lower()
    assert "delete from" not in source
    assert "실제 삭제는 차단됨" in source
