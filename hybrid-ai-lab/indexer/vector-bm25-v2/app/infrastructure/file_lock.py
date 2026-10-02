"""프로세스 종료 시 운영체제가 해제하는 파일 잠금으로 동시 쓰기를 조정함."""

from __future__ import annotations

from pathlib import Path
import importlib
import os
from threading import Lock, get_ident
from typing import BinaryIO, ClassVar


class LockUnavailableError(RuntimeError):
    """다른 실행이 잠금을 보유해 현재 쓰기 작업을 시작할 수 없음을 나타냄."""

    pass


class CrossPlatformFileLock:
    """같은 스레드의 중첩 사용을 허용하고 다른 실행의 잠금 경쟁은 즉시 거부함.

    잠금 파일 경로를 받으며, 파일에 인덱싱 상태를 기록하거나 다른 실행을 강제로 종료하지 않음.
    잠금 파일이 남아 있더라도 운영체제 잠금 보유 여부로 사용 가능성을 판정함.
    """

    _guard: ClassVar[Lock] = Lock()  # 프로세스 안에서 잠금 소유 기록을 동시에 바꾸지 못하도록 보호함
    _held: ClassVar[dict[Path, tuple[BinaryIO, int, int]]] = {}  # 경로별 파일 핸들·중첩 횟수·소유 스레드 ID

    def __init__(self, path: Path) -> None:
        """같은 파일을 다른 상대 경로로 중복 인식하지 않도록 경로를 정규화함."""
        self.path = Path(path).resolve()
        self._acquire_count = 0

    @staticmethod
    def _os_lock(stream: BinaryIO) -> None:
        """운영체제별 비차단 잠금을 걸어 사용 중인 파일을 기다리지 않고 실패하게 함."""
        # Windows의 바이트 구간 잠금에 필요한 첫 바이트를 확보함. 내용은 실행 상태를 뜻하지 않음.
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"\0")
            stream.flush()
            os.fsync(stream.fileno())
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            fcntl = importlib.import_module("fcntl")
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)

    @staticmethod
    def _os_unlock(stream: BinaryIO) -> None:
        """획득할 때와 같은 위치와 운영체제 방식으로 파일 잠금을 해제함."""
        stream.seek(0)
        if os.name == "nt":
            import msvcrt

            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            fcntl = importlib.import_module("fcntl")
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)

    def acquire(self) -> None:
        """다른 쓰기 작업과 충돌하지 않도록 잠금을 얻고 중첩 횟수를 기록함.

        방법: 같은 스레드의 재진입은 횟수만 늘리고 최초 진입이면 운영체제 잠금을 확보함.
        반환값: 없음. 정상 반환 후 이 스레드가 잠금을 보유함.
        예외: 다른 스레드가 보유하거나 운영체제 잠금 호출이 실패하면 LockUnavailableError가 발생함.
        예외: 디렉터리·파일 생성 실패는 OSError 계열 예외로 전달됨.
        부수효과: 잠금 파일과 디렉터리를 만들 수 있으며 프로세스 내부 소유 기록을 갱신함.
        """
        owner = get_ident()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._guard:
            current = self._held.get(self.path)
            if current is not None:
                stream, count, current_owner = current
                if current_owner != owner:
                    raise LockUnavailableError("다른 스레드가 인덱싱 쓰기 잠금을 사용 중입니다.")
                self._held[self.path] = (stream, count + 1, owner)
                self._acquire_count += 1
                return
            stream = self.path.open("a+b")
            try:
                self._os_lock(stream)
            except OSError as error:
                stream.close()
                raise LockUnavailableError("다른 프로세스가 인덱싱 쓰기 잠금을 사용 중입니다.") from error
            self._held[self.path] = (stream, 1, owner)
            self._acquire_count += 1

    def release(self) -> None:
        """호출자의 잠금 보유 횟수를 줄이고 마지막 사용이 끝나면 잠금과 파일 핸들을 해제함.

        인자: acquire를 수행한 스레드에서 획득한 횟수만큼 호출해야 함.
        반환값: 없음. 중첩 사용이 남아 있으면 운영체제 잠금은 유지됨.
        예외: 획득하지 않았거나 소유 스레드가 아니면 RuntimeError, 운영체제 해제 실패는 OSError임.
        부수효과: 소유 기록을 갱신하고 마지막 해제 시 핸들을 닫음. 잠금 파일은 삭제하지 않음.
        """
        if self._acquire_count <= 0:
            raise RuntimeError("획득하지 않은 파일 잠금은 해제할 수 없습니다.")
        owner = get_ident()
        with self._guard:
            stream, count, current_owner = self._held[self.path]
            if current_owner != owner:
                raise RuntimeError("파일 잠금을 획득한 스레드에서만 해제할 수 있습니다.")
            self._acquire_count -= 1
            if count > 1:
                self._held[self.path] = (stream, count - 1, owner)
                return
            try:
                self._os_unlock(stream)
            finally:
                stream.close()
                self._held.pop(self.path, None)

    def __enter__(self) -> "CrossPlatformFileLock":
        """with 블록에 들어가기 전에 잠금을 확보하고 현재 잠금 객체를 반환함."""
        self.acquire()
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        """with 블록의 성공 여부와 관계없이 잠금 해제를 시도하고 예외 억제를 요청하지 않음."""
        self.release()


__all__ = ["CrossPlatformFileLock", "LockUnavailableError"]
