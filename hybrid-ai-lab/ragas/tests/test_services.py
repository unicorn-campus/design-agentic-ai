"""서비스 시험 — 평가셋 변환 · RAGAS 집계 · 검토표 · 비교표(파일은 임시 폴더, LLM · 색인은 가짜)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.application.compare_service import CompareService
from app.application.eval_set_service import EvalSetService
from app.application.models import QualityError
from app.application.ragas_service import RagasService
from app.application.review_service import ReviewService
from app.domain.verification import Chunk
from app.infrastructure.files import LocalArtifactStore

from .fakes import FakeJudge, retriever_log
from .test_domain import SAMPLE_MD

STORE = LocalArtifactStore()


class FakeCorpus:
    def __init__(self, chunks):
        self._chunks = chunks

    def active_generation(self) -> str:
        return "gen-test"

    def chunks(self):
        return self._chunks


def test_build_writes_json_only_when_verification_passes(tmp_path: Path):
    md = tmp_path / "eval-set.md"
    md.write_text(SAMPLE_MD, encoding="utf-8")
    good = [Chunk("c1", "D1_약관.pdf", "직전 12개월 이용금액이 3,000,000원 이상"),
            Chunk("c2", "D3_S02.txt", "비교해 주세요"), Chunk("c3", "D3_S02.txt", "확인부터 하려는 거예요 아직 신청 안 했어요")]
    report = EvalSetService(STORE, FakeCorpus(good)).build(md, tmp_path / "ok.json")
    assert report["passed"] and report["composition"] == {"D1": 1, "D2": 0, "D3": 1, "no_answer": 1}
    assert json.loads((tmp_path / "ok.json").read_text(encoding="utf-8"))["questions"][0]["id"] == "Q01"

    report = EvalSetService(STORE, FakeCorpus(good[:1])).build(md, tmp_path / "bad.json")
    assert not report["passed"] and report["saved_to"] is None and not (tmp_path / "bad.json").exists()


def test_ragas_scores_only_eligible_rows_and_records_failed_metric(tmp_path: Path):
    judge = FakeJudge({"faithfulness": 0.5}, fail_metric="context_recall")
    log = tmp_path / "retriever.json"
    STORE.write_json(log, retriever_log("5", 0.8))
    report = RagasService(STORE, lambda provider: judge).score_file(log, tmp_path / "ragas.json", provider="local",
                                                                    repeat=3)
    assert report["scored"] == 1 and report["excluded"] == [{"id": "Q02", "reason": "no_answer_question"}]
    assert len(judge.calls) == 4 * 3  # 채점 행 1 × 지표 4 × 반복 3
    assert ("answer_relevancy", ("response", "user_input")) in judge.calls  # 지표가 읽는 칸만 넘김
    assert report["summary"]["faithfulness"]["mean"] == 0.5
    assert report["summary"]["faithfulness"]["repeat_means"] == [0.5, 0.5, 0.5]
    assert set(report["summary"]) == {"context_precision", "context_recall", "faithfulness", "answer_relevancy"}
    assert report["summary"]["context_recall"]["n"] == 0 and len(report["failed_scores"]) == 3


def test_review_export_one_row_per_question_and_protects_human_judgements(tmp_path: Path):
    STORE.write_json(tmp_path / "r.json", retriever_log("5", 0.8))
    RagasService(STORE, lambda p: FakeJudge()).score_file(tmp_path / "r.json", tmp_path / "g.json", provider="local",
                                                          repeat=1)
    service = ReviewService(STORE)
    out = tmp_path / "review.csv"
    assert service.export(tmp_path / "r.json", tmp_path / "g.json", out) == 2
    rows = STORE.read_csv(out)
    assert rows[0]["ragas_faithfulness"] == "0.8" and rows[1]["ragas_faithfulness"] == ""
    assert out.read_bytes().startswith(b"\xef\xbb\xbf")  # 엑셀용 BOM

    rows[0]["human_pass"] = "pass"
    STORE.write_csv(out, list(rows[0]), rows)
    with pytest.raises(QualityError):
        service.export(tmp_path / "r.json", tmp_path / "g.json", out)


def test_review_agree_counts_only_judged_rows_and_marks_reference_value(tmp_path: Path):
    path = tmp_path / "review.csv"
    rows = [{"id": "Q01", "ragas_faithfulness": "0.9", "code_hit": "1", "human_pass": "pass"},
            {"id": "Q02", "ragas_faithfulness": "0.2", "code_hit": "0", "human_pass": "FAIL"},
            {"id": "Q03", "ragas_faithfulness": "0.9", "code_hit": "1", "human_pass": "모름"},
            {"id": "Q04", "ragas_faithfulness": "", "code_hit": "", "human_pass": ""}]
    STORE.write_csv(path, ["id", "ragas_faithfulness", "code_hit", "human_pass"], rows)
    report = ReviewService(STORE).agree([path], threshold=0.5)
    faith = next(m for m in report["metrics"] if m["metric"] == "ragas_faithfulness")
    assert report["judged"] == 2 and faith["agreement"] == 1.0 and faith["confidence"] == "참고값"
    assert report["input_problems"] == [{"file": str(path), "id": "Q03", "value": "모름"}]


def _version(dir_: Path, version: str, recall: float, faith_means: list[float], eval_hash: str = "h1"):
    STORE.write_json(dir_ / version / "config.json", {"value": int(version), "reindex": False, "generation": "g",
                                                       "eval_set_hash": eval_hash})
    STORE.write_json(dir_ / version / "retriever.json", retriever_log(version, recall))
    summary = {m: {"mean": 0.7, "std": 0.0, "min": 0.7, "max": 0.7, "n": 1, "repeat_means": [0.7]}
               for m in ("context_precision", "context_recall", "answer_relevancy")}
    summary["faithfulness"] = {"mean": sum(faith_means) / len(faith_means), "std": None, "min": min(faith_means),
                               "max": max(faith_means), "n": 1, "repeat_means": faith_means}
    STORE.write_json(dir_ / version / "ragas.json", {"provider": "local", "repeat": 3, "summary": summary,
                                                     "scored": 1})


def test_compare_uses_baseline_band_and_fixed_k(tmp_path: Path):
    _version(tmp_path, "5", 0.8, [0.78, 0.81, 0.79])
    _version(tmp_path, "3", 0.7, [0.80, 0.80, 0.80])
    _version(tmp_path, "10", 0.9, [0.95, 0.95, 0.95])
    result = CompareService(STORE).build(tmp_path, hyperparameter="top_k", baseline_id="5", order=["5", "3", "10"])
    rows = {r["version"]: r for r in result["rows"]}
    assert rows["5"]["d_search_recall@5"] is None and rows["3"]["d_search_recall@5"] == -0.1
    assert "3 faithfulness" in result["verdicts"]["차이 없음"]  # |0.007| ≤ 흔들림 폭 0.03
    assert "10 faithfulness" in result["verdicts"]["개선"]
    markdown = (tmp_path / "compare.md").read_text(encoding="utf-8")
    assert "## ① 검색이 근거를 찾았나" in markdown and "5 ★기준" in markdown


def test_compare_warns_when_ragas_scored_rows_differ(tmp_path: Path):
    """채점 행이 기준과 3개 이상 다르면 경고와 ⚠ — 서로 다른 문항 묶음의 평균을 비교하는 중임."""

    _version(tmp_path, "800", 0.8, [0.8])
    _version(tmp_path, "600", 0.8, [0.7])
    report = STORE.read_json(tmp_path / "800" / "ragas.json")
    STORE.write_json(tmp_path / "800" / "ragas.json", {**report, "scored": 11})
    report = STORE.read_json(tmp_path / "600" / "ragas.json")
    STORE.write_json(tmp_path / "600" / "ragas.json", {**report, "scored": 8})
    result = CompareService(STORE).build(tmp_path, hyperparameter="chunk_size", baseline_id="800", order=["800", "600"])
    assert any("채점 행이 기준과 3개" in w for w in result["warnings"])
    assert "600 faithfulness ⚠" in result["verdicts"]["악화"]
    assert "| 8 ⚠ |" in (tmp_path / "compare.md").read_text(encoding="utf-8")


def test_compare_refuses_delta_when_eval_set_differs(tmp_path: Path):
    _version(tmp_path, "5", 0.8, [0.8])
    _version(tmp_path, "3", 0.7, [0.8], eval_hash="other")
    result = CompareService(STORE).build(tmp_path, hyperparameter="top_k", baseline_id="5", order=["5", "3"])
    assert result["warnings"] and result["rows"][1]["d_search_recall@5"] is None
