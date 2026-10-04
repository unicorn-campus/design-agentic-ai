"""실행기 흐름 시험 — 되돌리기 · 실패 처리 · 이어 하기 · 실행 전 거부 · 중단을 가짜 포트로 검증함."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from app.application.compare_service import CompareService
from app.application.models import FAILED, SKIPPED, SUCCESS, UNSUPPORTED, QualityError, RunnerPaths
from app.application.ragas_service import RagasService
from app.application.review_service import ReviewService
from app.application.runner_service import RunnerService
from app.domain.eval_set import eval_set_hash
from app.infrastructure.files import LocalArtifactStore

from .fakes import QUESTIONS, FakeEnvironment, FakeIndexer, FakeJudge, FakeLock, FakePointer, FakeProbe, FakeRetriever

STORE = LocalArtifactStore()


def setup(tmp_path: Path, *, plan: str = "chunk", indexer_fail: bool = False, retriever_kwargs: dict | None = None,
          probe: list[str] | None = None, lock_busy: bool = False):
    """임시 폴더에 인덱서 설정 원본 · 평가셋 · 계획 파일을 만들고 실행기를 조립함."""

    indexer_dir = tmp_path / "indexer"
    STORE.write_json(indexer_dir / "config" / "document_policies.json",
                     {"defaults": {"chunk_size": 800, "chunk_overlap": 200}, "documents": {"D1": {"x": 1}}})
    STORE.write_json(tmp_path / "eval-set.json", {"schema_version": 1, "questions": QUESTIONS})
    common = {"eval_set": {"path": "eval-set.json", "sha256": eval_set_hash(QUESTIONS)},
              "scoring": {"ragas_provider": "local", "ragas_repeat": 2, "human_pass_threshold": 0.5}}
    if plan == "chunk":
        body = {"hyperparameter": "chunk_size", "apply": "config_file",
                "target": "indexer:config:config/document_policies.json#defaults.chunk_size", "reindex": True,
                "baseline": 800, "versions": [{"id": "800", "value": 800}, {"id": "600", "value": 600}]}
    else:
        body = {"hyperparameter": "top_k", "apply": "code_arg", "target": "retriever:arg:--top-k", "reindex": False,
                "baseline": 5, "versions": [{"id": "3", "value": 3}, {"id": "5", "value": 5}]}
    plan_path = tmp_path / "plans" / "p.yaml"
    STORE.write_text(plan_path, yaml.safe_dump({"schema_version": 1, **body, **common}, allow_unicode=True))
    pointer = FakePointer("gen-base")
    indexer = FakeIndexer(pointer, fail=indexer_fail)
    retriever = FakeRetriever(pointer, **(retriever_kwargs or {}))
    lock = FakeLock(busy=lock_busy)
    runner = RunnerService(
        store=STORE, pointer=pointer, lock=lock, indexer=indexer, retriever=retriever, probe=FakeProbe(probe),
        environment=FakeEnvironment(), ragas=RagasService(STORE, lambda p: FakeJudge()), review=ReviewService(STORE),
        compare=CompareService(STORE),
        paths=RunnerPaths(ragas_root=tmp_path, experiments_root=tmp_path / "experiments", indexer_dir=indexer_dir,
                          data_root=tmp_path / "data"))
    return runner, plan_path, pointer, indexer, retriever, lock


def statuses(result: dict, version: str) -> dict:
    return result["versions"][version]


def test_reindex_plan_restores_pointer_between_versions_and_builds_compare(tmp_path: Path):
    runner, plan_path, pointer, indexer, retriever, lock = setup(tmp_path)
    result = runner.run(plan_path)
    assert statuses(result, "800") == {"F1": SUCCESS, "F2": SUCCESS, "F3": SUCCESS, "F4": SUCCESS, "F5": SUCCESS,
                                       "F6": SUCCESS}
    # 기준 버전부터 돌고, 두 번째 색인도 기준 세대에서 시작함(버전마다 되돌렸기 때문 — 게시 거부 방지)
    assert [call[0].split("-")[2] for call in indexer.calls] == ["800", "600"]
    assert indexer.base_seen == ["gen-base", "gen-base"]
    # 검색은 그 버전이 만든 세대로 돌았고, 끝난 뒤 포인터는 원래 값임
    assert [c["generation"] for c in retriever.calls] == [f"gen-{indexer.calls[0][0]}", f"gen-{indexer.calls[1][0]}"]
    assert pointer.content["generation"] == "gen-base" and result["pointer_restored"]["matches"]
    assert lock.events == ["acquire", "release"]

    copy = tmp_path / "experiments" / "chunk_size" / "600" / "document_policies.json"
    assert json.loads(copy.read_text(encoding="utf-8"))["defaults"]["chunk_size"] == 600
    assert indexer.calls[1][1]["POLICIES_PATH"] == str(copy.resolve())
    config = STORE.read_json(tmp_path / "experiments" / "chunk_size" / "600" / "config.json")
    assert config["config_copy"]["differences"] == ["defaults.chunk_size"] and config["generation"].startswith("gen-exp")
    assert config["environment"]["secrets"]["GROQ_API_KEY"] == "(설정됨)"
    assert (tmp_path / "experiments" / "chunk_size" / "compare.md").exists()
    original = STORE.read_json(tmp_path / "indexer" / "config" / "document_policies.json")
    assert original["defaults"]["chunk_size"] == 800  # 원본 설정은 그대로


def test_failed_step_still_restores_and_next_version_runs(tmp_path: Path):
    runner, plan_path, pointer, indexer, retriever, _ = setup(tmp_path, retriever_kwargs={"fail_versions": ("800",)})
    result = runner.run(plan_path)
    assert statuses(result, "800")["F3"] == FAILED and statuses(result, "800")["F4"] == SUCCESS
    assert statuses(result, "800")["F5"] == SKIPPED and statuses(result, "600")["F6"] == SUCCESS
    assert pointer.content["generation"] == "gen-base"
    state = STORE.read_json(tmp_path / "experiments" / "chunk_size" / "state.json")
    assert state["versions"]["800"]["steps"]["F3"]["code"] == "E-EXIT"


def test_indexer_failure_is_recorded_and_pointer_untouched(tmp_path: Path):
    runner, plan_path, pointer, *_ = setup(tmp_path, indexer_fail=True)
    result = runner.run(plan_path, stop_on_error=True)
    assert statuses(result, "800")["F2"] == FAILED and "600" in result["versions"]
    assert statuses(result, "600")["F1"] not in (SUCCESS,)  # --stop-on-error라 다음 버전은 돌지 않음
    assert pointer.writes == []


def test_resume_skips_success_steps_and_repoints_for_retrieval(tmp_path: Path):
    runner, plan_path, pointer, indexer, retriever, _ = setup(tmp_path, retriever_kwargs={"fail_versions": ("600",)})
    runner.run(plan_path)
    assert len(indexer.calls) == 2
    retriever.fail_versions = ()
    result = runner.run(plan_path, resume=True)
    assert len(indexer.calls) == 2  # 색인은 다시 하지 않음
    assert retriever.calls[-1]["version"] == "600"
    assert retriever.calls[-1]["generation"] == f"gen-{indexer.calls[1][0]}"  # 저장해 둔 그 버전 세대로 다시 돌려 검색함
    assert statuses(result, "600")["F6"] == SUCCESS and pointer.content["generation"] == "gen-base"


def test_resume_refuses_changed_plan(tmp_path: Path):
    runner, plan_path, *_ = setup(tmp_path)
    runner.run(plan_path)
    plan = yaml.safe_load(plan_path.read_text(encoding="utf-8"))
    plan["scoring"]["ragas_repeat"] = 1
    plan_path.write_text(yaml.safe_dump(plan, allow_unicode=True), encoding="utf-8")
    with pytest.raises(QualityError) as error:
        runner.run(plan_path, resume=True)
    assert error.value.exit_code == 2


@pytest.mark.parametrize("kwargs", [{"probe": ["http://127.0.0.1:8020"]}, {"lock_busy": True}])
def test_preflight_rejections_change_nothing(tmp_path: Path, kwargs):
    runner, plan_path, pointer, indexer, retriever, _ = setup(tmp_path, **kwargs)
    with pytest.raises(QualityError) as error:
        runner.run(plan_path)
    assert error.value.exit_code == 2
    assert indexer.calls == [] and retriever.calls == [] and pointer.writes == []


def test_eval_set_hash_mismatch_is_rejected(tmp_path: Path):
    runner, plan_path, *_ = setup(tmp_path)
    STORE.write_json(tmp_path / "eval-set.json", {"questions": QUESTIONS[:1]})
    with pytest.raises(QualityError) as error:
        runner.run(plan_path)
    assert "V6" in error.value.message


def test_interrupt_during_retrieval_restores_pointer_and_releases_lock(tmp_path: Path):
    runner, plan_path, pointer, _, _, lock = setup(tmp_path, retriever_kwargs={"interrupt_versions": ("800",)})
    with pytest.raises(KeyboardInterrupt):
        runner.run(plan_path)
    assert pointer.content["generation"] == "gen-base" and lock.events == ["acquire", "release"]


def test_top_k_plan_passes_argument_and_skips_reindex(tmp_path: Path):
    runner, plan_path, pointer, indexer, retriever, _ = setup(tmp_path, plan="top_k")
    result = runner.run(plan_path)
    assert indexer.calls == [] and statuses(result, "3")["F2"] == SKIPPED
    assert [c["version"] for c in retriever.calls] == ["5", "3"]
    args = retriever.calls[1]["args"]
    assert args[args.index("--top-k") + 1] == "3" and args[args.index("--fixed-k") + 1] == "5"
    assert pointer.writes == []


def test_unsupported_argument_marks_versions_and_skips_tools(tmp_path: Path):
    runner, plan_path, _, _, retriever, _ = setup(tmp_path, plan="top_k", retriever_kwargs={"supported": ()})
    result = runner.run(plan_path)
    assert set(statuses(result, "3").values()) == {UNSUPPORTED} and retriever.calls == []
    assert result["compare"] is None
