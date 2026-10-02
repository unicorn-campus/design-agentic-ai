"""실측 검색 결과를 검토하기 쉬운 한국어 보고서로 바꿈."""

from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    """실측 JSON을 읽어 검색 품질 비교 보고서를 생성함.

    반환값: 없음.
    예외: 필수 실측 파일이나 기대 필드가 없으면 파일·키 관련 예외가 발생함.
    부수효과: results 아래 검색 품질 비교 Markdown 보고서를 덮어씀.
    """
    result = json.loads((HERE / "results" / "comparison.json").read_text(encoding="utf-8"))
    fixture = json.loads((HERE / "group2_questions.json").read_text(encoding="utf-8"))
    questions = fixture["questions"]
    info = result["index_info"]
    summaries = result["summary"]
    lookup = {(row["id"], row["index"], row["mode"]): row for row in result["results"]}
    def direction(old: float, new: float) -> str:
        """기존 값과 신규 값의 증감 관계를 보고서 문구로 반환함."""
        return "높아졌습니다" if new > old else "낮아졌습니다" if new < old else "같습니다"
    rank_changes = [f"{mode}의 MRR@5는 기존 {summaries['old_' + mode]['mrr_at_5']:.3f}에서 "
                    f"신규 {summaries['new_' + mode]['mrr_at_5']:.3f}로 "
                    f"{direction(summaries['old_' + mode]['mrr_at_5'], summaries['new_' + mode]['mrr_at_5'])}"
                    for mode in ("vector", "hybrid")]
    declines = [q["id"] for q in questions if q["answerable"] and
                lookup[q["id"], "new", "hybrid"]["metrics"]["mrr_at_5"] <
                lookup[q["id"], "old", "hybrid"]["metrics"]["mrr_at_5"]]
    misses = [q["id"] for q in questions if q["answerable"] and all(
        not lookup[q["id"], label, mode]["metrics"]["hit_at_5"]
        for label in ("old", "new") for mode in ("vector", "hybrid"))]
    audit = json.loads((HERE / "results" / "index-audit.json").read_text(encoding="utf-8"))
    initial = json.loads((HERE / "results" / "build-result.json").read_text(encoding="utf-8"))
    final = json.loads((HERE / "results" / "final-build-result.json").read_text(encoding="utf-8"))
    noop = json.loads((HERE / "results" / "noop-result.json").read_text(encoding="utf-8"))
    positives = sum(q["answerable"] for q in questions)
    lines = [
        "# 기존·신규 인덱서의 검색 품질 비교",
        "",
        "같은 원문에서 만든 두 인덱스를 기존 `retriever/vector-retriever`의 검색 유스케이스로 비교했습니다.",
        "질문은 지정된 수업 자료의 2조 20문항을 그대로 사용했습니다.",
        "카드·고객이 불명확한 질문은 사용자와 합의한 대상을 적용했습니다.",
        "",
        "## 이번 결과의 판단",
        "",
        *rank_changes,
        "검색 방식마다 변화를 따로 확인해야 하며, 청크 수가 줄었다고 검색 순위도 좋아진다고 볼 수는 없습니다.",
        "문서 유형마다 별도 청킹 코드를 유지하던 부담과 불필요한 재임베딩을 줄인 점이 이번 변경의 이점입니다.",
        "",
        f"Hybrid에서 첫 근거 순위가 내려간 문항은 {', '.join(declines) or '없음'}입니다.",
        f"두 인덱스·두 검색 방식 모두 Top-5에서 근거를 놓친 문항은 {', '.join(misses) or '없음'}입니다.",
        "다음 개선은 별도 평가셋으로 오탈자 처리와 Hybrid 결합 점수를 확인하는 것이 좋습니다.",
        "이번 비교 조건인 질문 변환 끔과 검색 가중치는 그대로 유지했습니다.",
        "",
        "## 비교 조건",
        "",
        "| 항목 | 조건 |",
        "|---|---|",
        f"| 저장 청크 | 기존 {info['old']['count']}개 / 신규 {info['new']['count']}개 |",
        "| 검색 방식 | Vector, Hybrid / Top-5 / 질문 변환 끔 / 리랭킹 끔 |",
        "| Hybrid | 기존 검색기의 벡터 0.6·BM25 0.4, 후보 배수 4 |",
        "| 질문 벡터 | 같은 모델 revision·같은 질문 벡터 캐시를 양쪽에 사용 |",
        "| 문서 벡터 | 같은 단일 벡터 변환·768차원, 기존 입력 상한 255 / 신규 800토큰 |",
        "| 신규 청킹 | 문서별 구분자, 특수토큰을 포함한 800토큰·중첩 상한 200토큰 |",
        "| 기준 인덱스 | 백업에 저장된 Chroma·BM25의 평가용 복사본 |",
        "| 원본 보존 | 평가 전후 백업 인덱스의 모든 파일 SHA-256 일치 |",
        "| 상담 고객 | 연회비 대비 가치를 상담한 `m_59853c3d8e1e3c25` |",
        "| 카드 | 생활 포인트 `D2-C001`, 무할 `D2-C003` |",
        "",
        "고객·카드 조건이 없는 질문은 전체 문서에서 검색했습니다.",
        "확정된 고객·카드 조건은 순위 계산 전에 메타데이터로 적용했습니다.",
        "복합 질문 E13은 약관과 해당 카드 범위를 OR로 결합하여 총 5개를 반환했습니다.",
        "이 필터는 평가용 어댑터가 적용하며, 기존 검색기의 점수 계산·후보 병합 코드는 그대로 사용했습니다.",
        "",
        "## 원문 근거를 찾은 비율과 순위",
        "",
        f"정답 근거가 있는 {positives}문항을 집계했습니다. 근거가 없는 {len(questions)-positives}문항은 따로 다룹니다.",
        "청크 ID 대신 원문 파일과 미리 지정한 근거 문자열로 일치 여부를 확인했습니다.",
        "같은 근거가 중첩된 여러 청크에 있어도 근거 Recall에는 한 번만 반영합니다.",
        "",
        "| 인덱스·검색 | Hit@5 | 근거 Recall@5 | MRR@5 | 근거 청크 Precision@5 | 검색 중앙값(ms) |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for label in ("old", "new"):
        for mode in ("vector", "hybrid"):
            summary = result["summary"][f"{label}_{mode}"]
            name = "기존" if label == "old" else "신규"
            lines.append(f"| {name} {mode} | {summary['hit_at_5']:.1%} | "
                         f"{summary['evidence_recall_at_5']:.1%} | {summary['mrr_at_5']:.3f} | "
                         f"{summary['precision_at_5']:.1%} | {summary['search_ms_median']:.1f} |")
    lines += ["", "Hit@5는 근거를 하나라도 찾은 질문 비율입니다. 근거 Recall@5는 질문별로 필요한 근거 조각 중",
              "찾은 비율을 평균한 값입니다. MRR@5는 처음 근거가 등장한 순위의 역수를 평균합니다.",
              "Precision@5는 반환한 5개 중 지정 근거를 포함한 청크의 비율입니다.",
              "이 값은 원문 조각을 찾는 지표이며, 답변의 완전성이나 의미적 정확성을 판정하지 않습니다.",
              "", "검색 시간은 모델 적재·질문 임베딩을 제외한 단일 실행 관측값입니다.",
              "실행 순서와 캐시의 영향을 받으므로 성능 우위를 입증하는 벤치마크로 해석하지 않습니다.",
              "", "## 문항별 결과", "",
              "각 칸은 **처음 근거가 나온 순위 / 근거 조각 회수율**입니다. `없음`은 상위 5개에서 찾지 못했다는 뜻입니다.",
              "", "| 문항 | 기존 Vector | 신규 Vector | 기존 Hybrid | 신규 Hybrid |",
              "|---|---|---|---|---|"]
    for question in questions:
        if not question["answerable"]:
            continue
        cells = []
        for label, mode in (("old", "vector"), ("new", "vector"), ("old", "hybrid"), ("new", "hybrid")):
            metric = lookup[question["id"], label, mode]["metrics"]
            ranks = metric["relevant_ranks"]
            cells.append(f"{str(ranks[0]) + '위' if ranks else '없음'} / {metric['evidence_recall_at_5']:.0%}")
        lines.append(f"| {question['id']} | " + " | ".join(cells) + " |")
    lines += ["", "## 근거가 없는 질문", "",
              "검색은 관련도가 높은 후보를 반환하므로, 자료에 정답이 없어도 결과가 나올 수 있습니다.",
              "이번에는 답변 생성·거절 판단을 실행하지 않아 이 질문들의 정답률이나 환각률은 계산하지 않았습니다.",
              "", "| 문항 | 질문 | 근거 없음의 이유 |", "|---|---|---|"]
    for question in questions:
        if not question["answerable"]:
            lines.append(f"| {question['id']} | {question['question']} | {question['no_answer_reason']} |")
    lines += ["", "## 해석할 때 고려할 점", "",
              "이번 변경은 공통 분할기와 후속 정제뿐 아니라 기존 모델의 255토큰 절단도 함께 수정했습니다.",
              "따라서 점수 차이를 청킹 순서 하나의 효과로 분리해 설명할 수는 없습니다.",
              "새로운 일반화 규칙은 이 20문항에 맞춰 청크 크기나 구분자를 튜닝하지 않은 상태로 평가했습니다.",
              "", "긴 청크는 정답 근거를 함께 담을 가능성이 커지지만, 불필요한 문맥도 함께 검색할 수 있습니다.",
              "표 구조·페이지를 넘는 조항의 완전한 보존은 이번 공통 분할 방식이 보장하는 성질이 아닙니다.",
              "다른 카드·고객 질문과 표를 해석해야 하는 질문은 별도 보류 평가셋으로 확인하는 것이 좋습니다.",
              "", "## 실제 인덱싱과 재실행 확인", "",
              f"원문 {final['sources']}개에서 {audit['chunk_count']}개 청크를 게시했습니다.",
              f"문서 유형별 청크 수는 {audit['chunks_by_document_type']}입니다.",
              f"정제 후 실제 입력 길이는 {audit['actual_token_min']}~{audit['actual_token_max']}토큰입니다.",
              f"벡터 {audit['vector_count']}개의 차원은 {audit['dimension']}이고 L2 노름 검사를 통과했습니다.",
              f"검사 대상 개인정보 형식의 잔존은 {audit['residual_pii_format_matches']}건입니다.",
              "", f"첫 구축은 {initial['index']['newly_embedded']}개를 실제 임베딩했고, "
              f"최종 코드의 재실행에서는 {final['index']['skipped_by_hash']}개 벡터를 재사용했습니다.",
              f"변경 없는 새 실행의 결과는 `no_op={str(noop['no_op']).lower()}`입니다.",
              f"해당 응용 처리 시간은 {noop['timings']['total_ms']}ms이며 Python 프로세스 시작 시간은 제외합니다.",
              "상세 값은 `index-audit.json`, `build-result.json`, `final-build-result.json`, `noop-result.json`에 있습니다.",
              "", "## 재현 자료", "",
              "- `comparison.json`: 80회 검색의 순위·본문·점수·시간, 설정, 원본 파일 지문",
              "- `../group2_questions.json`: 원문 질문, 평가 대상, 정답 근거와 근거 없음의 이유",
              "- `../compare.py`: 기존 검색기를 호출하는 실행 코드",
              "- `test-results.txt`, `type-check.txt`: 테스트와 타입 검사 실행 결과",
              "- `../../README.md`: 실행 방법과 계층별 책임", ""]
    (HERE / "results" / "검색품질-비교보고서.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
