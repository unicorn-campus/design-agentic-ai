"""고객 조회에 공통으로 적용하는 순수 도메인 규칙."""

from datetime import date


MIN_BASE_DATE = date(2026, 3, 1)
MAX_BASE_DATE = date(2026, 8, 31)


def validate_customer(base_date: str, member: dict | None) -> dict:
    """기준일 범위와 고객의 조회 가능 여부를 검증함."""

    parsed = date.fromisoformat(base_date)
    if not MIN_BASE_DATE <= parsed <= MAX_BASE_DATE:
        raise ValueError("실습 조회 기준일은 2026-03-01 ~ 2026-08-31 범위임")
    if member is None:
        raise ValueError("존재하지 않는 합성 고객 ID임")
    join_date = member["join_date"]
    if isinstance(join_date, str):
        join_date = date.fromisoformat(join_date)
    if join_date > parsed:
        raise ValueError("가입 전 기준일로 조회할 수 없음")
    return member


def fill_months(rows: list[dict], base_date: str) -> list[dict]:
    """최근 6개월 중 거래가 없는 월을 0원으로 보충함."""

    end = date.fromisoformat(base_date)
    index = end.year * 12 + end.month - 1
    amounts = {row["month"]: row["total_amount"] for row in rows}
    months = [f"{month // 12:04d}-{month % 12 + 1:02d}" for month in range(index - 5, index + 1)]
    return [{"month": month, "total_amount": amounts.get(month, 0)} for month in months]
