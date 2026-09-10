"""표현 계층(CLI)과 의존성 조립. 업무 처리는 CustomerService에 위임."""
import argparse
import json
from html import escape
import psycopg
from src.common.config import ROOT, load_settings
from src.nl2sql.application.customer_service import CustomerService
from src.common.database import PostgresRepository
from src.common.llm_client import ClaudeGateway

REPRESENTATIVES = {1: 'M-1001', 2: 'M-1042', 3: 'M-3001',
                   4: 'M-4001', 5: 'M-5001', 6: 'M-6001'}


def run(example: str, reference=False) -> int:
    parser = argparse.ArgumentParser(description='S2.2 정형 데이터 실습 정답 예제')
    parser.add_argument('--segment', type=int, choices=range(1, 7), default=2)
    parser.add_argument('--member-id')
    parser.add_argument('--base-date', default='2026-08-31')
    parser.add_argument('--question', default='이 고객의 보유 상품, 최근 사용 추이와 연체 지표를 요약해 주세요.')
    parser.add_argument('--offline', action='store_true', help='Claude 호출 없이 데이터와 프롬프트 확인')
    parser.add_argument('--reference', action='store_true', help='강사용 정답 구현 사용')
    args = parser.parse_args()
    try:
        settings = load_settings()
        repository = PostgresRepository(settings.db_dsn, settings.db_password)
        print('PostgreSQL 공통 RDB 사용: public 스키마, 읽기 전용 연결')
        service = CustomerService(repository, reference=reference or args.reference)
        member_id = args.member_id or REPRESENTATIVES[args.segment]
        if example == 'schema':
            output = repository.schema()
        elif example in ('products', 'usage', 'delinquency'):
            method = {'products': service.products, 'usage': service.monthly_usage,
                      'delinquency': service.delinquency}[example]
            output = method(member_id, args.base_date)
        elif example == 'context':
            print(service.context(member_id, args.base_date))
            return 0
        elif example == 'first':
            system = '교육용 질문에 한국어로 간결하게 답함. 제공되지 않은 고객 데이터는 모른다고 답함.'
            question = '카드 연회비란 무엇인가요?' if args.question == parser.get_default('question') else args.question
            output = (
                {'system': system, 'question': question}
                if args.offline else ClaudeGateway(settings).ask(system, question)
            )
        elif example == 'nl2sql':
            # 임의 생성 SQL은 실행하지 않음. 실행 예제는 별도의 고정 SQL 세 본임.
            system = ('교육용 PostgreSQL SELECT 문 한 개만 제안함. 실행하지 않음. '
                      '허용 테이블 card(card_id,member_id,product_id,brand,issue_date,status), '
                      'product(product_id,product_name), '
                      'product_annual_fee(product_id,brand,total_fee). '
                      'SELECT * 금지, %(member_id)s 바인딩, ACTIVE 카드만, LIMIT 20 필수.')
            question = ('고객 %(member_id)s의 보유 상품명·연회비·발급일·상태를 '
                        '조회하는 SQL을 작성해 주세요.')
            print('검토용 SQL만 출력함. DB에 실행하지 않음.')
            output = (
                {'system': system, 'question': question}
                if args.offline else ClaudeGateway(settings).ask(system, question)
            )
        elif example == 'ask':
            context = service.context(member_id, args.base_date)
            system = (ROOT / 'src/nl2sql/prompts/05_ask_with_context.md').read_text(encoding='utf-8')
            user = f'<question>{escape(args.question)}</question>\n<context>{escape(context)}</context>'
            output = {'system': system, 'user': user} if args.offline else ClaudeGateway(settings).ask(system, user)
        else:
            raise ValueError('알 수 없는 예제임')
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if isinstance(output, dict) and output.get('stop_reason') == 'max_tokens':
            print('응답이 출력 토큰 상한에 도달함. 완성 답변으로 사용하지 말고 질문 길이 확인 필요.')
            return 2
        return 0
    except (ValueError, RuntimeError, OSError, psycopg.Error) as error:
        print(f'실행 중단: {error}')
        return 1
