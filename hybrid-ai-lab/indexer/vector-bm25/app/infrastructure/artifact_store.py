"""정제된 청크와 벡터를 체크포인트에서 다시 읽을 수 있는 JSON 산출물로 저장함."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from app.application.ports import ArtifactStorePort


_SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")  # 경로 구분자를 막고 이름을 128자 이내로 제한함


class JsonArtifactStore(ArtifactStorePort):
    """실행별 산출물을 JSON으로 보관하고 저장소 내부의 참조만 허용함.

    저장 루트를 생성자로 받으며, 입력 데이터의 개인정보 제거와 스키마 검증은 호출자가 맡아야 함.
    """

    def __init__(self, root: Path) -> None:
        """산출물 루트를 절대 경로로 고정하고 디렉터리가 없으면 생성함."""
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _segment(value: str, label: str) -> str:
        """파일명에 사용할 수 없는 값이나 상위 경로 표시는 ValueError로 거부함."""
        if not _SAFE_SEGMENT.fullmatch(value) or value in {".", ".."}:
            raise ValueError(f"{label} 형식이 올바르지 않습니다.")
        return value

    def _path(self, run_id: str, name: str) -> Path:
        """실행·산출물 이름을 검증하고 실제 저장 위치가 루트 내부인지 확인함."""
        run = self._segment(str(run_id), "run_id")
        item = self._segment(str(name), "산출물 이름")
        path = (self.root / run / f"{item}.json").resolve()
        if not path.is_relative_to(self.root):
            raise ValueError("산출물 경로가 저장소 밖을 가리킵니다.")
        return path

    def save(self, run_id: str, name: str, value: Any) -> str:
        """완성된 JSON만 보이도록 같은 디렉터리의 임시 파일을 원자적으로 교체함.

        인자: value는 개인정보 처리를 끝낸 JSON 직렬화 가능 값이어야 함.
        반환값: 다른 프로세스도 load에 전달할 수 있는 저장 루트 기준 상대 경로임.
        예외: 이름·경로 검증은 ValueError, 직렬화 불가 값은 TypeError, 파일 쓰기 실패는 OSError가 발생함.
        부수효과: 디렉터리를 만들고 같은 실행·이름의 산출물을 덮어쓰며 임시 파일은 정리함.
        """
        path = self._path(run_id, name)
        if path.exists() and path.is_symlink():
            raise ValueError("심볼릭 링크 산출물에는 저장할 수 없습니다.")
        payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".artifact-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return path.relative_to(self.root).as_posix()

    def load(self, reference: str) -> Any:
        """체크포인트가 가리키는 저장소 내부 JSON을 다시 읽음.

        인자: save가 반환한 상대 경로임. 절대 경로와 루트 밖으로 벗어나는 참조는 허용하지 않음.
        반환값: JSON을 역직렬화한 값이며 내용의 업무 검증은 호출자가 수행해야 함.
        예외: 잘못된 경로는 ValueError, 없는 파일은 FileNotFoundError, 손상된 JSON은 JSONDecodeError임.
        부수효과: 파일을 읽기만 하며 저장된 산출물을 변경하지 않음.
        """
        relative = Path(str(reference))
        path = (self.root / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(self.root):
            raise ValueError("산출물 참조가 저장소 밖을 가리킵니다.")
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"산출물을 찾을 수 없습니다: {reference}")
        return json.loads(path.read_text(encoding="utf-8-sig"))


__all__ = ["JsonArtifactStore"]
