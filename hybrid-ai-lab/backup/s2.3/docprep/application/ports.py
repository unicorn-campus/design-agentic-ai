"""응용 계층이 사용하는 입출력 계약. 구현체는 CLI에서 주입함."""
from pathlib import Path
from typing import Protocol


class PdfReader(Protocol):
    def __call__(self, path: Path, remove_margins: bool = True) -> tuple[list[dict], dict]: ...


class DocumentStore(Protocol):
    def read_text(self, path: Path) -> str: ...
    def load_markdown(self, path: Path) -> dict: ...
    def save(self, output: Path, documents: list[dict], reports: list[dict],
             validation: dict | None, write_report: bool, manifest: dict) -> None: ...
