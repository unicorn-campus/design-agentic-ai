"""환경변수 · .env에서 경로 · 평가자 · 임베딩 설정을 읽음. 비밀값은 코드에 두지 않음."""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Mapping

from dotenv import dotenv_values

APP_ROOT = Path(__file__).resolve().parents[2]  # hybrid-ai-lab/ragas
LAB_ROOT = APP_ROOT.parent  # hybrid-ai-lab


def _venv_python(project: Path) -> Path:
    """프로젝트 .venv의 python 실행 파일 — Windows는 Scripts, macOS · Linux는 bin 아래에 있음."""

    windows = project / ".venv" / "Scripts" / "python.exe"
    return windows if windows.exists() else project / ".venv" / "bin" / "python"


@dataclass(frozen=True)
class Settings:
    """품질평가 프로그램 설정. bootstrap이 한 번 읽어 어댑터에 나눠 줌."""

    app_root: Path
    indexer_dir: Path
    retriever_dir: Path
    data_root: Path  # 인덱서 결과 폴더(사용 중 세대 포인터가 있음)
    experiments_root: Path
    indexer_python: Path
    retriever_python: Path
    ollama_base_url: str  # 로컬 평가자 — Ollama의 OpenAI 호환 주소
    local_model: str
    anthropic_model: str
    groq_model: str
    groq_base_url: str
    embed_model: str
    embed_revision: str
    embed_device: str  # auto면 CUDA가 있을 때 cuda, 없으면 cpu
    hf_local_files_only: bool
    ragas_concurrency: int
    ragas_max_tokens: int
    retriever_api_urls: tuple[str, ...]  # 실험 전 꺼져 있어야 하는 검색 API 서버 주소(V14)
    anthropic_api_key: str | None = field(default=None, repr=False)
    groq_api_key: str | None = field(default=None, repr=False)
    process_timeout_seconds: float | None = None  # 하위 프로세스 시간 상한 — 근거가 없어 기본은 없음(결정 필요)


def load_settings(overrides: Mapping[str, str] | None = None) -> Settings:
    """환경변수 → ragas/.env → hybrid-ai-lab/.env 순으로 값을 고름(앞이 우선).

    부수효과: .env 파일을 읽기만 함. 예외: 숫자 칸에 숫자가 아니면 ValueError.
    """

    values = {**dotenv_values(LAB_ROOT / ".env"), **dotenv_values(APP_ROOT / ".env"), **os.environ, **(overrides or {})}

    def text(key: str, default: str = "") -> str:
        value = values.get(key)
        return str(value).strip() if value not in (None, "") else default

    def path(key: str, default: Path) -> Path:
        raw = text(key)
        if not raw:
            return default.resolve()
        candidate = Path(raw).expanduser()
        return (candidate if candidate.is_absolute() else APP_ROOT / candidate).resolve()

    indexer_dir = path("INDEXER_DIR", LAB_ROOT / "indexer" / "vector-bm25")
    retriever_dir = path("RETRIEVER_DIR", LAB_ROOT / "retriever" / "vector-retriever")
    timeout = text("PROCESS_TIMEOUT_SECONDS")
    return Settings(
        app_root=APP_ROOT,
        indexer_dir=indexer_dir,
        retriever_dir=retriever_dir,
        data_root=path("DATA_ROOT", indexer_dir / "data"),
        experiments_root=path("EXPERIMENTS_ROOT", APP_ROOT / "experiments"),
        indexer_python=path("INDEXER_PYTHON", _venv_python(indexer_dir)),
        retriever_python=path("RETRIEVER_PYTHON", _venv_python(retriever_dir)),
        ollama_base_url=text("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
        local_model=text("JUDGE_LOCAL_MODEL", "hf.co/unsloth/Qwen3.5-9B-GGUF:Q4_K_M"),
        anthropic_model=text("JUDGE_ANTHROPIC_MODEL", "claude-opus-5-5"),
        groq_model=text("JUDGE_GROQ_MODEL", "openai/gpt-oss-120b"),
        groq_base_url=text("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
        embed_model=text("EMBED_MODEL", "nlpai-lab/KURE-v2"),
        embed_revision=text("EMBED_REVISION", "3431f86d399d666083890dbb882aced6708873bc"),
        embed_device=text("EMBED_DEVICE", "auto"),
        hf_local_files_only=text("HF_LOCAL_FILES_ONLY", "true").lower() in {"1", "true", "yes"},
        ragas_concurrency=int(text("RAGAS_CONCURRENCY", "4")),
        ragas_max_tokens=int(text("RAGAS_MAX_TOKENS", "2048")),
        retriever_api_urls=tuple(u.strip() for u in text("RETRIEVER_API_URLS", "http://127.0.0.1:8020").split(",")
                                 if u.strip()),
        # 팀 공용 .env는 CLAUDE_API_KEY 이름을 씀 — Anthropic SDK 기본 이름(ANTHROPIC_API_KEY)도 함께 받음
        anthropic_api_key=text("ANTHROPIC_API_KEY") or text("CLAUDE_API_KEY") or None,
        groq_api_key=text("GROQ_API_KEY") or None,
        process_timeout_seconds=float(timeout) if timeout else None,
    )
