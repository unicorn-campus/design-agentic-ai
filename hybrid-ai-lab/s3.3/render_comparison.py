"""실제 실행 JSON 5개를 질문·Baseline·적용 기법 비교표로 변환함."""

import argparse
import json
from pathlib import Path


BASE = Path(__file__).resolve().parent
MODES = ("baseline", "rewrite", "multi", "hyde", "stepback")
LABELS = {
    "rewrite": "Rewriting",
    "multi": "Multi-Query",
    "hyde": "HyDE",
    "stepback": "Step-Back",
}


def load_results(results_dir: Path) -> dict:
    """기법별 실제 실행 결과를 읽음."""
    values = {}
    for mode in MODES:
        path = results_dir / f"{mode}_kure_actual.json"
        values[mode] = json.loads(path.read_text(encoding="utf-8"))
    return values


def rank_cell(row: dict) -> str:
    """정답 청크별 순위와 Top-3 판정을 한 셀에 표시함."""
    if not row["scorable"]:
        return "평가 제외(정답 미매핑)"
    parts = []
    for chunk_id, rank in row["ranks"].items():
        parts.append(f"{chunk_id} {rank}위" if rank is not None else f"{chunk_id} 후보 밖")
    verdict = "○" if row["top_k_included"] else "×"
    return f"{', '.join(parts)} · {verdict}"


def render(results: dict) -> str:
    """네 개의 3열 비교표와 전체 결과를 마크다운으로 만듦."""
    baseline = {row["id"]: row for row in results["baseline"]["rows"]}
    baseline_passed = results["baseline"]["passed_count"]
    lines = [
        "# 질문 변환 기법별 실제 검색 결과",
        "",
        "- 실행일: 2026-09-12",
        "- 임베딩 모델: `nlpai-lab/KURE-v1`",
        "- 인덱스: `s3.2/data/chroma/group1`, 컬렉션 `card_docs_ref`(485개 청크)",
        "- 측정: 상위 10건을 모아 중복 제거·점수순 정렬 후 정답 청크의 Top-3 포함 여부 확인",
        "- 비교 원칙: 각 기법을 Baseline에 단독 적용",
        "- q7: 현재 원문·인덱스에 정답 청크가 없어 평가 제외",
        "",
        "## 전체 결과",
        "",
        "| 방식 | Top-3 통과 | 평가 가능 질문 | Baseline 대비 |",
        "|---|---:|---:|---:|",
    ]
    for mode in MODES:
        result = results[mode]
        label = "Baseline" if mode == "baseline" else LABELS[mode]
        delta = result["passed_count"] - baseline_passed
        delta_text = "기준" if mode == "baseline" else f"{delta:+d}건"
        lines.append(
            f"| {label} | {result['passed_count']}/{result['scored_count']} | "
            f"{result['scored_count']}/{result['case_count']} | {delta_text} |"
        )

    for mode in MODES[1:]:
        label = LABELS[mode]
        lines.extend([
            "",
            f"## Baseline과 {label} 비교",
            "",
            f"| 질문 | Baseline | {label} |",
            "|---|---|---|",
        ])
        for row in results[mode]["rows"]:
            question = str(row["question"]).replace("|", "\\|")
            lines.append(
                f"| {question} | {rank_cell(baseline[row['id']])} | {rank_cell(row)} |"
            )

    lines.extend([
        "",
        "## 관찰 결과",
        "",
        "- Rewriting: q3의 `D1_0010`과 q6의 `D2_0003`이 후보 밖으로 밀려 2건 감소",
        "- Multi-Query: q3의 `D1_0010`이 24위, q6의 `D1_0010`이 5위가 되어 2건 감소",
        "- HyDE: q6의 `D1_0010`이 5위가 되어 1건 감소. 생성문에 원문과 다른 수치·조건 포함",
        "- Step-Back: q3의 `D1_0010`이 12위, q6의 `D2_0003`이 4위가 되어 2건 감소",
        "- 결론: 이 질문 세트에서는 질문 변환의 일괄 적용 근거가 없으며 질문 유형별 적용과 프롬프트 개선 필요",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="질문 변환 실제 결과 비교표 생성")
    parser.add_argument("--results-dir", type=Path, default=BASE / "results")
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE / "results/query_transform_comparison_kure.md",
    )
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(load_results(args.results_dir)), encoding="utf-8")
    print(f"비교표 저장: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
