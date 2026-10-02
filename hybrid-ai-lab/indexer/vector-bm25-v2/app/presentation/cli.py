"""명령행 옵션을 응용 요청으로 바꾸고 실행 결과와 종료 코드를 출력함."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import sys
from uuid import uuid4

from app.application.models import IndexRequest


def main(argv: list[str] | None = None) -> int:
    """명령행 인덱싱 요청을 실행하고 자동화 도구가 판단할 종료 코드를 반환함.

    인자: argv가 None이면 프로세스의 명령행 인자를 사용함.
    반환값: 정상 실행은 서비스의 종료 코드, 사용자 중단은 130, 실행 중 오류는 1임.
    예외: 옵션 해석은 argparse에 맡기므로 도움말·잘못된 옵션은 SystemExit로 처리됨.
    부수효과: 서비스가 인덱스를 갱신할 수 있으며 결과 JSON은 표준 출력, 실행 ID·오류는 표준 오류에 기록함.
    """
    parser = argparse.ArgumentParser(description="문서별 구분자와 800/200토큰으로 Chroma·BM25를 구축합니다.")
    parser.add_argument("--input", help="원문 디렉터리 또는 파일")
    parser.add_argument("--output", help="결과 디렉터리")
    parser.add_argument("--doc", choices=("all", "D1", "D2", "D3"), default="all")
    parser.add_argument("--segment", type=int, help="D3 상담 세그먼트 번호(1~6)")
    parser.add_argument("--thread-id", help="중단된 실행과 같은 값을 주면 체크포인트부터 재개합니다.")
    parser.add_argument("--full-reindex", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="정제·청킹·검증까지 수행하고 색인은 게시하지 않습니다.")
    args = parser.parse_args(argv)
    thread_id = args.thread_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8]
    # 처리 시작 전에 실행 ID를 남겨 중단되어도 같은 ID로 재개할 수 있게 함.
    print(f"thread_id={thread_id}", file=sys.stderr, flush=True)
    try:
        # 도움말만 조회할 때는 모델·저장소 조립에 필요한 모듈을 불필요하게 읽지 않음.
        from app.bootstrap import create_cli_service
        service, input_path, output_path = create_cli_service({"INPUT_PATH": args.input, "OUTPUT_PATH": args.output})
        request = IndexRequest(input_path=input_path, output_path=output_path, doc=args.doc,
                               segment=args.segment, thread_id=thread_id, full_reindex=args.full_reindex,
                               dry_run=args.dry_run)
        result = service.run(request)
        print(result.model_dump_json(indent=2))
        return result.exit_code
    except KeyboardInterrupt:
        # 명령행 중단 관례인 130을 사용하여 일반 실행 오류와 구분함.
        print(json.dumps({"status": "interrupted", "thread_id": thread_id}, ensure_ascii=False), file=sys.stderr)
        return 130
    except Exception as error:
        # 호출자가 실패를 자동 판정할 수 있게 오류 종류·메시지를 JSON과 종료 코드 1로 전달함.
        print(json.dumps({"status": "error", "thread_id": thread_id,
                          "error_type": type(error).__name__, "message": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
