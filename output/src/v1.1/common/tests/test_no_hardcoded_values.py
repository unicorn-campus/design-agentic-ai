"""소스에 시간 제한·재시도 숫자와 모델 벤더·모델 이름이 박히지 않았는지 스스로 확인함."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SOURCE_ROOT = Path(__file__).resolve().parents[1]

DESIGN_TIMEOUT_VALUES = {
    50, 80, 100, 120, 150, 200, 300, 500, 600, 800,
    1000, 1800, 2000, 3000, 4000, 5000, 6000, 2850, 2440, 1900,
}

MODEL_NAME_PATTERN = re.compile(
    r"claude-[a-z0-9.\-]+|gpt-[a-z0-9.\-]+|gemini-[a-z0-9.\-]+", re.IGNORECASE
)
VENDOR_PATTERN = re.compile(r"\b(anthropic|openai|google|bedrock|vertex)\b", re.IGNORECASE)


EXCLUDED_DIRS = {".venv", "tests", "model_adapters", "__pycache__"}

# `units.py`는 단위 환산 상수만 두는 파일이라 숫자 검사에서 빼고 따로 확인함.
UNIT_ONLY_FILE = "units.py"


def _production_files() -> list[Path]:
    return sorted(
        path
        for path in SOURCE_ROOT.rglob("*.py")
        if not EXCLUDED_DIRS.intersection(path.relative_to(SOURCE_ROOT).parts)
        and path.name != UNIT_ONLY_FILE
    )


def _adapter_files() -> list[Path]:
    return sorted(
        path
        for path in (SOURCE_ROOT / "model_adapters").rglob("*.py")
        if "__pycache__" not in path.parts
    )


def test_production_files_were_found() -> None:
    assert _production_files(), "검사할 소스 파일을 못 찾음"


@pytest.mark.parametrize("path", _production_files(), ids=lambda p: p.name)
def test_no_design_owned_numbers_in_source(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
        and node.value in DESIGN_TIMEOUT_VALUES
    ]
    assert not found, f"{path.name}에 설계서 소유 숫자가 박혀 있음: {found}"


@pytest.mark.parametrize("path", _production_files(), ids=lambda p: p.name)
def test_no_model_name_in_source(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert not MODEL_NAME_PATTERN.findall(text), f"{path.name}에 모델 이름이 박혀 있음"


@pytest.mark.parametrize("path", _production_files(), ids=lambda p: p.name)
def test_no_vendor_name_in_dispatch_code(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert not VENDOR_PATTERN.findall(text), f"{path.name}에 벤더 이름이 박혀 있음"


def test_unit_only_file_holds_nothing_but_the_conversion_factor() -> None:
    """단위 환산 파일이 설계서 값의 은닉처가 되지 않았는지 확인함."""
    from common.units import MS_PER_SECOND

    tree = ast.parse((SOURCE_ROOT / UNIT_ONLY_FILE).read_text(encoding="utf-8"))
    numbers = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    }
    assert numbers == {MS_PER_SECOND}


@pytest.mark.parametrize("path", _adapter_files(), ids=lambda p: p.name)
def test_adapter_pins_no_model_name(path: Path) -> None:
    """벤더 어댑터도 모델 이름은 주입받음. 벤더 이름은 모듈 이름이라 여기서만 허용함."""
    text = path.read_text(encoding="utf-8")
    assert not MODEL_NAME_PATTERN.findall(text), f"{path.name}에 모델 이름이 박혀 있음"
