"""Layered Architecture의 import 방향을 AST로 확인함."""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "app"
TECHNOLOGY_ROOTS = {
    "chromadb",
    "httpx",
    "langchain",
    "langchain_core",
    "langchain_text_splitters",
    "langgraph",
    "openai",
    "psycopg",
    "requests",
    "sentence_transformers",
}


def imports(path: Path) -> list[str]:
    """파일의 import 대상 이름을 AST(소스 구문 트리)에서 수집함."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            result.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            result.append(node.module)
    return result


def python_files(layer: str) -> list[Path]:
    """지정한 계층에 속한 파이썬 파일을 정렬하여 반환함."""
    directory = ROOT / layer
    return sorted(directory.rglob("*.py")) if directory.exists() else []


def test_domain_has_no_inward_or_technology_dependency() -> None:
    """domain 계층이 외부 기술이나 바깥 계층에 의존하지 않음을 보증함."""
    violations: list[str] = []
    for path in python_files("domain"):
        for name in imports(path):
            root = name.split(".", 1)[0]
            if root in TECHNOLOGY_ROOTS or (
                name.startswith("app.") and not name.startswith("app.domain")
            ):
                violations.append(f"{path.relative_to(ROOT)} -> {name}")
    assert violations == []


def test_application_does_not_import_infrastructure_or_execution_sdks() -> None:
    """application 계층이 구현 계층과 실행 SDK를 직접 가져오지 않음을 보증함."""
    violations: list[str] = []
    for path in python_files("application"):
        for name in imports(path):
            root = name.split(".", 1)[0]
            if root in TECHNOLOGY_ROOTS or name.startswith(("app.infrastructure", "app.presentation")):
                violations.append(f"{path.relative_to(ROOT)} -> {name}")
    assert violations == []


def test_presentation_reaches_implementations_only_through_bootstrap() -> None:
    """presentation 계층이 infrastructure 구현체에 직접 접근하지 않음을 보증함."""
    violations: list[str] = []
    for path in python_files("presentation"):
        for name in imports(path):
            if name.startswith("app.infrastructure"):
                violations.append(f"{path.relative_to(ROOT)} -> {name}")
    assert violations == []
