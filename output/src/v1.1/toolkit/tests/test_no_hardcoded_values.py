"""코드에 박힌 주소 · 자격 · 시간 상한 숫자가 **0건**임을 문자열 검색으로 확인함.

`common`(01-runtime)과 시험 파일은 대상이 아님 — 시험 고정값은 시험 안에만 있음.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import services
import toolkit

TOOLKIT_ROOT = Path(toolkit.__file__).resolve().parent
SERVICES_ROOT = Path(services.__file__).resolve().parent

# 주소로 읽힐 문자열 — 어느 소스에도 없어야 함
ADDRESS_PATTERN = re.compile(r"https?://[a-zA-Z0-9.\-]+")
# 자격 이름이 아니라 **값**으로 읽힐 문자열
CREDENTIAL_PATTERN = re.compile(
    r"(api[_-]?key|secret|token|password)\s*[:=]\s*[\"'][A-Za-z0-9\-_]{8,}[\"']",
    re.IGNORECASE,
)
# 밀리초 단위 시간 상한으로 읽힐 숫자 리터럴(3자리 이상 · 밑줄 표기 포함)
TIMEOUT_PATTERN = re.compile(r"\b(timeout|retry|backoff)\w*\s*[:=]\s*\d{2,}", re.IGNORECASE)


def _source_files() -> list[Path]:
    files: list[Path] = []
    # 이 검사는 04-connector 범위만 소유함. API의 CORS 허용 주소처럼 다른 프롬프트가
    # 소유하는 값까지 훑으면 커넥터와 무관한 코드가 추가될 때 거짓 실패가 발생함.
    candidates = list(TOOLKIT_ROOT.rglob("*.py"))
    candidates.extend(SERVICES_ROOT.rglob("tools/*.py"))
    candidates.append(SERVICES_ROOT / "registry.py")
    for path in candidates:
        parts = set(path.parts)
        if ".venv" in parts or "tests" in parts or "__pycache__" in parts:
            continue
        files.append(path)
    return files


def test_source_files_were_found() -> None:
    names = {path.name for path in _source_files()}
    assert "runner.py" in names
    assert "c9_billing_register.py" in names
    assert len(_source_files()) >= 15


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: p.name)
def test_no_hardcoded_address(path: Path) -> None:
    hits = ADDRESS_PATTERN.findall(path.read_text(encoding="utf-8"))
    assert hits == [], f"{path.name}에 박힌 주소: {hits}"


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: p.name)
def test_no_hardcoded_credential_value(path: Path) -> None:
    hits = CREDENTIAL_PATTERN.findall(path.read_text(encoding="utf-8"))
    assert hits == [], f"{path.name}에 박힌 자격 값: {hits}"


@pytest.mark.parametrize("path", _source_files(), ids=lambda p: p.name)
def test_no_hardcoded_timeout_or_retry_number(path: Path) -> None:
    hits = TIMEOUT_PATTERN.findall(path.read_text(encoding="utf-8"))
    assert hits == [], f"{path.name}에 박힌 시간 상한·재시도 숫자: {hits}"


def test_timeout_and_retry_come_from_runtime_settings() -> None:
    """값은 ③에서만 옴 — 도구 계층은 `common.config.Settings`에게 물어봄."""
    source = (Path(toolkit.__file__).resolve().parent / "runner.py").read_text(
        encoding="utf-8"
    )
    assert "self.settings.backoff_ms(" in source
    assert "call_with_limits(" in source
    assert "step_timeout_ms" not in source


def test_mode_and_endpoint_are_never_defaulted_in_code() -> None:
    """대역·실물 판정과 주소에 코드 기본값이 없음 — 없으면 멈춤."""
    settings_source = (Path(toolkit.__file__).resolve().parent / "settings.py").read_text(
        encoding="utf-8"
    )
    mode_block = settings_source.split("connector_mode:")[1].split("connector_endpoint:")[0]
    assert "default" not in mode_block, "대역·실물 판정에 코드 기본값이 있음"
