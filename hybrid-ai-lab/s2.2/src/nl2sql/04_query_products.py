"""완성 예제: 활성 카드의 상품 조회."""
try:
    from . import _bootstrap
except ImportError:
    import _bootstrap
from src.common.database import require_complete

SQL = '''
SELECT p.product_name, f.total_fee AS annual_fee, c.issue_date, c.status
FROM card AS c
JOIN product AS p ON p.product_id = c.product_id
JOIN product_annual_fee AS f
  ON f.product_id = c.product_id AND f.brand = c.brand
WHERE c.member_id = %(member_id)s AND c.status = 'ACTIVE'
  AND c.issue_date <= %(base_date)s::date
ORDER BY c.issue_date DESC, c.card_id
LIMIT 20
'''

def query(repository, member_id, base_date):
    require_complete(SQL, '04_query_products.py')
    rows = repository.rows(SQL, {'member_id': member_id, 'base_date': base_date})
    return rows

if __name__ == '__main__':
    from src.nl2sql.presentation import run
    raise SystemExit(run('products'))
