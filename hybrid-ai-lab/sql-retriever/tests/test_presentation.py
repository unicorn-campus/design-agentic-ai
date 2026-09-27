"""CLI 표현 계층과 조립 경계 시험."""

from contextlib import redirect_stdout
from io import StringIO
import unittest

from app.application.models import LabResult
from app.presentation.cli import MODES, build_parser, main


class FakeApplication:
    def __init__(self) -> None:
        self.calls = []

    def execute(self, example, request):
        self.calls.append((example, request))
        return LabResult({"ok": True})


class FailingApplication:
    def execute(self, _example, _request):
        raise RuntimeError("DB 연결 실패")


class PresentationTest(unittest.TestCase):
    def test_cli_delegates_one_request_to_application(self) -> None:
        application = FakeApplication()
        with redirect_stdout(StringIO()) as output:
            code = main(
                argv=["--mode", "schema", "--segment", "3"],
                application_factory=lambda: application,
            )

        self.assertEqual(0, code)
        self.assertEqual("schema", application.calls[0][0])
        self.assertEqual("M-3001", application.calls[0][1].member_id)
        self.assertIn('"ok": true', output.getvalue())

    def test_reference_branch_is_absent_from_help(self) -> None:
        self.assertNotIn("reference", build_parser().format_help())

    def test_all_example_modes_are_available(self) -> None:
        self.assertEqual(
            {"schema", "products", "usage", "delinquency", "context", "first", "nl2sql", "ask"},
            set(MODES),
        )

    def test_runtime_error_is_reported_without_traceback(self) -> None:
        with redirect_stdout(StringIO()) as output:
            code = main(
                argv=["--mode", "schema"],
                application_factory=lambda: FailingApplication(),
            )

        self.assertEqual(1, code)
        self.assertIn("실행 중단: DB 연결 실패", output.getvalue())


if __name__ == "__main__":
    unittest.main()
