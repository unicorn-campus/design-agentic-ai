"""Retriever CLI 표현 경계 시험."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import unittest
from unittest.mock import patch

from app.application.state import RouteInfo, SearchResult
from app.presentation.cli import build_parser, main


def result(status: str = "ok") -> SearchResult:
    return SearchResult(
        query="연회비 조건",
        mode="vector",
        transform="off",
        role="agent",
        top_k=5,
        route=RouteInfo(action="off"),
        status=status,
        thread_id="ret-cli",
    )


class RetrieverCliTest(unittest.TestCase):
    def test_cli_help_lists_vector_rerank_mode(self) -> None:
        self.assertIn("vector_rerank", build_parser().format_help())

    def test_cli_calls_one_answer_use_case(self) -> None:
        with (
            patch("app.presentation.cli.answer_question", return_value=result()) as answer,
            redirect_stdout(StringIO()) as stdout,
        ):
            code = main(
                [
                    "--query",
                    "연회비 조건",
                    "--mode",
                    "vector",
                    "--thread-id",
                    "ret-cli",
                ]
            )
        self.assertEqual(0, code)
        self.assertEqual(1, answer.call_count)
        self.assertIn('"status": "ok"', stdout.getvalue())

    def test_cli_accepts_and_forwards_vector_rerank_mode(self) -> None:
        with (
            patch("app.presentation.cli.answer_question", return_value=result()) as answer,
            redirect_stdout(StringIO()),
        ):
            code = main(
                [
                    "--query",
                    "연회비 조건",
                    "--mode",
                    "vector_rerank",
                    "--thread-id",
                    "ret-vector-rerank",
                ]
            )

        self.assertEqual(0, code)
        request = answer.call_args.args[0]
        self.assertEqual("vector_rerank", request.mode)

    def test_cli_rejects_blank_query_with_error_json(self) -> None:
        with (
            redirect_stdout(StringIO()) as stdout,
            redirect_stderr(StringIO()) as stderr,
        ):
            code = main(["--query", "   ", "--thread-id", "ret-error"])
        self.assertEqual(1, code)
        self.assertIn('"status": "error"', stdout.getvalue())
        self.assertIn("실행 중단:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
