"""품질평가 명령행 — build · verify · ragas · review export/agree · run · compare 하위 명령을 서비스로 넘김."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Callable

from app.application.models import QualityError

DEFAULT_MD = "eval-set.md"
DEFAULT_JSON = "eval-set.json"


def _print(value: Any) -> None:
    """결과 dict를 한글 그대로 들여 써서 보여 줌."""

    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def _parser() -> argparse.ArgumentParser:
    """하위 명령별 인자를 정의함."""

    parser = argparse.ArgumentParser(description="품질평가 프로그램 — 평가셋 · RAGAS · 사람 검토표 · 버전 실험")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="eval-set.md → eval-set.json(검증 통과 때만 저장)")
    build.add_argument("--md", type=Path, default=Path(DEFAULT_MD))
    build.add_argument("--out", type=Path, default=Path(DEFAULT_JSON))
    build.add_argument("--no-index", action="store_true", help="색인 없이 구조 검사(⑤)만 함")

    verify = sub.add_parser("verify", help="eval-set.json을 사용 중 세대로 다시 검증")
    verify.add_argument("--questions", type=Path, default=Path(DEFAULT_JSON))
    verify.add_argument("--no-index", action="store_true")
    verify.add_argument("--out", type=Path, default=None, help="검증 보고서 JSON 저장 경로")

    ragas = sub.add_parser("ragas", help="리트리버 결과 로그를 RAGAS 핵심 4지표(Precision · Recall · Faithfulness · Relevancy)로 채점")
    ragas.add_argument("--log", type=Path, required=True, help="evaluate_retriever.py --generate-answer 결과 JSON")
    ragas.add_argument("--provider", choices=("local", "anthropic", "groq"), default="local")
    ragas.add_argument("--repeat", type=int, default=3)
    ragas.add_argument("--out", type=Path, default=None, help="기본 logs/ragas-시각.json")

    review = sub.add_parser("review", help="사람 검토표 export · agree")
    review_sub = review.add_subparsers(dest="action", required=True)
    export = review_sub.add_parser("export", help="문항당 1행 검토표 CSV 만들기")
    export.add_argument("--log", type=Path, required=True)
    export.add_argument("--ragas-log", type=Path, required=True)
    export.add_argument("--out", type=Path, required=True)
    export.add_argument("--version", default=None)
    export.add_argument("--overwrite", action="store_true", help="사람 판정이 든 검토표도 덮어씀")
    agree = review_sub.add_parser("agree", help="사람 판정과 지표별 LLM 판정의 일치율 · F1 · kappa")
    agree.add_argument("csv", type=Path, nargs="+")
    agree.add_argument("--threshold", type=float, default=0.5, help="LLM 합격 기준값(설계 가정 0.5)")
    agree.add_argument("--out", type=Path, default=None)

    run = sub.add_parser("run", help="계획 파일로 버전 실험 실행(F0 ~ F7)")
    run.add_argument("--plan", type=Path, required=True)
    run.add_argument("--versions", default=None, help="돌릴 버전 id를 쉼표로(기준은 항상 포함)")
    run.add_argument("--resume", action="store_true", help="성공 단계는 건너뛰고 실패 · 끊긴 단계부터")
    run.add_argument("--stop-on-error", action="store_true", help="한 버전이 실패하면 전체를 멈춤")
    run.add_argument("--check-only", action="store_true", help="실행 전 검사만 하고 끝냄")

    compare = sub.add_parser("compare", help="실험 폴더로 비교표만 다시 만들기")
    compare.add_argument("--plan", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None, services_factory: Callable[[], Any] | None = None) -> int:
    """명령을 실행하고 종료 코드를 돌려줌(정상 0 · 검사 거부 2 · 실행 오류 1 · 중단 130).

    인자: services_factory를 주면 그 서비스로 실행함(시험용). 없으면 bootstrap으로 조립함.
    """

    args = _parser().parse_args(argv)
    if services_factory is None:
        from app.bootstrap import create_services  # 도움말만 볼 때 모델 · 평가자 모듈을 읽지 않게 늦게 import함

        services_factory = create_services
    try:
        services = services_factory()
        if args.command == "build":
            report = services.eval_set.build(args.md, args.out, with_index=not args.no_index)
            _print(report)
            return 0 if report["passed"] else 1
        if args.command == "verify":
            report = services.eval_set.verify_file(args.questions, with_index=not args.no_index, out_path=args.out)
            _print(report)
            return 0 if report["passed"] else 1
        if args.command == "ragas":
            from datetime import datetime, timezone

            out = args.out or Path("logs") / f"ragas-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.json"
            report = services.ragas.score_file(args.log, out, provider=args.provider, repeat=args.repeat)
            _print({"saved_to": str(out), "scored": report["scored"], "excluded": report["excluded"],
                    "failed_scores": len(report["failed_scores"]),
                    "summary": {m: v["mean"] for m, v in report["summary"].items()}})
            return 0
        if args.command == "review" and args.action == "export":
            rows = services.review.export(args.log, args.ragas_log, args.out, version=args.version,
                                          overwrite=args.overwrite)
            _print({"saved_to": str(args.out), "rows": rows})
            return 0
        if args.command == "review" and args.action == "agree":
            _print(services.review.agree(args.csv, threshold=args.threshold, out_path=args.out))
            return 0
        if args.command == "run":
            if args.check_only:
                _print(services.runner.preflight(args.plan))
                return 0
            only = [v.strip() for v in args.versions.split(",")] if args.versions else None
            _print(services.runner.run(args.plan, only=only, resume=args.resume, stop_on_error=args.stop_on_error))
            return 0
        if args.command == "compare":
            result = services.runner.rebuild_compare(args.plan)
            _print({"warnings": result["warnings"], "verdicts": result["verdicts"]})
            return 0
    except QualityError as error:
        print(json.dumps({"status": "error", "code": error.code, "message": error.message}, ensure_ascii=False),
              file=sys.stderr)
        return error.exit_code
    except KeyboardInterrupt:
        print(json.dumps({"status": "interrupted"}, ensure_ascii=False), file=sys.stderr)
        return 130
    return 1


def run_with(command: list[str]) -> int:
    """실행 스크립트(build_eval_set.py 등)가 앞 명령어를 붙여 부르는 진입점."""

    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    return main([*command, *sys.argv[1:]])


if __name__ == "__main__":
    for _stream in (sys.stdout, sys.stderr):
        if hasattr(_stream, "reconfigure"):
            _stream.reconfigure(encoding="utf-8")
    raise SystemExit(main())
