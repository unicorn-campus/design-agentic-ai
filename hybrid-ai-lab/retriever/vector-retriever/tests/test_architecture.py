"""계층 import 규칙(레이어드 가이드 §2 · §7)을 소스 정적 분석으로 지킴을 보증함."""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
# 실행 기술. application·domain에서 import하면 DIP 위반임(가이드 §4 '외부 기술 최소화')
FORBIDDEN_TECH = {
    "psycopg", "langchain", "langchain_core", "langgraph", "httpx", "requests", "chromadb", "openai", "groq",
    "bm25s", "kiwipiepy", "sentence_transformers", "torch", "transformers", "fastapi", "uvicorn", "numpy",
}


def _imports(path: Path) -> set[str]:
    """파일이 import하는 모듈의 전체 이름 집합을 반환함."""

    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefix = "." * node.level
            names.add(prefix + node.module)
    return names


def _files(layer: str) -> list[Path]:
    return sorted((APP / layer).rglob("*.py"))


def test_domain_imports_only_standard_library():
    for path in _files("domain"):
        for name in _imports(path):
            assert not name.startswith(("app.", "..")), f"{path.name}: domain이 다른 계층 import — {name}"
            assert name.split(".")[0] not in FORBIDDEN_TECH, f"{path.name}: 외부 기술 import — {name}"


def test_application_does_not_import_infrastructure_or_technology():
    for path in _files("application"):
        for name in _imports(path):
            assert "infrastructure" not in name and "presentation" not in name, f"{path.name}: {name}"
            assert name.lstrip(".").split(".")[0] not in FORBIDDEN_TECH, f"{path.name}: 외부 기술 import — {name}"


def test_presentation_does_not_import_infrastructure_directly():
    for path in _files("presentation"):
        for name in _imports(path):
            assert "infrastructure" not in name, f"{path.name}: bootstrap을 거치지 않은 구현체 import — {name}"


def test_ports_are_abstract_protocols():
    tree = ast.parse((APP / "application" / "ports.py").read_text(encoding="utf-8"))
    for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
        assert any(getattr(b, "id", "") == "Protocol" for b in cls.bases), cls.name
        for method in [n for n in cls.body if isinstance(n, ast.FunctionDef)]:
            decorators = {getattr(d, "id", "") for d in method.decorator_list}
            assert "abstractmethod" in decorators, f"{cls.name}.{method.name}에 @abstractmethod 없음"
