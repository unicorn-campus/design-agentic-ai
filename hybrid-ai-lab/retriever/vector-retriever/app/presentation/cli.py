"""명령행 입력을 검색 요청으로 바꿔 결과를 사람이 읽을 형태로 보여 주는 CLI 진입점임."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from typing import Any, TextIO

from app.application.models import (
    STATUS_ERROR,
    SearchRequest,
    SearchResponse,
)
from app.domain.access import ROLE_ACCESS_LEVELS

EVIDENCE_PREVIEW_CHARS = 160  # 근거 본문 미리보기 길이. 터미널 한 화면에 여러 건이 보이게 자름
ROLE_CHOICES = tuple(ROLE_ACCESS_LEVELS)  # 역할 목록은 권한 규칙(domain)이 소유함


class _ParserExit(Exception):
    """argparse가 프로세스를 바로 끝내지 못하게 막는 내부 신호. main이 종료 코드로 바꿈."""

    def __init__(self, status: int, message: str | None = None) -> None:
        self.status = status
        self.message = message


class _ArgumentParser(argparse.ArgumentParser):
    """시험에서 SystemExit 없이 종료 코드를 확인할 수 있게 exit·error를 예외로 바꿈."""

    def exit(self, status: int = 0, message: str | None = None) -> None:
        """argparse가 프로세스를 끝내지 않고 종료 코드를 돌려주게 예외로 바꿈."""
        raise _ParserExit(status, message)

    def error(self, message: str) -> None:
        """인자 오류도 종료 코드 2의 예외로 바꿈."""
        raise _ParserExit(2, message)


def build_parser() -> argparse.ArgumentParser:
    """CLI 인자 정의를 만듦. 역할은 본문이 아니라 실행자가 직접 주는 값임."""

    parser = _ArgumentParser(description="문서 검색(Agentic RAG) 리트리버 CLI")
    parser.add_argument("--query", required=True, help="질문(500자 이하)")
    parser.add_argument(
        "--role",
        required=True,
        choices=ROLE_CHOICES,
        help="열람 역할. agent는 public, auditor는 public·restricted 문서를 봄",
    )
    parser.add_argument(
        "--generate-answer",
        action="store_true",
        help="답변 생성까지 함(기본은 끔 — 근거 목록만 돌려줌)",
    )
    parser.add_argument("--top-k", type=int, default=5, help="반환 수(1 ~ 10, 기본 5)")
    parser.add_argument("--member-id", default=None, help="상담 중인 회원번호(예: M-1042) — 상담 이력은 그 회원 것만 검색")
    parser.add_argument("--json", action="store_true", help="사람이 읽는 요약 대신 응답 JSON 원본을 출력")
    return parser


def main(
    argv: Sequence[str] | None = None,
    service: Any = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """CLI를 실행하고 프로세스 종료 코드를 반환함.

    인자: service를 주면 그 서비스를 쓰고, 없으면 bootstrap으로 조립함(시험에서 가짜 주입용).
    반환값: 정상 0, 응답 상태가 오류면 1, 인자 오류면 2임.
    부수효과: stdout에 결과를, stderr에 오류 안내를 씀.
    """

    output = stdout or sys.stdout
    errors = stderr or sys.stderr
    try:
        args = build_parser().parse_args(argv)
    except _ParserExit as exit_signal:
        if exit_signal.message:
            print(f"[인자 오류] {exit_signal.message}", file=errors)
        return exit_signal.status

    try:
        application = service if service is not None else _create_service()
    except Exception:  # noqa: BLE001 - 조립 실패 원인은 서버 로그에만 남기고 화면에는 일반 안내만 보임
        print("[오류] 검색 서비스를 준비하지 못했습니다. 설정과 색인 폴더를 확인해 주세요.", file=errors)
        return 1

    request = SearchRequest(
        query=args.query,
        generate_answer=args.generate_answer,
        top_k=args.top_k,
        member_id=args.member_id,
    )
    response = application.execute(request, args.role)

    if args.json:
        payload = response.model_dump(mode="json") if hasattr(response, "model_dump") else response
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str), file=output)
    else:
        _print_summary(response, output)
    return 1 if getattr(response, "status", "") == STATUS_ERROR else 0


def _create_service() -> Any:
    """조립된 서비스를 가져옴. 표현 계층이 구현체를 직접 만들지 않게 bootstrap만 부름."""

    from app.bootstrap import create_service

    return create_service()


def _print_summary(response: SearchResponse, output: TextIO) -> None:
    """응답을 사람이 읽기 쉬운 요약으로 출력함.

    방법: 상태 → 답변 → 근거 → 확인 못 한 항목 → 경고 → 단계별 시간·호출 수 순서로 보여 줌.
    """

    print(f"상태: {response.status}", file=output)
    if response.request_id:
        print(f"요청ID: {response.request_id}", file=output)
    if response.generation:
        print(f"색인 세대: {response.generation}", file=output)
    if response.question_type:
        print(f"질문 유형: {response.question_type}", file=output)
    if response.message:
        print(f"안내: {response.message}", file=output)
    if response.error_code:
        print(f"오류 코드: {response.error_code}", file=output)

    if response.answer:
        print("\n[답변]", file=output)
        for order, sentence in enumerate(response.answer, start=1):
            quoted = ", ".join(citation.chunk_id for citation in sentence.citations)
            print(f" {order}. {sentence.text}", file=output)
            print(f"    근거 조각: {quoted or '없음'}", file=output)

    if response.evidence:
        print(f"\n[근거 {len(response.evidence)}건]", file=output)
        for item in response.evidence:
            print(f" {item.rank}. {_source_line(item)}", file=output)
            print(f"    점수 {_score_line(item.scores)}", file=output)
            print(f"    본문 {_preview(item.text)}", file=output)

    if response.unresolved:
        print("\n[확인 못 한 항목]", file=output)
        for item in response.unresolved:
            print(f" - {item.sub_question_id} {item.question} — {item.reason}", file=output)
    if response.clarify_question:
        print(f"\n[확인 질문] {response.clarify_question}", file=output)
    if response.warnings:
        print("\n[경고]", file=output)
        for warning in response.warnings:
            print(f" - {warning}", file=output)

    print(f"\n단계별 시간: {_timing_line(response.timings)}", file=output)
    print(f"LLM 호출 수: {response.llm_calls}", file=output)
    if response.finish_reason:
        print(f"종료 사유: {response.finish_reason}", file=output)


def _source_line(item: Any) -> str:
    """근거 1건의 출처 표시를 만듦. 없는 항목(쪽·조항·카드)은 생략함."""

    parts = [item.source or item.doc_key]
    if item.page is not None:
        page = f"p.{item.page}"
        if item.page_end is not None and item.page_end != item.page:
            page = f"p.{item.page} ~ {item.page_end}"
        parts.append(page)
    if item.clause_no:
        parts.append(str(item.clause_no))  # 색인 값이 이미 "제11조"처럼 "조"까지 담고 있음
    if item.card_name:
        parts.append(item.card_name)
    if item.section_label:
        parts.append(item.section_label)
    parts.append(f"조각 {item.chunk_id}")
    return " · ".join(str(part) for part in parts if part)


def _score_line(scores: Any) -> str:
    """검색 점수 4종을 한 줄로 만듦. 해당 검색기 후보에 없던 점수는 '-'로 보임."""

    def shown(value: float | None) -> str:
        """점수를 소수 셋째 자리로, 없으면 '-'로 보여 줌."""
        return "-" if value is None else f"{value:.3f}"

    return (
        f"vector={shown(scores.vector)} bm25={shown(scores.bm25)} "
        f"fused={shown(scores.fused)} rerank={shown(scores.rerank)}"
    )


def _timing_line(timings: dict[str, float]) -> str:
    """단계별 시간을 단계ID 순서로 한 줄로 만듦. 비면 '측정값 없음'임."""

    if not timings:
        return "측정값 없음"
    return ", ".join(f"{step} {seconds:.2f}s" for step, seconds in sorted(timings.items()))


def _preview(text: str) -> str:
    """본문을 한 줄 미리보기로 자름. 줄바꿈은 공백으로 바꿔 표 모양이 깨지지 않게 함."""

    flat = " ".join(str(text).split())
    if len(flat) <= EVIDENCE_PREVIEW_CHARS:
        return flat
    return flat[:EVIDENCE_PREVIEW_CHARS] + "..."
