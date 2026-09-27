"""검토된 읽기 전용 SQL을 응용 포트에 맞추는 조회 어댑터."""

from ..domain.customer import fill_months


PRODUCTS_SQL = """
SELECT p.product_name, f.total_fee AS annual_fee, c.issue_date, c.status
FROM card AS c
JOIN product AS p ON p.product_id = c.product_id
JOIN product_annual_fee AS f
  ON f.product_id = c.product_id AND f.brand = c.brand
WHERE c.member_id = %(member_id)s AND c.status = 'ACTIVE'
  AND c.issue_date <= %(base_date)s::date
ORDER BY c.issue_date DESC, c.card_id
LIMIT 20
"""

USAGE_SQL = """
SELECT to_char(t.txn_date, 'YYYY-MM') AS month,
       SUM(t.amount) AS total_amount
FROM card_txn AS t
JOIN card AS c ON t.card_id = c.card_id
WHERE c.member_id = %(member_id)s
  AND t.txn_date >= date_trunc('month', %(base_date)s::date) - INTERVAL '5 months'
  AND t.txn_date < %(base_date)s::date + INTERVAL '1 day'
  AND t.approval_code = 'APPROVED'
GROUP BY month
ORDER BY month ASC
LIMIT 12
"""

DELINQUENCY_SQL = """
SELECT d.base_month, d.overdue_count_12m, d.overdue_days, d.overdue_amount
FROM delinquency AS d
WHERE d.member_id = %(member_id)s
  AND d.base_month <= %(base_month)s
ORDER BY d.base_month DESC
LIMIT 1
"""


def query_products(repository, member_id: str, base_date: str) -> list[dict]:
    return repository.rows(PRODUCTS_SQL, {"member_id": member_id, "base_date": base_date})


def query_usage(repository, member_id: str, base_date: str) -> list[dict]:
    rows = repository.rows(USAGE_SQL, {"member_id": member_id, "base_date": base_date})
    return fill_months(rows, base_date)


def query_delinquency(repository, member_id: str, base_date: str) -> dict | None:
    rows = repository.rows(
        DELINQUENCY_SQL,
        {"member_id": member_id, "base_month": base_date[:7]},
    )
    return rows[0] if rows else None

