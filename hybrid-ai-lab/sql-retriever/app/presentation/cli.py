"""명령행 입력을 응용 요청으로 바꾸고 결과를 출력하는 표현 계층."""

import argparse
import json

from app.application.lab_service import DEFAULT_QUESTION
from app.application.models import LabRequest


MODES = (
    "schema",
    "products",
    "usage",
    "delinquency",
    "context",
    "first",
    "nl2sql",
    "ask",
)
DATABASE_MODES = frozenset({"schema", "products", "usage", "delinquency", "context", "ask"})
REPRESENTATIVES = {
    1: "M-1001",
    2: "M-1042",
    3: "M-3001",
    4: "M-4001",
    5: "M-5001",
    6: "M-6001",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Layered Architecture 기반 SQL·NL2SQL 예제")
    parser.add_argument("--mode", choices=MODES, default="ask", help="실행할 예제 모드")
    parser.add_argument("--segment", type=int, choices=range(1, 7), default=2)
    parser.add_argument("--member-id")
    parser.add_argument("--base-date", default="2026-08-31")
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    parser.add_argument("--offline", action="store_true", help="LLM 호출 없이 입력과 프롬프트 확인")
    return parser


def main(argv: list[str] | None = None, application_factory=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if application_factory is None:
            from app.bootstrap import build_application

            application_factory = build_application
        application = application_factory()
        request = LabRequest(
            member_id=args.member_id or REPRESENTATIVES[args.segment],
            base_date=args.base_date,
            question=args.question,
            offline=args.offline,
        )
        if args.mode in DATABASE_MODES:
            print("PostgreSQL 공통 RDB 사용: public 스키마, 읽기 전용 연결")
        result = application.execute(args.mode, request)
        for notice in result.notices:
            print(notice)
        if isinstance(result.payload, str):
            print(result.payload)
        else:
            print(json.dumps(result.payload, ensure_ascii=False, indent=2))
        return result.exit_code
    except (ValueError, RuntimeError, OSError, ImportError) as error:
        print(f"실행 중단: {error}")
        return 1

