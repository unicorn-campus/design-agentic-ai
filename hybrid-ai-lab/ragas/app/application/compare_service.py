"""버전 비교표 — 하이퍼 파라미터 폴더의 버전들을 모아 기준 대비 차이와 판정을 compare.md · .csv로 씀."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from app.domain.comparison import delta, direction_match, judge_code, judge_ragas
from app.domain.scoring import METRICS

from .ports import ArtifactStorePort

CODE_METRICS = ("recall", "ndcg", "hit", "mrr", "precision")
SCORED_GAP_WARN = 3  # RAGAS 채점 행 수가 기준과 이만큼 이상 다르면 Δ 옆에 ⚠(설계 가정 — 숫자 3에 측정 근거 없음)


def _scored_gap(row: dict[str, Any], base: dict[str, Any] | None) -> int | None:
    """RAGAS 채점 행 수가 기준과 몇 개 다른지. 어느 한쪽에 RAGAS 결과가 없으면 None.

    채점 행은 '근거를 들고 끝난 답 있음 문항'이라 버전마다 달라짐 — 차이가 크면 평균끼리의 Δ가 문항 구성 차이를 섞음.
    """

    if base is None or row["ragas_scored"] is None or base["ragas_scored"] is None:
        return None
    return abs(row["ragas_scored"] - base["ragas_scored"])
FINAL_COUNTS = ("answerable_returned", "answerable_returned_with_relevant", "no_answer_refused")


def _fmt(value: Any, digits: int = 3) -> str:
    """표 칸 글자 — 없으면 '—', 실수는 소수 셋째 자리, Δ는 부호를 붙임."""

    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _signed(value: float | None) -> str:
    """Δ 칸 글자 — +0.012 · -0.030 꼴."""

    return "—" if value is None else f"{value:+.3f}"


class CompareService:
    """비교표 서비스. 버전 폴더(config · retriever · ragas · review-agree)를 읽기만 하고 실험은 돌리지 않음."""

    def __init__(self, store: ArtifactStorePort):
        self.store = store

    def _load(self, version_dir: Path) -> dict[str, Any] | None:
        """버전 폴더 하나의 비교 재료를 모음. 검색 결과가 없으면(실패 · 미지원) None."""

        retriever = version_dir / "retriever.json"
        if not self.store.exists(retriever):
            return None
        config = self.store.read_json(version_dir / "config.json") if self.store.exists(version_dir / "config.json") else {}
        log = self.store.read_json(retriever)
        summary = log["summary"]["all"]
        ragas_path = version_dir / "ragas.json"
        ragas = self.store.read_json(ragas_path) if self.store.exists(ragas_path) else None
        agree_path = version_dir / "review-agree.json"
        agree = self.store.read_json(agree_path) if self.store.exists(agree_path) else None
        return {
            "version": version_dir.name,
            "value": config.get("value"),
            "reindex": config.get("reindex"),
            "generation": config.get("generation"),
            "eval_set_hash": config.get("eval_set_hash"),
            "judge": None if ragas is None else f"{ragas.get('provider')} · repeat {ragas.get('repeat')}",
            "n": summary.get("answerable"),
            # Top-k 버전끼리 같은 잣대가 되도록 Δ는 고정 k(@5) 값으로 계산함. 옛 로그는 search_top5로 대신함
            "search_fixed": summary.get("search_fixed") or summary.get("search_top5") or {},
            "search_at_k": summary.get("search_top5") or {},
            "metric_k": log.get("metric_k", 5),
            "final": summary.get("final_evidence") or {},
            "counts": {key: summary.get(key) for key in FINAL_COUNTS},
            "seconds_median": summary.get("seconds_median"),
            "llm_calls_mean": summary.get("llm_calls_mean"),
            "ragas": None if ragas is None else ragas["summary"],
            "ragas_scored": None if ragas is None else ragas.get("scored"),
            "kappa": None if agree is None else {m["metric"]: m["kappa"] for m in agree["metrics"]},
        }

    def build(self, param_dir: Path, *, hyperparameter: str, baseline_id: str, order: list[str]) -> dict[str, Any]:
        """버전 폴더들을 모아 compare.csv · compare.md를 씀.

        방법: 기준 버전 대비 Δ를 내고, 코드 지표는 부호로, RAGAS는 기준 버전 반복 흔들림 폭과 비교해 판정함.
              평가셋 지문이나 평가자가 버전끼리 다르면 Δ를 계산하지 않고 경고만 적음(같은 조건 원칙).
        반환값: 비교 행 목록 · 경고 · 판정 요약.
        부수효과: param_dir/compare.csv · compare.md 생성.
        """

        rows = [r for r in (self._load(param_dir / vid) for vid in order) if r is not None]
        base = next((r for r in rows if r["version"] == baseline_id), None)
        warnings = []
        if base is None:
            warnings.append("기준 버전 결과가 없어 Δ를 계산하지 않음")
        else:
            for row in rows:
                if row["eval_set_hash"] != base["eval_set_hash"]:
                    warnings.append(f"{row['version']}: 평가셋 지문이 기준과 달라 Δ를 계산하지 않음")
                if row["judge"] != base["judge"]:
                    warnings.append(f"{row['version']}: 평가자 · 반복 수가 기준과 달라 RAGAS Δ를 계산하지 않음")
                gap = _scored_gap(row, base)
                if gap is not None and gap >= SCORED_GAP_WARN:
                    warnings.append(f"{row['version']}: RAGAS 채점 행이 기준과 {gap}개 달라 서로 다른 문항 묶음의 평균을 "
                                    "비교하는 중 — RAGAS Δ는 참고만 함(⚠)")
        comparable = {r["version"]: base is not None and r["eval_set_hash"] == base["eval_set_hash"] for r in rows}
        same_judge = {r["version"]: base is not None and r["judge"] == base["judge"] for r in rows}
        bands = {}
        if base and base["ragas"]:
            for metric in METRICS:
                item = base["ragas"].get(metric) or {}
                bands[metric] = None if item.get("max") is None else round(item["max"] - item["min"], 4)

        verdicts: dict[str, list[str]] = {"개선": [], "악화": [], "차이 없음": [], "원인 확인": []}
        csv_rows = []
        for row in rows:
            ok = comparable[row["version"]] and row is not base
            record: dict[str, Any] = {"version": row["version"], "param": hyperparameter, "param_value": row["value"],
                                      "reindex": row["reindex"], "generation": row["generation"],
                                      "eval_set_hash": row["eval_set_hash"], "judge": row["judge"], "n": row["n"]}
            for metric in CODE_METRICS:
                value = row["search_fixed"].get(metric)
                diff = delta(value, base["search_fixed"].get(metric)) if ok else None
                record[f"search_{metric}@5"] = value
                record[f"d_search_{metric}@5"] = diff
                if ok and metric in {"recall", "ndcg"}:
                    verdicts.setdefault(judge_code(diff), []).append(f"{row['version']} search_{metric}@5")
            record["search_recall@k"] = row["search_at_k"].get("recall")
            record["metric_k"] = row["metric_k"]
            for key in FINAL_COUNTS:
                record[key] = row["counts"].get(key)
            for metric in ("recall", "ndcg"):
                record[f"final_{metric}"] = row["final"].get(metric)
            for metric in METRICS:
                item = (row["ragas"] or {}).get(metric) or {}
                value = item.get("mean")
                diff = delta(value, ((base or {}).get("ragas") or {}).get(metric, {}).get("mean")) \
                    if ok and same_judge[row["version"]] and base and base["ragas"] else None
                record[metric] = value
                record[f"d_{metric}"] = diff
                record[f"sd_repeat_{metric}"] = item.get("std")
                if diff is not None:
                    gap = _scored_gap(row, base)
                    mark = " ⚠" if gap is not None and gap >= SCORED_GAP_WARN else ""
                    verdicts.setdefault(judge_ragas(diff, bands.get(metric)), []).append(f"{row['version']} {metric}{mark}")
            record["ragas_scored"] = row["ragas_scored"]
            gap = _scored_gap(row, base)
            record["ragas_scored_warning"] = "⚠" if gap is not None and gap >= SCORED_GAP_WARN else ""
            match = direction_match(record.get("d_search_recall@5"), record.get("d_context_recall"))
            record["agree_direction"] = match
            if match.startswith("반대"):
                verdicts["원인 확인"].append(f"{row['version']} 코드 Recall ↔ RAGAS ContextRecall")
            record["kappa_faithfulness"] = (row["kappa"] or {}).get("ragas_faithfulness")
            record["seconds_median"] = row["seconds_median"]
            record["llm_calls_mean"] = row["llm_calls_mean"]
            csv_rows.append(record)

        header = list(csv_rows[0]) if csv_rows else ["version"]
        self.store.write_csv(param_dir / "compare.csv", header, csv_rows)
        self.store.write_text(param_dir / "compare.md",
                              _markdown(hyperparameter, baseline_id, base, csv_rows, bands, warnings, verdicts))
        return {"rows": csv_rows, "warnings": warnings, "verdicts": verdicts}


def _markdown(hyperparameter: str, baseline_id: str, base: dict[str, Any] | None, rows: list[dict[str, Any]],
              bands: dict[str, float | None], warnings: list[str], verdicts: dict[str, list[str]]) -> str:
    """분석 순서(① 검색 → ② 어디서 막혔나 → ③ 채점끼리 → 판정)대로 표를 만듦."""

    judge = "—" if base is None else (base["judge"] or "RAGAS 없음")
    lines = [f"# 비교표 — {hyperparameter}",
             "",
             f"- 기준 버전: {baseline_id} · 평가셋 지문: {_fmt(None if base is None else base['eval_set_hash'])} · 평가자: {judge}",
             "- Δ = 그 버전 − 기준 버전. 코드 지표는 버전끼리 같은 잣대가 되도록 @5로 계산함(@k는 참고 열)",
             "- RAGAS 판정은 |Δ|가 기준 버전 반복 흔들림 폭보다 클 때만 개선 · 악화로 봄. 고정 합격선은 쓰지 않음",
             "- 흔들림 폭은 평가자 반복만 반영함 — 리트리버 답변 생성(LLM)의 실행 간 흔들림은 들어 있지 않아 작은 Δ는 "
             "같은 설정을 다시 돌려 확인함",
             ""]
    if warnings:
        lines += ["> 경고: " + " / ".join(warnings), ""]
    lines += ["## ① 검색이 근거를 찾았나", "",
              "| 버전 | 값 | Recall@5 | Δ | nDCG@5 | Δ | Hit@5 | Δ | MRR@5 | Precision@5 | Recall@k(참고) | n |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        star = " ★기준" if r["version"] == baseline_id else ""
        lines.append(f"| {r['version']}{star} | {_fmt(r['param_value'])} | {_fmt(r['search_recall@5'])} | "
                     f"{_signed(r['d_search_recall@5'])} | {_fmt(r['search_ndcg@5'])} | {_signed(r['d_search_ndcg@5'])} | "
                     f"{_fmt(r['search_hit@5'])} | {_signed(r['d_search_hit@5'])} | {_fmt(r['search_mrr@5'])} | "
                     f"{_fmt(r['search_precision@5'])} | {_fmt(r['search_recall@k'])} (@{r['metric_k']}) | {_fmt(r['n'])} |")
    lines += ["", "## ② 어디서 막혔나 — 최종 응답 · RAGAS", "",
              "| 버전 | 근거 들고 끝남 | 그중 정답 근거 | 확인 필요 정답 | ContextRecall | Δ | ContextPrecision | Δ | "
              "Faithfulness | Δ | AnswerRelevancy | Δ | RAGAS 채점 행 |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['version']} | {_fmt(r['answerable_returned'])} | {_fmt(r['answerable_returned_with_relevant'])} | "
                     f"{_fmt(r['no_answer_refused'])} | {_fmt(r['context_recall'])} | {_signed(r['d_context_recall'])} | "
                     f"{_fmt(r['context_precision'])} | {_signed(r['d_context_precision'])} | {_fmt(r['faithfulness'])} | "
                     f"{_signed(r['d_faithfulness'])} | {_fmt(r['answer_relevancy'])} | {_signed(r['d_answer_relevancy'])} | "
                     f"{_fmt(r['ragas_scored'])}{' ' + r['ragas_scored_warning'] if r['ragas_scored_warning'] else ''} |")
    band_text = " · ".join(f"{m} {_fmt(b)}" for m, b in bands.items()) or "—"
    lines += ["", f"흔들림 폭(기준 버전 반복 평균의 최대 − 최소): {band_text}", "",
              "## ③ 채점끼리 맞나", "",
              "| 버전 | 코드 Recall@5 Δ | RAGAS ContextRecall Δ | 방향 | kappa(Faithfulness, 사람) |",
              "|---|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r['version']} | {_signed(r['d_search_recall@5'])} | {_signed(r['d_context_recall'])} | "
                     f"{r['agree_direction']} | {_fmt(r['kappa_faithfulness'])} (참고값) |")
    lines += ["", "## 판정", ""]
    for name, items in verdicts.items():
        lines.append(f"- {name}: {', '.join(items) if items else '없음'}")
    lines += ["- 다음 하이퍼 파라미터: 가장 큰 병목 하나만 골라 사람이 정함", ""]
    return "\n".join(lines)
