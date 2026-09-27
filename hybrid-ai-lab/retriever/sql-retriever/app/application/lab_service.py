"""CLI 종류와 무관하게 실습 유스케이스를 실행하는 응용 서비스."""

from html import escape

from .customer_service import CustomerService
from .models import LabRequest, LabResult
from .ports import CustomerRepositoryPort, LLMPort


FIRST_SYSTEM = "교육용 질문에 한국어로 간결하게 답함. 제공되지 않은 고객 데이터는 모른다고 답함."
DEFAULT_QUESTION = "이 고객의 보유 상품, 최근 사용 추이와 연체 지표를 요약해 주세요."
NL2SQL_SYSTEM = (
    "교육용 PostgreSQL SELECT 문 한 개만 제안함. 실행하지 않음. "
    "허용 테이블 card(card_id,member_id,product_id,brand,issue_date,status), "
    "product(product_id,product_name), "
    "product_annual_fee(product_id,brand,total_fee). "
    "SELECT * 금지, %(member_id)s 바인딩, ACTIVE 카드만, LIMIT 20 필수."
)
NL2SQL_QUESTION = (
    "고객 %(member_id)s의 보유 상품명·연회비·발급일·상태를 조회하는 SQL을 작성해 주세요."
)


class LabService:
    def __init__(
        self,
        repository: CustomerRepositoryPort,
        llm: LLMPort,
        customers: CustomerService,
        answer_prompt: str,
    ) -> None:
        self.repository = repository
        self.llm = llm
        self.customers = customers
        self.answer_prompt = answer_prompt

    def execute(self, example: str, request: LabRequest) -> LabResult:
        notices: list[str] = []
        if example == "schema":
            payload = self.repository.schema()
        elif example in {"products", "usage", "delinquency"}:
            method = {
                "products": self.customers.products,
                "usage": self.customers.monthly_usage,
                "delinquency": self.customers.delinquency,
            }[example]
            payload = method(request.member_id, request.base_date)
        elif example == "context":
            payload = self.customers.context(request.member_id, request.base_date)
        elif example == "first":
            question = "카드 연회비란 무엇인가요?" if request.question == DEFAULT_QUESTION else request.question
            payload = self._ask(FIRST_SYSTEM, question, request.offline, "question")
        elif example == "nl2sql":
            notices.append("검토용 SQL만 출력함. DB에 실행하지 않음.")
            payload = self._ask(NL2SQL_SYSTEM, NL2SQL_QUESTION, request.offline, "question")
        elif example == "ask":
            context = self.customers.context(request.member_id, request.base_date)
            user = f"<question>{escape(request.question)}</question>\n<context>{escape(context)}</context>"
            payload = self._ask(self.answer_prompt, user, request.offline, "user")
        else:
            raise ValueError("알 수 없는 예제임")

        exit_code = 0
        if isinstance(payload, dict) and payload.get("stop_reason") == "max_tokens":
            notices.append("응답이 출력 토큰 상한에 도달함. 완성 답변으로 사용하지 말고 질문 길이 확인 필요.")
            exit_code = 2
        return LabResult(payload=payload, notices=tuple(notices), exit_code=exit_code)

    def _ask(self, system: str, user: str, offline: bool, input_name: str) -> dict:
        if offline:
            return {"system": system, input_name: user}
        return self.llm.ask(system, user)

