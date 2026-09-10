"""작성: (1) 조인 키 (2) 월초에서 5개월 전 (3) 기준일 다음 날 (4) 승인 코드 (5) 월 그룹."""
try:
    from . import _bootstrap
except ImportError:
    import _bootstrap
from src.common.database import require_complete, fill_months

SQL = '''
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
LIMIT 12;
'''

def query(repository, member_id, base_date):
    require_complete(SQL, '04_query_usage_ref.py')
    rows = repository.rows(SQL, {'member_id': member_id, 'base_date': base_date})
    return fill_months(rows, base_date)

if __name__ == '__main__':
    from src.nl2sql.presentation import run
    raise SystemExit(run('usage', reference=True))
