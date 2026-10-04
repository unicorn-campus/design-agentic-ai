"""Retriever 명령을 응용 요청으로 바꾸는 얇은 표현 계층."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from uuid import uuid4

from app.application.retriever_service import RetrieverService
from app.application.state import RetrieverRequest, RouteInfo, SearchResult


def _thread_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"ret-{timestamp}-{uuid4().hex[:8]}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LangGraph 기반 문서 검색·답변")
    parser.add_argument("--query", required=True, help="검색 질문")
    parser.add_argument("--top-k", type=int, default=5, help="최종 검색 결과 건수")
    parser.add_argument(
        "--mode",
        choices=("vector", "vector_rerank", "hybrid", "hybrid_rerank"),
        default="hybrid_rerank",
        help="검색 경로: 벡터, 벡터+리랭킹, 하이브리드, 하이브리드+리랭킹",
    )
    parser.add_argument(
        "--transform",
        choices=("off", "auto"),
        default="off",
        help="질문 변환 방식",
    )
    parser.add_argument("--role", choices=("agent", "auditor"), default="agent")
    parser.add_argument("--thread-id", help="체크포인트 세션 키")
    parser.add_argument("--dry-run", action="store_true", help="인덱스 연결과 건수만 확인")
    parser.add_argument("--prompt-only", action="store_true", help="답변 LLM 호출 없이 프롬프트까지 실행")
    parser.add_argument("--max-llm-calls", type=int, default=8, help="전송 시도 상한")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="결과 JSON 저장 위치. .json으로 끝나면 그 파일에, 아니면 폴더로 보고 {thread_id}.json으로 저장",
    )
    return parser


def _save(result: SearchResult, out: Path, thread_id: str) -> Path:
    """--out이 .json이면 그 파일에, 아니면 폴더로 보고 실행 로그와 같은 이름으로 저장함."""

    if out.suffix.lower() == ".json":
        path = out
        path.parent.mkdir(parents=True, exist_ok=True)
    else:
        out.mkdir(parents=True, exist_ok=True)
        path = out / f"{thread_id}.json"
    path.write_text(
        json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _report_saved(result: SearchResult, out: Path | None, thread_id: str) -> None:
    """저장에 실패해도 실행 결과 보고 자체는 막지 않음."""

    if out is None:
        return
    try:
        print(f"결과 저장: {_save(result, out, thread_id)}", file=sys.stderr)
    except OSError as error:
        print(f"결과 저장 실패: {error}", file=sys.stderr)


def _emit(result: SearchResult) -> None:
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None, service: RetrieverService | None = None) -> int:
    """CLI 진입점. service를 넘기면 그대로 쓰고(시험용 주입 지점), 없으면 bootstrap으로 조립함."""

    parser = build_parser()
    args = parser.parse_args(argv)
    thread_id = args.thread_id or _thread_id()
    try:
        if not args.query.strip():
            raise ValueError("--query는 공백이 아닌 글자를 포함해야 함")
        request = RetrieverRequest(
            query=args.query.strip(),  # 검색할 질문의 앞뒤 공백을 제거한 문자열
            top_k=args.top_k,  # 최종 결과로 받을 검색 문서의 최대 개수
            mode=args.mode,  # 검색 방식: 벡터·벡터+리랭킹·하이브리드·하이브리드+리랭킹
            transform=args.transform,  # 질문 변환 사용 여부: off 또는 auto
            role=args.role,  # 검색 권한 역할: agent 또는 제한 문서도 보는 auditor
            thread_id=thread_id,  # 체크포인트와 실행 로그에서 이번 요청을 구분하는 ID
            dry_run=args.dry_run,  # True이면 인덱스 상태만 확인하고 실제 검색은 생략
            prompt_only=args.prompt_only,  # True이면 답변용 프롬프트까지만 만들고 LLM 호출은 생략
            max_llm_calls=args.max_llm_calls,  # 한 요청에서 허용할 최대 LLM 호출 횟수
        )
        if service is None:
            from app.bootstrap import create_service

            service = create_service()
        result = service.answer(request)
        _emit(result)
        _report_saved(result, args.out, thread_id)
        return 1 if result.status == "error" else 0
    except (ValueError, OSError, RuntimeError, ImportError) as error:
        detail = RetrieverService.describe_error(error)
        print(f"실행 중단: {detail}", file=sys.stderr)
        # 검색까지는 성공했을 수 있으므로 부분 결과가 있으면 그대로 남김.
        partial = getattr(error, "partial_result", None)
        record = (
            partial
            if isinstance(partial, SearchResult)
            else SearchResult(
                query=args.query.strip(),
                mode=args.mode,
                transform=args.transform,
                role=args.role,
                top_k=max(0, args.top_k),
                route=RouteInfo(action="off", error=detail),
                status="error",
                thread_id=thread_id,
            )
        )
        _emit(record)
        _report_saved(record, args.out, thread_id)
        return 1
