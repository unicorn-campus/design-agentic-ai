"""eval-set.md를 검증한 뒤 eval-set.json으로 저장함(검증 실패면 저장하지 않음)."""

from app.presentation.cli import run_with

if __name__ == "__main__":
    raise SystemExit(run_with(["build"]))
