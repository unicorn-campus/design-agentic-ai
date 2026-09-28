from pathlib import Path

from app.infrastructure.sql_guard import validate_sql


PROMPT = Path(__file__).resolve().parents[1] / "app" / "prompts" / "search_plan.md"
AVERAGE_EXPRESSION = (
    "ROUND(SUM(approved_amount) * 1.0 / NULLIF(SUM(transaction_count), 0), 2)"
)


def test_transaction_average_prompt_uses_guard_compatible_decimal_division():
    prompt = PROMPT.read_text(encoding="utf-8")
    sql = f"SELECT {AVERAGE_EXPRESSION} AS average_approved_amount FROM monthly_usage LIMIT 1"

    assert AVERAGE_EXPRESSION in prompt
    assert "형변환을 추가하지 않음" in prompt
    assert validate_sql(sql) == sql
