"""Indexer CLI 표현 경계 시험."""

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.application.state import IndexResult
from app.presentation.cli import main


class IndexerCliTest(unittest.TestCase):
    def test_cli_calls_one_use_case_and_saves_numbered_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = IndexResult(
                status="dry_run",
                exit_code=0,
                thread_id="idx-cli",
            )
            with (
                patch("app.presentation.cli.run_indexing", return_value=result) as run,
                redirect_stdout(StringIO()) as stdout,
                redirect_stderr(StringIO()) as stderr,
            ):
                code = main(
                    [
                        "--in",
                        directory,
                        "--out",
                        directory,
                        "--backend",
                        "smoke",
                        "--dry-run",
                        "--thread-id",
                        "idx-cli",
                    ]
                )
            self.assertEqual(0, code)
            self.assertEqual(1, run.call_count)
            self.assertIn('"status": "dry_run"', stdout.getvalue())
            self.assertIn("결과 저장:", stderr.getvalue())
            self.assertTrue((output / "index_run1.json").is_file())

    def test_cli_error_keeps_stdout_json_contract(self) -> None:
        with (
            patch("app.presentation.cli.run_indexing", side_effect=ValueError("잘못된 입력")),
            redirect_stdout(StringIO()) as stdout,
            redirect_stderr(StringIO()) as stderr,
        ):
            code = main(["--thread-id", "idx-error"])
        self.assertEqual(1, code)
        self.assertIn('"status": "error"', stdout.getvalue())
        self.assertIn("실행 중단:", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
