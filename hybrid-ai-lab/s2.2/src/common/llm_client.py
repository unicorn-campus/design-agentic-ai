"""외부 연동 계층: CLAUDE_API_KEY를 명시적으로 SDK에 전달."""
import anthropic
from src.common.config import Settings


class ClaudeGateway:
    def __init__(self, settings: Settings):
        self.settings = settings

    def ask(self, system: str, user: str, max_tokens: int = 1800) -> dict:
        if not self.settings.api_key:
            raise ValueError('저장소 .env에 CLAUDE_API_KEY를 설정해야 함')
        try:
            with anthropic.Anthropic(api_key=self.settings.api_key,
                                     timeout=60.0, max_retries=1) as client:
                message = client.messages.create(
                    model=self.settings.model, max_tokens=max_tokens,
                    thinking={'type': 'disabled'}, system=system,
                    messages=[{'role': 'user', 'content': user}])
        except anthropic.APIStatusError as error:
            raise RuntimeError(f'Claude API 호출 실패(HTTP {error.status_code}). 키 권한·모델 접근·잔액 확인 필요') from None
        except anthropic.APIConnectionError:
            raise RuntimeError('Claude API 연결 실패. 네트워크·프록시 확인 필요') from None
        return {'role': message.role,
                'content': ''.join(block.text for block in message.content if block.type == 'text'),
                'stop_reason': message.stop_reason,
                'usage': {'input_tokens': message.usage.input_tokens,
                          'output_tokens': message.usage.output_tokens},
                'model': message.model}
