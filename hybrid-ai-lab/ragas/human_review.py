"""사람 검토표를 내보내거나(export) 사람 판정과 LLM 판정의 일치도를 계산함(agree)."""

from app.presentation.cli import run_with

if __name__ == "__main__":
    raise SystemExit(run_with(["review"]))
