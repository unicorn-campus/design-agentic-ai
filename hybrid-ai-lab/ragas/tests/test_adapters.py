"""어댑터 · 계층 규칙 · 명령행 시험(외부 서비스 없음). live 표시 시험은 실제 색인 · 로컬 평가자가 있어야 함."""

from __future__ import annotations

import asyncio
from pathlib import Path
import re

import pytest

from app.application.models import QualityError
from app.infrastructure.files import ActiveCorpusReader, ActivePointer, LocalArtifactStore, RunnerLock
from app.infrastructure.processes import IndexerProcess
from app.infrastructure.settings import load_settings
from app.presentation.cli import main

APP = Path(__file__).resolve().parents[1] / "app"
FORBIDDEN = re.compile(r"^\s*(from|import)\s+(ragas|openai|anthropic|langchain|yaml|subprocess|urllib|torch)\b", re.M)


def test_layer_imports_point_inward_only():
    """domain · application은 외부 기술을 import하지 않고, presentation은 infrastructure를 import하지 않음."""

    for layer in ("domain", "application"):
        for path in (APP / layer).glob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert not FORBIDDEN.search(source), path
            assert "app.infrastructure" not in source and "app.presentation" not in source, path
    for path in (APP / "domain").glob("*.py"):
        assert "app.application" not in path.read_text(encoding="utf-8"), path
    assert "app.infrastructure" not in (APP / "presentation" / "cli.py").read_text(encoding="utf-8")


def test_ports_have_abstract_methods():
    from app.application import ports

    for name in dir(ports):
        cls = getattr(ports, name)
        if name.endswith("Port"):
            methods = [m for m in vars(cls) if not m.startswith("_")]
            assert methods and all(getattr(getattr(cls, m), "__isabstractmethod__", False) for m in methods), name


def test_store_writes_atomically_and_reads_bom(tmp_path: Path):
    store = LocalArtifactStore()
    store.write_json(tmp_path / "a" / "b.json", {"한글": 1})
    assert store.read_json(tmp_path / "a" / "b.json") == {"한글": 1}
    (tmp_path / "bom.json").write_bytes(b"\xef\xbb\xbf{\"x\": 2}")
    assert store.read_json(tmp_path / "bom.json") == {"x": 2}
    assert not list((tmp_path / "a").glob(".tmp-*"))


def test_pointer_write_round_trip_and_missing_pointer(tmp_path: Path):
    pointer = ActivePointer(tmp_path)
    with pytest.raises(QualityError):
        pointer.read()
    sha = pointer.write({"generation": "gen-a"})
    assert pointer.read() == {"generation": "gen-a"} and sha == pointer.sha256()


def test_runner_lock_rejects_second_holder(tmp_path: Path):
    first, second = RunnerLock(tmp_path / ".runner.lock"), RunnerLock(tmp_path / ".runner.lock")
    first.acquire()
    try:
        with pytest.raises(QualityError):
            second.acquire()
    finally:
        first.release()
    second.acquire()
    second.release()


def test_indexer_process_reads_generation_and_classifies_exit_codes(tmp_path: Path):
    """가짜 run_indexer.py로 결과 JSON 읽기 · 종료 코드 분류를 확인함(실제 인덱서는 부르지 않음)."""

    import sys

    script = tmp_path / "run_indexer.py"
    script.write_text('import json,sys\nprint("{\\"status\\":\\"ok\\",\\"index\\":{\\"generation\\":\\"gen-x\\"}}")\n',
                      encoding="utf-8")
    assert IndexerProcess(Path(sys.executable), tmp_path).reindex("t", {}, tmp_path / "logs") == "gen-x"
    script.write_text("import sys\nsys.exit(130)\n", encoding="utf-8")
    with pytest.raises(QualityError) as error:
        IndexerProcess(Path(sys.executable), tmp_path).reindex("t", {}, tmp_path / "logs")
    assert error.value.code == "E-INT"


def test_settings_prefers_environment_and_accepts_team_key_name(monkeypatch):
    monkeypatch.setenv("RAGAS_CONCURRENCY", "2")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    settings = load_settings({"CLAUDE_API_KEY": "test-key"})
    assert settings.ragas_concurrency == 2 and settings.anthropic_api_key == "test-key"
    assert "test-key" not in repr(settings)  # 비밀값은 repr에 나오지 않음


class _FakeRunner:
    def preflight(self, plan_path):
        raise QualityError("plan_rejected", "V14 서버가 떠 있음", 2)


class _FakeServices:
    runner = _FakeRunner()


def test_cli_returns_reject_exit_code():
    assert main(["run", "--plan", "x.yaml", "--check-only"], services_factory=lambda: _FakeServices()) == 2


@pytest.mark.live
def test_live_corpus_reader_reads_active_generation():
    """실제 사용 중 세대의 말뭉치를 읽음(인덱서 data가 있어야 함)."""

    reader = ActiveCorpusReader(load_settings().data_root)
    chunks = reader.chunks()
    assert reader.active_generation().startswith("gen-") and len(chunks) > 100
    assert any(chunk.benefit_ids for chunk in chunks)


@pytest.mark.live
def test_live_local_judge_scores_one_metric():
    """로컬 평가자(Ollama Qwen3.5-9B)로 지표 하나를 실제 채점함."""

    from app.bootstrap import create_judge_factory

    judge = create_judge_factory(load_settings())("local")
    value, _ = asyncio.run(judge.score("context_recall", {
        "user_input": "연회비 면제 기준은?", "reference": "직전 12개월 이용금액이 3,000,000원 이상이면 면제",
        "retrieved_contexts": ["직전 12개월 이용금액이 3,000,000원 이상이고 연체가 없으면 기본 연회비를 면제합니다."]}))
    assert 0.0 <= value <= 1.0
