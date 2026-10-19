"""세 실행(기준1, 기준2, A)의 결과를 모아 비교표 `compare.md`를 만듦.

판정 규칙(위임 프롬프트 [처리] 3)
- 흔들림 = max(|기준2 − 기준1|, 평가자 반복 흔들림 중 가장 큰 값)
- |A − 기준1|이 흔들림보다 클 때만 '개선' 또는 '악화'로 적고, 그렇지 않으면 '차이 없음'으로 적음
- 흔들림이 0인데 차이가 있으면 '차이 있음(흔들림 0)'으로 적어 더 확인하게 함 —
  평가자가 로컬이면 반복 3회가 같은 값이라 흔들림이 0으로 나오는 일이 잦기 때문임

실행:
    ragas/.venv/Scripts/python verify/neo4j-bm25-compare/ragas-ab/compare.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "runs"
OUT_MD = ROOT / "compare.md"
OUT_JSON = ROOT / "compare.json"

LABELS = ("base1", "base2", "A")
TITLES = {"base1": "기준1", "base2": "기준2", "A": "A 방식"}
SEARCH_METRICS = (("recall", "Recall@5"), ("ndcg", "nDCG@5"), ("hit", "Hit@5"), ("mrr", "MRR@5"))
RAGAS_METRICS = (("context_precision", "ContextPrecision"), ("context_recall", "ContextRecall"),
                 ("faithfulness", "Faithfulness"), ("answer_relevancy", "AnswerRelevancy"))


def load(label: str) -> dict[str, Any]:
    """실행 한 벌의 검색 결과와 RAGAS 결과를 읽음(RAGAS가 아직 없으면 None으로 둠)."""

    folder = RUNS / label
    retriever = json.loads((folder / "retriever.json").read_text(encoding="utf-8"))
    ragas_path = folder / "ragas.json"
    ragas = json.loads(ragas_path.read_text(encoding="utf-8")) if ragas_path.exists() else None
    return {"label": label, "retriever": retriever, "ragas": ragas}


def verdict(base1: float | None, base2: float | None, a: float | None, judge_noise: float) -> tuple[str, str]:
    """차이와 흔들림을 견줘 판정 문구를 만듦. 반환값은 (흔들림 표기, 판정 문구)임."""

    if base1 is None or a is None:
        return ("-", "잴 수 없음")
    run_noise = abs(base2 - base1) if base2 is not None else 0.0
    noise = max(run_noise, judge_noise)
    diff = a - base1
    if abs(diff) <= noise:
        return (f"{noise:.3f}", "차이 없음")
    if noise == 0.0:
        return ("0.000", f"차이 있음({diff:+.3f}, 흔들림 0 — 확인 필요)")
    return (f"{noise:.3f}", f"{'개선' if diff > 0 else '악화'}({diff:+.3f})")


def search_block(runs: dict[str, dict[str, Any]]) -> list[str]:
    """검색 지표(코드 채점 @5) 비교표 줄을 만듦."""

    lines = ["| 지표 | 기준1 | 기준2 | A | 흔들림 | 판정 |", "|---|---:|---:|---:|---:|---|"]
    for key, title in SEARCH_METRICS:
        values = {label: runs[label]["retriever"]["summary"]["all"]["search_top5"].get(key) for label in LABELS}
        noise_text, text = verdict(values["base1"], values["base2"], values["A"], 0.0)
        cells = " | ".join("-" if values[label] is None else f"{values[label]:.3f}" for label in LABELS)
        lines.append(f"| {title} | {cells} | {noise_text} | {text} |")
    return lines


def ragas_block(runs: dict[str, dict[str, Any]]) -> list[str]:
    """RAGAS 4지표 비교표 줄을 만듦. 세 실행 중 하나라도 채점 결과가 없으면 안내만 적음."""

    if any(runs[label]["ragas"] is None for label in LABELS):
        missing = ", ".join(TITLES[label] for label in LABELS if runs[label]["ragas"] is None)
        return [f"**채점하지 못함** — RAGAS 결과가 없는 실행: {missing}.",
                "평가자가 로컬 Ollama인데 Ollama가 떠 있지 않아 채점을 돌리지 못함(README 「이어서 하는 법」 참고).",
                "숫자를 지어내지 않으려고 이 칸은 비워 둠."]
    lines = ["| 지표 | 기준1 | 기준2 | A | 흔들림 | 판정 |", "|---|---:|---:|---:|---:|---|"]
    for key, title in RAGAS_METRICS:
        values, stds = {}, []
        for label in LABELS:
            block = runs[label]["ragas"]["summary"].get(key) or {}
            values[label] = block.get("mean")
            stds.append(float(block.get("std") or 0.0))
        noise_text, text = verdict(values["base1"], values["base2"], values["A"], max(stds))
        cells = " | ".join("-" if values[label] is None else f"{values[label]:.3f}" for label in LABELS)
        lines.append(f"| {title} | {cells} | {noise_text} | {text} |")
    scored = " / ".join(str(runs[label]["ragas"].get("scored")) for label in LABELS)
    lines.append("")
    lines.append(f"채점 행 수(기준1 / 기준2 / A): {scored} — 3행 이상 차이면 Δ는 참고만 함")
    return lines


def ragas_common_block(runs: dict[str, dict[str, Any]]) -> list[str]:
    """세 실행이 모두 채점한 문항만 모아 평균을 다시 냄.

    왜 필요한가: 실행마다 답변 생성이 시간을 넘겨 채점 대상 문항이 달라짐. 문항 묶음이 다르면
    평균 차이가 BM25 탓인지 문항이 바뀐 탓인지 가릴 수 없어, 공통 문항으로 한 번 더 봄.
    """

    if any(runs[label]["ragas"] is None for label in LABELS):
        return []
    per_run = {label: {row["id"]: {key: block["mean"] for key, block in row["metrics"].items()}
                       for row in runs[label]["ragas"]["rows"]} for label in LABELS}
    common = sorted(set(per_run["base1"]) & set(per_run["base2"]) & set(per_run["A"]))
    if not common:
        return ["세 실행이 함께 채점한 문항이 없어 공통 비교를 하지 못함."]
    lines = [f"세 실행이 모두 채점한 {len(common)}문항({', '.join(common)})만으로 다시 낸 평균임.", "",
             "| 지표 | 기준1 | 기준2 | A | 흔들림 | 판정 |", "|---|---:|---:|---:|---:|---|"]
    for key, title in RAGAS_METRICS:
        values = {label: sum(per_run[label][q][key] for q in common) / len(common) for label in LABELS}
        noise_text, text = verdict(values["base1"], values["base2"], values["A"], 0.0)
        cells = " | ".join(f"{values[label]:.3f}" for label in LABELS)
        lines.append(f"| {title} | {cells} | {noise_text} | {text} |")
    return lines


def judge_only_rows(runs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """근거 묶음은 세 실행이 똑같은데 RAGAS 점수만 달라진 문항을 찾음.

    이런 문항의 점수 차이는 검색(BM25)이 아니라 답변 문장이 달라진 탓임 — BM25 판정에서 빼야 함.
    """

    evidence = {label: {row["id"]: [item["source"] + "|" + item["text"][:60] for item in row["evidence"]]
                        for row in runs[label]["retriever"]["rows"]} for label in LABELS}
    answers = {label: {row["id"]: row["answer"] for row in runs[label]["retriever"]["rows"]} for label in LABELS}
    per_run = {label: {row["id"]: {key: block["mean"] for key, block in row["metrics"].items()}
                       for row in runs[label]["ragas"]["rows"]} for label in LABELS}
    common = sorted(set(per_run["base1"]) & set(per_run["base2"]) & set(per_run["A"]))
    found = []
    for question_id in common:
        same_evidence = evidence["base1"][question_id] == evidence["A"][question_id] == evidence["base2"][question_id]
        if not same_evidence:
            continue
        scores = {key: [round(per_run[label][question_id][key], 3) for label in LABELS] for key, _ in RAGAS_METRICS}
        if all(len(set(values)) == 1 for values in scores.values()):
            continue
        found.append({
            "id": question_id,
            "same_evidence": True,
            "scores": scores,
            "answers": {label: answers[label][question_id] for label in LABELS},
        })
    return found


def status_block(runs: dict[str, dict[str, Any]]) -> list[str]:
    """답 있음 문항이 근거를 들고 끝났는지, 답 없음 문항을 거절했는지 비교함."""

    lines = ["| 항목 | 기준1 | 기준2 | A |", "|---|---:|---:|---:|"]
    rows = (("답 있음 17문항 중 근거를 들고 끝남", "answerable_returned"),
            ("그중 정답 조각을 담음", "answerable_returned_with_relevant"),
            ("답 없음 5문항 중 확인 필요로 끝남", "no_answer_refused"))
    for title, key in rows:
        cells = " | ".join(str(runs[label]["retriever"]["summary"]["all"][key]) for label in LABELS)
        lines.append(f"| {title} | {cells} |")
    return lines


def diff_rows(runs: dict[str, dict[str, Any]], other: str = "A") -> list[dict[str, Any]]:
    """기준1과 다른 실행에서 결과가 달라진 문항을 모음(상태, 근거 묶음, 검색 적중 기준).

    인자: other는 견줄 실행 이름임. 'A'면 BM25 차이, 'base2'면 같은 설정 두 번 돌린 실행 간 흔들림을 봄.
    """

    by_label = {label: {row["id"]: row for row in runs[label]["retriever"]["rows"]} for label in LABELS}
    found = []
    for question_id, base_row in by_label["base1"].items():
        a_row = by_label[other].get(question_id)
        if a_row is None:
            continue
        base_evidence = [item["source"] + "|" + item["text"][:40] for item in base_row["evidence"]]
        a_evidence = [item["source"] + "|" + item["text"][:40] for item in a_row["evidence"]]
        changed = (base_row["status"] != a_row["status"] or base_evidence != a_evidence
                   or base_row["search"]["hit"] != a_row["search"]["hit"])
        if not changed:
            continue
        found.append({
            "id": question_id,
            "other": other,
            "question": base_row["question"],
            "status": {"base1": base_row["status"], other: a_row["status"]},
            "search_hit": {"base1": base_row["search"]["hit"], other: a_row["search"]["hit"]},
            "evidence_count": {"base1": base_row["evidence_count"], other: a_row["evidence_count"]},
            # 차이가 LLM 시간 초과 때문인지 가리려고 경고를 함께 남김(시간 초과면 BM25 탓이 아님)
            "warnings": {"base1": base_row["warnings"], other: a_row["warnings"]},
            "base1_evidence": base_evidence,
            f"{other}_evidence": a_evidence,
            "base1_answer": base_row["answer"],
            f"{other}_answer": a_row["answer"],
        })
    return found


def diff_table(rows: list[dict[str, Any]], other: str) -> list[str]:
    """달라진 문항 목록을 표로 만듦. 비고 칸에는 LLM 시간 초과 여부를 적음."""

    if not rows:
        return ["달라진 문항 없음."]
    lines = [f"| 문항 | 상태(기준1 → {TITLES[other]}) | 검색 적중 | 근거 수 | 비고 |", "|---|---|---|---|---|"]
    for row in rows:
        timeouts = [warning for side in ("base1", other) for warning in row["warnings"][side] if "timeout" in warning]
        if timeouts:
            note = timeouts[0].split(" →")[0] + " — LLM 탓"
        elif other == "base2":
            # 기준1과 기준2는 BM25가 같음. 그런데도 달라졌다면 LLM이 만든 검색 질의가 달라진 것임
            note = "BM25는 같음 — 질의 변환(LLM) 탓"
        else:
            note = "BM25 차이로 보임"
        lines.append(f"| {row['id']} | {row['status']['base1']} → {row['status'][other]} | "
                     f"{row['search_hit']['base1']} → {row['search_hit'][other]} | "
                     f"{row['evidence_count']['base1']} → {row['evidence_count'][other]} | {note} |")
    return lines


def main() -> int:
    """비교표를 만들어 저장함. 반환값은 종료 코드(정상 0)."""

    runs = {label: load(label) for label in LABELS}
    generations = {runs[label]["retriever"].get("version"): label for label in LABELS}
    changed = diff_rows(runs, "A")
    noise_rows = diff_rows(runs, "base2")
    judge_rows = judge_only_rows(runs) if all(runs[label]["ragas"] for label in LABELS) else []

    lines = ["# A 방식(Neo4j 전문 검색) 대 기존 BM25 — 최종 답변 품질 비교", "",
             "세 실행은 평가셋, top_k, 답변 생성 설정, 평가자를 모두 같게 두고 BM25만 바꿔 돌린 결과임.", "",
             "## 1. 검색 지표(코드 채점 @5)", ""]
    lines += search_block(runs)
    lines += ["", "## 2. RAGAS 4지표", ""]
    lines += ragas_block(runs)
    lines += ["", "## 3. RAGAS 4지표 — 세 실행이 모두 채점한 문항만", ""]
    lines += ragas_common_block(runs)
    lines += ["", "## 4. 근거는 같은데 점수만 달라진 문항", "",
              "아래 문항은 세 실행이 **똑같은 근거 조각**을 썼음. 그런데도 점수가 달라졌다면 원인은 BM25가 아니라",
              "답변 문장이 실행마다 달라진 것임. BM25 판정에서는 빼고 봐야 함.", ""]
    if not judge_rows:
        lines.append("해당 문항 없음.")
    else:
        lines.append("| 문항 | ContextPrecision | Faithfulness | AnswerRelevancy |")
        lines.append("|---|---|---|---|")
        for row in judge_rows:
            def cell(key: str) -> str:
                """기준1, 기준2, A 순서로 점수를 적음."""
                return " → ".join(f"{value:.2f}" for value in row["scores"][key])

            lines.append(f"| {row['id']} | {cell('context_precision')} | {cell('faithfulness')} | "
                         f"{cell('answer_relevancy')} |")
        lines.append("")
        lines.append("점수는 기준1 → 기준2 → A 순서임. 답변 문장은 `compare.json`의 `judge_only`에 담음.")
    lines += ["", "## 5. 끝맺음", ""]
    lines += status_block(runs)
    lines += ["", "## 6. 같은 설정 두 번(기준1 대 기준2) — 실행 간 흔들림", "",
              "BM25를 바꾸지 않고 같은 설정으로 두 번 돌렸는데도 달라진 문항임. 이만큼은 A와 견줄 때 흔들림으로 봐야 함.", ""]
    lines += diff_table(noise_rows, "base2")
    lines += ["", "## 7. 기준1과 A에서 달라진 문항", ""]
    lines += diff_table(changed, "A")
    lines += ["", "문항별 근거 조각과 답변 요지는 `compare.json`에 담음(`changed`와 `run_noise`).",
              "", "## 8. 실행 정보", "",
              f"- 실행 이름(버전 칸): {', '.join(str(key) for key in generations)}",
              f"- 평가셋: {runs['base1']['retriever']['questions_file']}",
              f"- top_k: {runs['base1']['retriever']['top_k']}", ""]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    OUT_JSON.write_text(json.dumps({"changed": changed, "run_noise": noise_rows, "judge_only": judge_rows},
                                   ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(lines))
    print(f"저장: {OUT_MD}와 {OUT_JSON}")
    return 0


if __name__ == "__main__":
    import sys

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
