"""회원과 기준일로 격리된 논리 읽기 모델 SQL."""


# NL2SQL은 아래 네 공개 CTE만 볼 수 있음. 밑줄로 시작하는 CTE는 저장소 내부 조립용이며
# SQL 검사기가 접근을 허용하지 않음.
LOGICAL_CTE_SQL = r"""
WITH
_request_scope AS (
    SELECT
        %(member_id)s::text AS member_id,
        %(base_date)s::date AS base_date,
        %(coverage_start)s::date AS coverage_start
),
customer_profile AS (
    SELECT m.join_date, m.age_band
    FROM public.member AS m
    JOIN _request_scope AS scope ON scope.member_id = m.member_id
    WHERE m.join_date <= scope.base_date
),
_customer_cards_internal AS (
    SELECT
        c.card_id,
        'CARD_' || lpad(
            row_number() OVER (ORDER BY c.card_id)::text,
            3,
            '0'
        ) AS card_ref,
        c.product_id,
        p.product_name,
        c.brand,
        c.issue_date,
        c.status AS current_status,
        p.effective_date AS product_effective_date,
        (p.effective_date <= scope.base_date) AS is_product_effective_on_base_date,
        fee.total_fee AS annual_fee
    FROM public.card AS c
    JOIN _request_scope AS scope ON scope.member_id = c.member_id
    JOIN public.product AS p ON p.product_id = c.product_id
    JOIN public.product_annual_fee AS fee
      ON fee.product_id = c.product_id AND fee.brand = c.brand
    WHERE c.issue_date <= scope.base_date
),
customer_cards AS (
    SELECT
        card_ref,
        product_id,
        product_name,
        brand,
        issue_date,
        current_status,
        product_effective_date,
        is_product_effective_on_base_date,
        annual_fee
    FROM _customer_cards_internal
),
_usage_months AS (
    SELECT month_start::date AS month_start
    FROM _request_scope AS scope
    CROSS JOIN LATERAL generate_series(
        greatest(
            date_trunc('month', scope.base_date) - INTERVAL '5 months',
            date_trunc('month', scope.coverage_start)
        ),
        date_trunc('month', scope.base_date),
        INTERVAL '1 month'
    ) AS month_start
),
monthly_usage AS (
    SELECT
        cards.card_ref,
        to_char(months.month_start, 'YYYY-MM') AS month,
        greatest(months.month_start, cards.issue_date)::date AS period_start,
        least(
            (months.month_start + INTERVAL '1 month - 1 day')::date,
            scope.base_date
        ) AS period_end,
        coalesce(sum(txn.amount), 0)::bigint AS approved_amount,
        count(txn.txn_id)::integer AS transaction_count
    FROM _customer_cards_internal AS cards
    CROSS JOIN _request_scope AS scope
    CROSS JOIN _usage_months AS months
    LEFT JOIN public.card_txn AS txn
      ON txn.card_id = cards.card_id
     AND txn.approval_code = 'APPROVED'
     AND txn.txn_date >= greatest(months.month_start, cards.issue_date)::date
     AND txn.txn_date <= least(
         (months.month_start + INTERVAL '1 month - 1 day')::date,
         scope.base_date
     )
    WHERE cards.issue_date <= least(
        (months.month_start + INTERVAL '1 month - 1 day')::date,
        scope.base_date
    )
    GROUP BY cards.card_ref, months.month_start, cards.issue_date, scope.base_date
),
customer_delinquency AS (
    SELECT
        delinquency.base_month,
        (
            to_date(delinquency.base_month || '-01', 'YYYY-MM-DD')
            + INTERVAL '1 month - 1 day'
        )::date AS as_of_date,
        delinquency.overdue_amount,
        delinquency.overdue_days,
        delinquency.overdue_count_12m
    FROM public.delinquency AS delinquency
    JOIN _request_scope AS scope ON scope.member_id = delinquency.member_id
    WHERE (
        to_date(delinquency.base_month || '-01', 'YYYY-MM-DD')
        + INTERVAL '1 month - 1 day'
    )::date <= scope.base_date
    ORDER BY delinquency.base_month DESC
    LIMIT 1
)
"""


PROFILE_SELECT = "SELECT join_date, age_band FROM customer_profile"

CARDS_SELECT = """
SELECT
    card_id,
    card_ref,
    product_id,
    product_name,
    brand,
    issue_date,
    current_status,
    product_effective_date,
    is_product_effective_on_base_date,
    annual_fee
FROM _customer_cards_internal
ORDER BY card_ref
"""

USAGE_SELECT = """
SELECT card_ref, month, period_start, period_end, approved_amount, transaction_count
FROM monthly_usage
ORDER BY month, card_ref
"""

DELINQUENCY_SELECT = """
SELECT base_month, as_of_date, overdue_amount, overdue_days, overdue_count_12m
FROM customer_delinquency
"""

SEARCH_METADATA_SELECT = """
SELECT
    EXISTS (
        SELECT 1
        FROM customer_cards
        WHERE is_product_effective_on_base_date = false
    ) AS has_future_product,
    (SELECT max(as_of_date) FROM customer_delinquency) AS delinquency_as_of_date
"""


def scoped_query(select_sql: str) -> str:
    """고정 CTE 뒤에 저장소 내부 SELECT를 결합함."""

    return f"{LOGICAL_CTE_SQL}\n{select_sql.strip()}"


def guarded_query(validated_sql: str) -> str:
    """검증된 논리 SQL을 CTE 범위 안에 두고 저장소 상한 101행을 적용함."""

    # psycopg의 pyformat 파서가 사용자 SQL의 LIKE '%'와 modulo %를 바인딩 표기로
    # 오해하지 않게 사용자 SQL 구간의 퍼센트만 이스케이프함. 실행 SQL 의미는 같음.
    escaped_sql = validated_sql.replace("%", "%%")
    return (
        f"{LOGICAL_CTE_SQL}\n"
        "SELECT * FROM (\n"
        f"{escaped_sql}\n"
        ") AS guarded_result\n"
        "LIMIT 101"
    )
