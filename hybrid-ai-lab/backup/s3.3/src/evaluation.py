"""슬라이드 20~21의 고정 질문 Top-K 포함률 실행기."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from time import perf_counter


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    expected_chunk_ids: tuple[str, ...]
    expected_location: str = ""
    note: str = ""


def load_cases(path: Path) -> list[EvaluationCase]:
    """질문과 사전 정답 ID를 읽고 기본 형식을 검사함."""
    raw = json.loads(path.read_text(encoding="utf-8-sig"))
    items = raw.get("cases") if isinstance(raw, dict) else None
    if not isinstance(items, list) or not items:
        raise ValueError("질문 파일에는 비어 있지 않은 cases 목록이 필요함")
    cases = []
    seen = set()
    for item in items:
        case_id = str(item.get("id", "")).strip()
        question = str(item.get("question", "")).strip()
        expected = item.get("expected_chunk_ids", [])
        if not case_id or case_id in seen or not question:
            raise ValueError("각 질문에는 중복되지 않는 id와 question이 필요함")
        if not isinstance(expected, list) or any(not str(v).strip() for v in expected):
            raise ValueError(f"{case_id}: expected_chunk_ids는 문자열 목록이어야 함")
        seen.add(case_id)
        cases.append(EvaluationCase(
            case_id=case_id,
            question=question,
            expected_chunk_ids=tuple(str(v).strip() for v in expected),
            expected_location=str(item.get("expected_location", "")).strip(),
            note=str(item.get("note", "")).strip(),
        ))
    return cases


def _merge_hits(hit_groups: list[list]) -> list:
    """같은 청크는 가장 높은 점수 한 건만 남기고 점수순으로 정렬함."""
    best = {}
    for hits in hit_groups:
        for hit in hits:
            chunk_id = str(hit.metadata.get("chunk_id", ""))
            if chunk_id and (chunk_id not in best or hit.score > best[chunk_id].score):
                best[chunk_id] = hit
    return sorted(best.values(), key=lambda hit: hit.score, reverse=True)


def evaluate_cases(
    cases: list[EvaluationCase],
    search_fn,
    *,
    transform_fn=None,
    mode: str = "baseline",
    retrieve_k: int = 10,
    judge_k: int = 3,
    user_role: str = "agent",
) -> dict:
    """모든 정답 청크가 상위 judge_k에 포함되는지 사례별로 평가함."""
    if retrieve_k < judge_k or judge_k <= 0:
        raise ValueError("retrieve_k는 judge_k 이상이고 judge_k는 양수여야 함")
    if mode != "baseline" and transform_fn is None:
        raise ValueError("질문 변환 방식에는 transform_fn이 필요함")

    rows = []
    passed = 0
    scored = 0
    for case in cases:
        started = perf_counter()
        queries = [case.question] if mode == "baseline" else transform_fn(case.question, mode)
        groups = [search_fn(q, retrieve_k, None, user_role) for q in queries]
        hits = _merge_hits(groups)
        top = hits[:judge_k]
        top_ids = [str(hit.metadata.get("chunk_id", "")) for hit in top]
        ranks = {
            expected: next(
                (index for index, hit in enumerate(hits, start=1)
                 if hit.metadata.get("chunk_id") == expected),
                None,
            )
            for expected in case.expected_chunk_ids
        }
        scorable = bool(case.expected_chunk_ids)
        success = scorable and all(
            rank is not None and rank <= judge_k for rank in ranks.values()
        )
        if scorable:
            scored += 1
            passed += int(success)
        rows.append({
            "id": case.case_id,
            "question": case.question,
            "queries": queries,
            "expected_chunk_ids": list(case.expected_chunk_ids),
            "expected_location": case.expected_location,
            "ranks": ranks,
            "top_hits": [
                {
                    "rank": index,
                    "chunk_id": hit.metadata.get("chunk_id"),
                    "score": hit.score,
                    "location": hit.metadata.get("clause_no", ""),
                    "source": hit.metadata.get("source", ""),
                }
                for index, hit in enumerate(top, start=1)
            ],
            "scorable": scorable,
            "top_k_included": success if scorable else None,
            "note": case.note,
            "elapsed_ms": round((perf_counter() - started) * 1000, 1),
        })

    return {
        "mode": mode,
        "retrieve_k": retrieve_k,
        "judge_k": judge_k,
        "case_count": len(cases),
        "scored_count": scored,
        "passed_count": passed,
        "inclusion_rate": round(passed / scored, 4) if scored else None,
        "dataset_ready": scored == len(cases),
        "rows": rows,
    }


def render_markdown(result: dict) -> str:
    """실행 결과를 교재 기록표와 같은 형태로 표시함."""
    rate = result["inclusion_rate"]
    rate_text = f"{rate * 100:.1f}%" if rate is not None else "계산 불가"
    judge_label = f"Top-{result['judge_k']}"
    lines = [
        f"# {judge_label} 정답 포함 결과",
        "",
        f"- 실행 방식: `{result['mode']}`",
        f"- 평가 가능 질문: {result['scored_count']}/{result['case_count']}",
        f"- 통과: {result['passed_count']}/{result['scored_count']}",
        f"- 포함률: {rate_text}",
        f"- 평가셋 준비 완료: {result['dataset_ready']}",
        "",
        f"| # | 원본 질문 | 정답 조각 | {judge_label} | 정답 순위 | 판정 |",
        "|---|---|---|---|---|---|",
    ]
    for row in result["rows"]:
        expected = ", ".join(row["expected_chunk_ids"]) or row["expected_location"] or "미지정"
        top_ids = ", ".join(hit["chunk_id"] for hit in row["top_hits"]) or "없음"
        rank_text = ", ".join(
            f"{chunk_id}:{rank or '없음'}" for chunk_id, rank in row["ranks"].items()
        ) or "정답 미매핑"
        verdict = "○" if row["top_k_included"] else ("×" if row["scorable"] else "평가 제외")
        cells = [row["id"], row["question"], expected, top_ids, rank_text, verdict]
        escaped = [str(value).replace("|", "\\|").replace("\n", " ") for value in cells]
        lines.append("| " + " | ".join(escaped) + " |")
    lines.append("")
    return "\n".join(lines)


def serializable_cases(cases: list[EvaluationCase]) -> list[dict]:
    """CLI 출력에 사용할 사례 목록을 반환함."""
    values = []
    for case in cases:
        item = asdict(case)
        item["expected_chunk_ids"] = list(case.expected_chunk_ids)
        values.append(item)
    return values
