"""S3.3 검색 품질 개선 실습 실행 도구."""

import argparse
import json
from pathlib import Path
import sys

from src.evaluation import evaluate_cases, load_cases, render_markdown
from src.s32_bridge import S32_ROOT, configure_s32, get_search


BASE = Path(__file__).resolve().parent


def emit(value) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2))


def main(reference: bool = False, default_action: str | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="S3.3 검색 품질 개선 실습")
    parser.add_argument(
        "action",
        nargs="?",
        choices=("transform", "hybrid", "run8"),
        default=default_action,
    )
    parser.add_argument("--query")
    parser.add_argument(
        "--mode",
        choices=("baseline", "rewrite", "multi", "hyde", "stepback"),
        default="baseline",
    )
    parser.add_argument("--questions", type=Path, default=BASE / "templates/baseline_questions.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--db-path", type=Path, default=S32_ROOT / "data/chroma/group1")
    parser.add_argument("--collection", default="card_docs_ref")
    parser.add_argument("--model", default="nlpai-lab/KURE-v1")
    parser.add_argument("--retrieve-k", type=int, default=10)
    parser.add_argument("--judge-k", type=int, default=3)
    parser.add_argument("--role", choices=("agent", "auditor"), default="agent")
    parser.add_argument(
        "--student-search",
        action="store_true",
        help="완성본 대신 S3.2의 학생 작성 search를 호출함",
    )
    args = parser.parse_args()

    if args.action is None:
        parser.error("action이 필요함: transform, hybrid 또는 run8")

    try:
        if args.action == "transform":
            if not args.query:
                raise ValueError("transform은 --query가 필요함")
            if args.mode == "baseline":
                value = {"mode": "baseline", "query": args.query, "queries": [args.query]}
            else:
                module_name = "src.query_transform_ref" if reference else "src.query_transform"
                module = __import__(module_name, fromlist=["transform_query"])
                value = {
                    "mode": args.mode,
                    "query": args.query,
                    "queries": module.transform_query(args.query, args.mode),
                }
        elif args.action == "hybrid":
            if not args.query:
                raise ValueError("hybrid는 --query가 필요함")
            config = configure_s32(
                db_path=args.db_path,
                collection=args.collection,
                model=args.model,
            )
            module_name = "src.hybrid_search_ref" if reference else "src.hybrid_search"
            search_hybrid = __import__(module_name, fromlist=["search_hybrid"]).search_hybrid
            hits = search_hybrid(args.query, top_k=args.judge_k, user_role=args.role)
            value = {
                "query": args.query,
                "implementation": "reference" if reference else "student",
                "db_path": str(config.db_path),
                "collection": config.collection,
                "model": config.model,
                "hits": [
                    {
                        "rank": rank,
                        "chunk_id": hit.metadata.get("chunk_id", ""),
                        "score": hit.score,
                        "source": hit.metadata.get("source", ""),
                        "location": hit.metadata.get("clause_no", ""),
                    }
                    for rank, hit in enumerate(hits, start=1)
                ],
            }
        else:
            config = configure_s32(
                db_path=args.db_path,
                collection=args.collection,
                model=args.model,
            )
            search_fn = get_search(reference=not args.student_search)
            transform_fn = None
            if args.mode != "baseline":
                module_name = "src.query_transform_ref" if reference else "src.query_transform"
                transform_fn = __import__(module_name, fromlist=["transform_query"]).transform_query
            cases = load_cases(args.questions)
            value = evaluate_cases(
                cases,
                search_fn,
                transform_fn=transform_fn,
                mode=args.mode,
                retrieve_k=args.retrieve_k,
                judge_k=args.judge_k,
                user_role=args.role,
            )
            value.update({
                "implementation": "reference" if reference else "student",
                "search_implementation": "student" if args.student_search else "reference",
                "db_path": str(config.db_path),
                "collection": config.collection,
                "model": config.model,
            })

        emit(value)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            if args.output.suffix.lower() == ".md" and args.action == "run8":
                args.output.write_text(render_markdown(value), encoding="utf-8")
            else:
                args.output.write_text(
                    json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        return 0
    except NotImplementedError as error:
        print(f"작성 필요: {error}\n완성 예시는 run_lab_ref.py로 실행 가능함", file=sys.stderr)
        return 3
    except (ValueError, KeyError, OSError, RuntimeError, ImportError) as error:
        print(f"실행 중단: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
