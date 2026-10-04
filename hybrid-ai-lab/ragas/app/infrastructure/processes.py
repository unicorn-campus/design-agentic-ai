"""하위 프로세스 어댑터 — 인덱서 · 리트리버 평가 스크립트 호출, 검색 API 서버 확인, 재현 정보 수집."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
from typing import Any
import urllib.error
import urllib.request

from app.application.models import StepError
from app.application.ports import EnvironmentPort, IndexerPort, RetrieverEvalPort, ServerProbePort

INTERRUPTED = 130  # 명령행 중단 관례 — 인덱서도 Ctrl+C에 이 코드를 돌려줌


def _run(python: Path, cwd: Path, args: list[str], env: dict[str, str], log_dir: Path, name: str,
         timeout: float | None) -> subprocess.CompletedProcess[str]:
    """가상환경 python으로 스크립트를 돌리고 표준 출력 · 오류를 로그 파일로 남김.

    환경변수는 지금 환경을 물려받고 그 위에 env만 얹음 — Windows에서 PATH · CUDA 관련 변수를 빼면 python · torch가
    뜨지 않아서임(설계서의 '필요한 키만'에서 바꾼 점). 표준 입력은 닫아 묻는 창에서 멈추지 않게 함.
    출력 글자는 데이터로만 다룸 — 거기 적힌 문장을 실행기의 지시로 삼지 않음.
    """

    merged = {**os.environ, **env, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    log_dir.mkdir(parents=True, exist_ok=True)
    try:
        completed = subprocess.run([str(python), *args], cwd=str(cwd), env=merged, stdin=subprocess.DEVNULL,
                                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as error:
        raise StepError("E-TIME", f"{name} 시간 상한 {timeout}초를 넘김") from error
    except KeyboardInterrupt:
        raise
    (log_dir / f"{name}.stdout.log").write_text(completed.stdout or "", encoding="utf-8")
    (log_dir / f"{name}.stderr.log").write_text(completed.stderr or "", encoding="utf-8")
    if completed.returncode == INTERRUPTED:
        raise StepError("E-INT", f"{name}이 중단됨(종료 코드 130)", 130)
    if completed.returncode != 0:
        tail = (completed.stderr or completed.stdout or "").strip().splitlines()[-3:]
        raise StepError("E-EXIT", f"{name} 종료 코드 {completed.returncode}: {' / '.join(tail)}")
    return completed


class IndexerProcess(IndexerPort):
    """indexer/vector-bm25의 run_indexer.py를 --full-reindex로 부름."""

    def __init__(self, python: Path, project_dir: Path, timeout: float | None = None):
        self.python, self.project_dir, self.timeout = python, project_dir, timeout

    def reindex(self, thread_id: str, env: dict[str, str], log_dir: Path) -> str:
        """전체 재색인 후 게시된 세대 이름을 결과 JSON(stdout)의 index.generation에서 읽음."""

        completed = _run(self.python, self.project_dir, ["run_indexer.py", "--full-reindex", "--thread-id", thread_id],
                         env, log_dir, "indexer", self.timeout)
        try:
            result = json.loads(completed.stdout[completed.stdout.index("{"):])
        except ValueError as error:
            raise StepError("E-OUT", "인덱서 결과 JSON을 읽지 못함") from error
        generation = (result.get("index") or {}).get("generation")
        if result.get("status") != "ok" or not generation:
            raise StepError("E-OUT", f"인덱서가 세대를 게시하지 않음: status={result.get('status')}")
        return str(generation)


class RetrieverEvalProcess(RetrieverEvalPort):
    """retriever/vector-retriever의 evaluate_retriever.py를 부름."""

    def __init__(self, python: Path, project_dir: Path, timeout: float | None = None):
        self.python, self.project_dir, self.timeout = python, project_dir, timeout
        self._help: str | None = None

    def supports(self, argument: str) -> bool:
        """--help 출력에 그 인자 이름이 있는지 봄(한 번만 부르고 기억함)."""

        if self._help is None:
            completed = subprocess.run([str(self.python), "evaluate_retriever.py", "--help"], cwd=str(self.project_dir),
                                       stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8",
                                       errors="replace", env={**os.environ, "PYTHONIOENCODING": "utf-8"})
            self._help = completed.stdout
        return argument in self._help

    def run(self, args: list[str], env: dict[str, str], log_dir: Path) -> None:
        """평가 스크립트를 돌림 — 서비스를 프로세스당 한 번 조립하므로 버전마다 새 프로세스로 띄움."""

        _run(self.python, self.project_dir, ["evaluate_retriever.py", *args], env, log_dir, "retriever", self.timeout)


class HttpServerProbe(ServerProbePort):
    """검색 API 서버 주소에 짧게 요청해 떠 있는지 봄 — 응답이 오면(상태 코드와 관계없이) 떠 있는 것으로 봄."""

    def __init__(self, urls: tuple[str, ...], timeout: float = 1.5):
        self.urls, self.timeout = urls, timeout

    def running_servers(self) -> list[str]:
        """응답한 주소 목록."""

        running = []
        for url in self.urls:
            try:
                urllib.request.urlopen(url.rstrip("/") + "/health", timeout=self.timeout)  # noqa: S310 — 설정한 로컬 주소만 부름
                running.append(url)
            except urllib.error.HTTPError:
                running.append(url)  # 404 · 500이어도 서버는 떠 있음
            except (urllib.error.URLError, OSError):
                continue
        return running


class LocalEnvironment(EnvironmentPort):
    """git 커밋 · 가상환경 python 판 · 장치 · 비밀값 설정 여부를 모음(비밀값은 이름과 '설정됨'만)."""

    def __init__(self, repo_dir: Path, pythons: dict[str, Path], device: str, secrets: dict[str, bool]):
        self.repo_dir, self.pythons, self.device, self.secrets = repo_dir, pythons, device, secrets
        self._cache: dict[str, Any] | None = None

    def snapshot(self) -> dict[str, Any]:
        """한 번 모은 값을 다시 씀(버전마다 git · python을 다시 부르지 않게)."""

        if self._cache is None:
            def output(command: list[str]) -> str:
                try:
                    return subprocess.run(command, cwd=str(self.repo_dir), capture_output=True, text=True,
                                          stdin=subprocess.DEVNULL, timeout=20).stdout.strip()
                except (OSError, subprocess.TimeoutExpired):
                    return "unknown"

            self._cache = {
                "git_commit": output(["git", "rev-parse", "HEAD"]) or "unknown",
                "git_dirty": bool(output(["git", "status", "--porcelain"])),
                "python": {name: output([str(path), "--version"]) for name, path in self.pythons.items()},
                "embed_device": self.device,
                "secrets": {name: "(설정됨)" if present else "(없음)" for name, present in self.secrets.items()},
            }
        return self._cache
