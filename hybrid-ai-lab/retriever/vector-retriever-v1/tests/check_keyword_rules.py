"""핵심어 선별 규칙을 pytest 없이 검증하는 실행 스크립트.

이 프로젝트의 가상환경에는 pytest가 없으므로 순수 함수 시험을 이 스크립트로 대신함.
Indexer의 tests/test_card_aliases.py가 이 스크립트를 하위 프로세스로 실행해 회귀를 함께 지킴.
모두 통과하면 "keyword-rules-ok"를 출력하고 0으로 끝남.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.domain.keywords import (  # noqa: E402
    TermObservation,
    bm25_idf,
    evaluate_coverage,
    select_keywords,
)


def _noun(token: str, *, proper: bool = False) -> TermObservation:
    """일반명사 또는 고유명사 관찰값을 만듦."""

    return TermObservation(token, "NNP" if proper else "NNG", proper)


def check_verbs_and_endings_are_dropped() -> None:
    """동사·어미는 명사가 아니므로 핵심어 후보에서 빠짐을 확인함."""

    report = select_keywords(
        [_noun("연회비"), TermObservation("하", "VV", False), TermObservation("어", "EC", False)],
        total_documents=100,
        document_frequency={"연회비": 5},
        max_document_ratio=1.0,
    )
    assert [item.token for item in report.keywords] == ["연회비"], report.keywords
    assert {item.token for item in report.dropped} == {"하", "어"}


def check_unindexed_proper_name_is_kept_and_common_noun_is_dropped() -> None:
    """색인에 없는 고유이름은 남기고, 색인에 없는 일반명사는 뺌을 확인함."""

    report = select_keywords(
        [_noun("한빛모아생활", proper=True), _noun("공과금")],
        total_documents=100,
        document_frequency={},
        max_document_ratio=1.0,
    )
    assert [item.token for item in report.keywords] == ["한빛모아생활"], report.keywords
    assert [item.token for item in report.dropped] == ["공과금"]
    assert report.keywords[0].document_frequency == 0


def check_frequent_words_are_dropped_by_ratio() -> None:
    """전체 청크의 기준 비율 이상에 나오는 흔한 말이 빠짐을 확인함."""

    report = select_keywords(
        [_noun("연회비"), _noun("면제")],
        total_documents=100,
        document_frequency={"연회비": 80, "면제": 12},
        max_document_ratio=0.6,
    )
    assert [item.token for item in report.keywords] == ["면제"], report.keywords
    assert [item.token for item in report.dropped] == ["연회비"]


def check_keywords_are_sorted_by_idf_and_deduplicated() -> None:
    """드문 말이 앞에 오고 같은 토큰은 한 번만 세어짐을 확인함."""

    report = select_keywords(
        [_noun("면제"), _noun("연회비"), _noun("면제")],
        total_documents=100,
        document_frequency={"연회비": 50, "면제": 3},
        max_document_ratio=1.0,
    )
    assert [item.token for item in report.keywords] == ["면제", "연회비"], report.keywords
    assert bm25_idf(100, 3) > bm25_idf(100, 50) > 0


def check_coverage_marks_missing_and_top_missing() -> None:
    """결과에 없는 핵심어와 상위 핵심어 미포함이 드러남을 확인함."""

    report = select_keywords(
        [_noun("한빛모아생활", proper=True), _noun("연회비")],
        total_documents=100,
        document_frequency={"한빛모아생활": 2, "연회비": 40},
        max_document_ratio=1.0,
    )
    covered = evaluate_coverage(
        report,
        {"c1": frozenset({"연회비", "면제"}), "c2": frozenset({"연회비"})},
    )
    assert covered.missing == ("한빛모아생활",), covered.missing
    assert covered.top_missing(1) == ("한빛모아생활",)
    assert [item.present_in for item in covered.coverage if item.keyword.token == "연회비"] == [
        ("c1", "c2")
    ]


def check_invalid_ratio_is_rejected() -> None:
    """기준 비율이 범위를 벗어나면 즉시 막힘을 확인함."""

    for ratio in (0.0, -0.1, 1.5):
        try:
            select_keywords([], total_documents=1, document_frequency={}, max_document_ratio=ratio)
        except ValueError:
            continue
        raise AssertionError(f"잘못된 기준 비율이 통과함: {ratio}")


def main() -> None:
    """모든 규칙 검증을 차례로 실행함."""

    check_verbs_and_endings_are_dropped()
    check_unindexed_proper_name_is_kept_and_common_noun_is_dropped()
    check_frequent_words_are_dropped_by_ratio()
    check_keywords_are_sorted_by_idf_and_deduplicated()
    check_coverage_marks_missing_and_top_missing()
    check_invalid_ratio_is_rejected()
    print("keyword-rules-ok")


if __name__ == "__main__":
    main()
