"""계층 안쪽 코드가 바깥 계층을 import하지 않는지 검증함."""

import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "app"


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


class ArchitectureTest(unittest.TestCase):
    def test_domain_does_not_import_outer_layers(self) -> None:
        forbidden = ("application", "infrastructure", "presentation", "bootstrap")
        for path in (PACKAGE / "domain").glob("*.py"):
            with self.subTest(path=path.name):
                imports = imported_modules(path)
                self.assertFalse(any(any(part in module for part in forbidden) for module in imports))

    def test_application_does_not_import_infrastructure_or_presentation(self) -> None:
        forbidden = ("infrastructure", "presentation", "bootstrap")
        for path in (PACKAGE / "application").glob("*.py"):
            with self.subTest(path=path.name):
                imports = imported_modules(path)
                self.assertFalse(any(any(part in module for part in forbidden) for module in imports))


if __name__ == "__main__":
    unittest.main()
