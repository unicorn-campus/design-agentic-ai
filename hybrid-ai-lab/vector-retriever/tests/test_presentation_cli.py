"""Retriever CLI 표현 경계 시험."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from tempfile import TemporaryDirectory
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

    def test_cli_out_directory_saves_file_named_by_thread_id(self) -> None:
        with TemporaryDirectory() as folder:
            target = Path(folder) / "answers"
            with (
                patch("app.presentation.cli.answer_question", return_value=result()),
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()) as stderr,
            ):
                code = main(["--query", "연회비 조건", "--thread-id", "ret-cli", "--out", str(target)])
            saved = target / "ret-cli.json"
            self.assertEqual(0, code)
            self.assertTrue(saved.exists())
            self.assertEqual("ok", json.loads(saved.read_text(encoding="utf-8"))["status"])
            self.assertIn("결과 저장:", stderr.getvalue())

    def test_cli_out_json_path_saves_to_that_exact_file(self) -> None:
        with TemporaryDirectory() as folder:
            target = Path(folder) / "nested" / "answer.json"
            with (
                patch("app.presentation.cli.answer_question", return_value=result()),
                redirect_stdout(StringIO()),
                redirect_stderr(StringIO()),
            ):
                code = main(["--query", "연회비 조건", "--thread-id", "ret-cli", "--out", str(target)])
            self.assertEqual(0, code)
            self.assertTrue(target.exists())

    def test_cli_out_also_saves_error_record_with_detail(self) -> None:
        with TemporaryDirectory() as folder:
            target = Path(folder) / "answers"
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                code = main(["--query", "   ", "--thread-id", "ret-error", "--out", str(target)])
            saved = target / "ret-error.json"
            self.assertEqual(1, code)
            self.assertTrue(saved.exists())
            record = json.loads(saved.read_text(encoding="utf-8"))
            self.assertEqual("error", record["status"])
            self.assertIn("ValueError", record["route"]["error"])


if __name__ == "__main__":
    unittest.main()
