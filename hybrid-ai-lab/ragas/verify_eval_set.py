"""eval-set.json을 사용 중 색인 세대로 다시 검증함(검증 5검사)."""

from app.presentation.cli import run_with

if __name__ == "__main__":
    raise SystemExit(run_with(["verify"]))
