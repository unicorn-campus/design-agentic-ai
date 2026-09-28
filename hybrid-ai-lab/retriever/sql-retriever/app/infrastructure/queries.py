"""회원·기준일 세션 범위로 격리된 논리 읽기 모델 조회문.

논리 테이블은 DB의 `app` 스키마 뷰이며, 정의는 `rdb/init/04_views_rls.sql`에 있음.
회원 격리는 원본 테이블의 행 수준 보안(RLS)이 담당하므로 이 모듈은 어떤 회원 조건도
SQL에 넣지 않음. 기준일·6개월 창은 뷰가 세션 변수를 읽어 적용함.

조회 전에 트랜잭션 안에서 SCOPE_SETTINGS 세 값을 지정해야 함.
지정하지 않으면 모든 뷰가 0행을 반환함(기본 거부).
"""


# 트랜잭션마다 set_config(..., true)로 지정하는 세션 변수.
MEMBER_SETTING = "app.member_id"
BASE_DATE_SETTING = "app.base_date"
COVERAGE_START_SETTING = "app.coverage_start"
SCOPE_SETTINGS = (MEMBER_SETTING, BASE_DATE_SETTING, COVERAGE_START_SETTING)

# NL2SQL이 볼 수 있는 논리 테이블. 검색 경로가 app을 가리키므로 모델은 스키마 없이 씀.
LOGICAL_SCHEMA_NAME = "app"
LOGICAL_VIEWS = (
    "customer_profile",
    "customer_cards",
    "monthly_usage",
    "customer_delinquency",
)


# 회원 존재·가입일 확인용. 기준일 필터가 없어 "없는 회원"과 "가입 전 기준일"을 구분함.
MEMBER_SELECT = """
SELECT member_id, join_date, age_band
FROM app_internal.member_basic
LIMIT 1
"""

# 회원과 무관한 메타데이터이므로 RLS 대상이 아님.
METADATA_SELECT = """
SELECT key, value
FROM public.lab_metadata
WHERE key IN ('base_date', 'txn_period')
"""

PROFILE_SELECT = "SELECT join_date, age_band FROM app.customer_profile"

# 원본 card_id가 필요한 고정 조회는 NL2SQL에 열지 않은 app_internal을 씀.
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
FROM app_internal.customer_cards_full
ORDER BY card_ref
"""

USAGE_SELECT = """
SELECT card_ref, month, period_start, period_end, approved_amount, transaction_count
FROM app.monthly_usage
ORDER BY month, card_ref
"""

DELINQUENCY_SELECT = """
SELECT base_month, as_of_date, overdue_amount, overdue_days, overdue_count_12m
FROM app.customer_delinquency
"""

SEARCH_METADATA_SELECT = """
SELECT
    EXISTS (
        SELECT 1
        FROM app.customer_cards
        WHERE is_product_effective_on_base_date = false
    ) AS has_future_product,
    (SELECT max(as_of_date) FROM app.customer_delinquency) AS delinquency_as_of_date
"""


def guarded_query(validated_sql: str) -> str:
    """검증된 논리 SQL에 저장소 상한 101행을 적용함.

    회원·기준일 조건을 덧붙이지 않음. 뷰와 RLS가 이미 범위를 좁혀 두었고,
    같은 조건을 두 곳에 두면 한쪽만 고쳤을 때 어긋나기 때문임.
    """

    return (
        "SELECT * FROM (\n"
        f"{validated_sql.strip()}\n"
        ") AS guarded_result\n"
        "LIMIT 101"
    )
