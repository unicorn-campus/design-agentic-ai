"""교육생 작성: 첫 블록을 참고하여 나머지 Context 블록 구현."""
try:
    from . import _bootstrap
except ImportError:
    import _bootstrap

def build_context(member_id: str, products: list[dict], monthly_usage: list[dict],
                  delinquency: dict | None, base_date: str) -> str:
    lines = [f'[고객 기본] 교육용 합성 가명ID: {member_id} · 기준일: {base_date}']
    # TODO: 보유 상품·월별 사용액·변화율·연체·미확인 항목 조립.
    # 금액 단위·출처·기준일 포함. None과 0 구분, 변화율 분모 0 처리.
    # 아래 예외를 작성한 본문과 return '\n'.join(lines)로 교체함.
    raise NotImplementedError('context_builder.py: Context 함수 본문을 작성해 주세요.')

if __name__ == '__main__':
    from src.nl2sql.presentation import run
    raise SystemExit(run('context'))
