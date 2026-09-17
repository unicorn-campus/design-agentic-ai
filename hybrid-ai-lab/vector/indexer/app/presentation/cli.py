"""Indexer 명령을 응용 요청으로 바꾸는 얇은 표현 계층."""

import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
from uuid import uuid4

from app.application.graph import run_indexing
from app.application.state import IndexRequest, IndexResult


APP_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = APP_ROOT.parent.parent / "docs"


def _thread_id() -> str:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"idx-{timestamp}-{uuid4().hex[:8]}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LangGraph 기반 문서 Indexer")
    parser.add_argument("--in", dest="in_path", type=Path, default=DEFAULT_INPUT, help="원문 폴더")
    parser.add_argument("--out", type=Path, default=Path("data"), help="결과 폴더")
    parser.add_argument("--doc", choices=("D1", "D2", "D3", "all"), default="all", help="처리 문서")
    parser.add_argument("--segment", type=int, choices=range(1, 7), help="D3 상담 파일 번호")
    parser.add_argument("--thread-id", default=None, help="체크포인트 세션 키")
    parser.add_argument("--full-reindex", action="store_true", help="전량 재적재")
    parser.add_argument("--dry-run", action="store_true", help="청킹까지만 실행")
    parser.add_argument(
        "--embedding-backend",
        choices=("sentence-transformers", "smoke"),
        default="sentence-transformers",
        help="임베딩 백엔드",
    )
    return parser


def _result_path(output_path: Path) -> Path:
    output_path.mkdir(parents=True, exist_ok=True)
    index = 1
    while (output_path / f"index_run{index}.json").exists():
        index += 1
    return output_path / f"index_run{index}.json"


def _emit(result: IndexResult) -> None:
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    thread_id = args.thread_id or _thread_id()
    try:
        request = IndexRequest(
            input_path=args.in_path,
            output_path=args.out,
            doc=args.doc,
            segment=args.segment,
            thread_id=thread_id,
            full_reindex=args.full_reindex,
            dry_run=args.dry_run,
            embedding_backend=args.embedding_backend,
        )
        result = run_indexing(request)
        _emit(result)
        result_path = _result_path(request.output_path)
        result_path.write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"결과 저장: {result_path}", file=sys.stderr)
        return result.exit_code
    except (ValueError, OSError, RuntimeError, NotImplementedError) as error:
        print(f"실행 중단: {error}", file=sys.stderr)
        _emit(IndexResult(status="error", exit_code=1, thread_id=thread_id))
        return 1
