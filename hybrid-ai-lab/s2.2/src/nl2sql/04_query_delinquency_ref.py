"""작성: (1) 회원 ID 자리표시자 (2) 기준월 내림차순."""
try:
    from . import _bootstrap
except ImportError:
    import _bootstrap
from src.common.database import require_complete

SQL = '''
SELECT d.base_month, d.overdue_count_12m, d.overdue_days, d.overdue_amount
FROM delinquency AS d
WHERE d.member_id = %(member_id)s
  AND d.base_month <= %(base_month)s
ORDER BY d.base_month DESC
LIMIT 1;
'''

def query(repository, member_id, base_date):
    require_complete(SQL, '04_query_delinquency_ref.py')
    rows = repository.rows(SQL, {'member_id': member_id, 'base_month': base_date[:7]})
    return rows[0] if rows else None

if __name__ == '__main__':
    from src.nl2sql.presentation import run
    raise SystemExit(run('delinquency', reference=True))
