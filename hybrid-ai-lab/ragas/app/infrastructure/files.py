"""파일 기반 어댑터 — 결과 파일 저장소 · 사용 중 세대 포인터 · 실행기 잠금 · 색인 말뭉치 읽기."""

from __future__ import annotations

import csv
import hashlib
import importlib
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any, BinaryIO

import yaml

from app.application.models import QualityError
from app.application.ports import ArtifactStorePort, CorpusPort, LockPort, PointerPort
from app.domain.verification import Chunk

POINTER_NAME = "active_generation.json"  # 인덱서 · 리트리버가 함께 보는 사용 중 세대 포인터
SEARCH_POINTER_NAME = "active_index.json"  # 세대 안쪽 텍스트 색인 포인터(말뭉치 위치가 적혀 있음)


def _atomic_write(path: Path, payload: bytes) -> None:
    """같은 폴더 임시 파일에 쓰고 fsync 후 바꿔치기함 — 인덱서가 포인터를 바꾸는 방식과 같음."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".tmp-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class LocalArtifactStore(ArtifactStorePort):
    """로컬 파일 시스템 저장소. 쓰기는 모두 원자적 바꿔치기로 함."""

    def exists(self, path: Path) -> bool:
        """파일이 있는지 봄."""

        return Path(path).is_file()

    def read_text(self, path: Path) -> str:
        """BOM을 떼고 UTF-8로 읽음."""

        return Path(path).read_text(encoding="utf-8-sig")

    def read_json(self, path: Path) -> Any:
        """JSON을 읽음."""

        return json.loads(self.read_text(path))

    def read_yaml(self, path: Path) -> Any:
        """YAML을 읽음 — safe_load라 파일 속 파이썬 객체 생성 태그는 실행하지 않음."""

        return yaml.safe_load(self.read_text(path))

    def write_text(self, path: Path, text: str) -> None:
        """UTF-8로 원자적으로 씀."""

        _atomic_write(Path(path), text.encode("utf-8"))

    def write_json(self, path: Path, value: Any) -> None:
        """들여쓰기 2칸 · 한글 그대로 원자적으로 씀."""

        self.write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")

    def append_text(self, path: Path, text: str) -> None:
        """파일 끝에 덧붙임(실험 세대 목록은 한 줄씩 쌓이므로 원자적 바꿔치기가 필요 없음)."""

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with Path(path).open("a", encoding="utf-8", newline="") as stream:
            stream.write(text)

    def read_csv(self, path: Path) -> list[dict[str, str]]:
        """머리 행 기준 dict 목록으로 읽음(엑셀이 붙인 BOM 허용)."""

        return list(csv.DictReader(io.StringIO(self.read_text(path))))

    def write_csv(self, path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
        """BOM 붙은 UTF-8로 씀 — 엑셀이 BOM이 없으면 한글을 ANSI로 읽어 깨뜨림."""

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=header, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows([{k: "" if v is None else v for k, v in row.items()} for row in rows])
        _atomic_write(Path(path), ("﻿" + buffer.getvalue()).encode("utf-8"))


class _OsFileLock:
    """운영체제 파일 잠금을 기다리지 않고 거는 작은 도우미(인덱서 잠금과 같은 방식 — 첫 바이트 구간 잠금)."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._stream: BinaryIO | None = None

    def acquire(self) -> bool:
        """잠금을 얻으면 True, 다른 프로세스가 잡고 있으면 False."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        stream = self.path.open("a+b")
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")  # Windows 구간 잠금에 필요한 첫 바이트 — 내용은 상태를 뜻하지 않음
            stream.flush()
        stream.seek(0)
        try:
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                fcntl = importlib.import_module("fcntl")
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            stream.close()
            return False
        self._stream = stream
        return True

    def release(self) -> None:
        """잡은 잠금을 놓음."""

        if self._stream is None:
            return
        self._stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(self._stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            importlib.import_module("fcntl").flock(self._stream.fileno(), importlib.import_module("fcntl").LOCK_UN)
        self._stream.close()
        self._stream = None


class RunnerLock(LockPort):
    """experiments/.runner.lock — 포인터가 실험 세대인 동안 다른 실행기가 끼어들지 못하게 막음."""

    def __init__(self, path: Path):
        self._lock = _OsFileLock(path)

    def acquire(self) -> None:
        """기다리지 않고 잠금을 얻음."""

        if not self._lock.acquire():
            raise QualityError("lock_unavailable", f"다른 실행기가 실험 중임: {self._lock.path}", 2)

    def release(self) -> None:
        """잠금을 놓음."""

        self._lock.release()


class ActivePointer(PointerPort):
    """인덱서 data 폴더의 사용 중 세대 포인터 파일."""

    def __init__(self, data_root: Path):
        self.path = Path(data_root) / POINTER_NAME
        # 인덱서 게시와 같은 잠금 파일을 잡아, 게시 도중에 실행기가 포인터를 덮어쓰지 않게 함
        self._publish_lock = _OsFileLock(Path(data_root) / ".publish.lock")

    def read(self) -> dict[str, Any]:
        """포인터 내용을 읽음."""

        try:
            return json.loads(self.path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            raise QualityError("pointer_unavailable", f"사용 중 세대 포인터를 읽지 못함: {self.path} ({error})") from error

    def sha256(self) -> str:
        """포인터 파일 바이트의 SHA-256."""

        return hashlib.sha256(self.path.read_bytes()).hexdigest()

    def write(self, content: dict[str, Any]) -> str:
        """게시 잠금을 잡고 포인터를 원자적으로 바꿈."""

        if not self._publish_lock.acquire():
            raise QualityError("lock_unavailable", "인덱서가 게시 중이라 포인터를 바꾸지 못함")
        try:
            _atomic_write(self.path, (json.dumps(content, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        finally:
            self._publish_lock.release()
        return self.sha256()


class ActiveCorpusReader(CorpusPort):
    """사용 중 세대의 말뭉치(corpus.jsonl)에서 조각 본문을 읽음 — 리트리버가 읽는 것과 같은 파일."""

    def __init__(self, data_root: Path):
        self.data_root = Path(data_root)

    def _pointer(self) -> dict[str, Any]:
        """사용 중 세대 포인터."""

        try:
            return json.loads((self.data_root / POINTER_NAME).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as error:
            raise QualityError("index_unavailable", f"사용 중 세대 포인터가 없음: {self.data_root}") from error

    def active_generation(self) -> str:
        """사용 중 세대 이름."""

        return str(self._pointer().get("generation"))

    def chunks(self) -> list[Chunk]:
        """말뭉치 한 줄 = 조각 하나. 혜택 코드는 메타데이터 benefit_id_all(JSON 글)에서 읽음."""

        pointer = self._pointer()
        search_root = self.data_root / str(pointer["search_index_root"])
        try:
            corpus = search_root / json.loads((search_root / SEARCH_POINTER_NAME).read_text(encoding="utf-8-sig"))["corpus"]
            lines = corpus.read_text(encoding="utf-8-sig").splitlines()
        except (OSError, ValueError, KeyError) as error:
            raise QualityError("index_unavailable", f"말뭉치를 읽지 못함: {search_root} ({error})") from error
        chunks = []
        for line in lines:
            if not line.strip():
                continue
            row = json.loads(line)
            metadata = row.get("metadata") or {}
            try:
                benefits = tuple(json.loads(metadata.get("benefit_id_all") or "[]"))
            except ValueError:
                benefits = ()
            chunks.append(Chunk(chunk_id=str(row["chunk_id"]), source=str(metadata.get("source", "")),
                                text=str(row["text"]), benefit_ids=benefits))
        return chunks
