"""Retriever 명령을 응용 요청으로 바꾸는 얇은 표현 계층."""

import argparse
from datetime import datetime
import json
import sys
from uuid import uuid4

from app.application.graph import answer_question
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
        choices=("vector", "hybrid", "hybrid_rerank"),
        default="hybrid_rerank",
        help="검색 경로",
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
    return parser


def _emit(result: SearchResult) -> None:
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    thread_id = args.thread_id or _thread_id()
    try:
        if not args.query.strip():
            raise ValueError("--query는 공백이 아닌 글자를 포함해야 함")
        request = RetrieverRequest(
            query=args.query.strip(),
            top_k=args.top_k,
            mode=args.mode,
            transform=args.transform,
            role=args.role,
            thread_id=thread_id,
            dry_run=args.dry_run,
            prompt_only=args.prompt_only,
            max_llm_calls=args.max_llm_calls,
        )
        result = answer_question(request)
        _emit(result)
        return 1 if result.status == "error" else 0
    except (ValueError, OSError, RuntimeError, ImportError) as error:
        print(f"실행 중단: {error}", file=sys.stderr)
        _emit(
            SearchResult(
                query=args.query.strip(),
                mode=args.mode,
                transform=args.transform,
                role=args.role,
                top_k=max(0, args.top_k),
                route=RouteInfo(action="off"),
                status="error",
                thread_id=thread_id,
            )
        )
        return 1
