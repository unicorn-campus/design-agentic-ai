"""슬라이드 21: 저장소의 Claude 설정을 사용하는 최소 LLM 어댑터."""

from pathlib import Path
import os

import anthropic
from dotenv import dotenv_values

BASE = Path(__file__).resolve().parents[1]


def _config_value(name: str, default: str = "") -> str:
    values = {
        **dotenv_values(BASE.parent / ".env"),
        **dotenv_values(BASE / ".env"),
        **os.environ,
    }
    return values.get(name) or default


def ask_llm(
    system: str,
    user: str,
    max_tokens: int = 1800,
    temperature: float | None = None,
) -> dict:
    """Claude Messages API를 한 번 호출하고 본문과 사용량을 반환함."""
    api_key = _config_value("CLAUDE_API_KEY")
    model = _config_value("CLAUDE_MODEL", "claude-sonnet-5")
    if not api_key:
        raise ValueError("루트 또는 s3.2/.env에 CLAUDE_API_KEY를 설정해야 함")
    try:
        with anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=1) as client:
            request = {
                "model": model,
                "max_tokens": max_tokens,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            }
            if model.startswith("claude-fable"):
                # Fable 5.x는 adaptive thinking만 지원함.
                request["thinking"] = {"type": "adaptive"}
                request["output_config"] = {
                    "effort": _config_value("CLAUDE_EFFORT", "low")
                }
            else:
                request["thinking"] = {"type": "disabled"}
            # 환경 변수로만 선택 적용해 기존 실습 명령과 호환함.
            configured_temperature = _config_value("CLAUDE_TEMPERATURE")
            if temperature is None and configured_temperature:
                temperature = float(configured_temperature)
            if temperature is not None:
                request["temperature"] = temperature
            message = client.messages.create(**request)
    except anthropic.APIStatusError as error:
        raise RuntimeError(
            f"Claude API 호출 실패(HTTP {error.status_code}). 키 권한·모델 접근·잔액 확인 필요"
        ) from None
    except anthropic.APIConnectionError:
        raise RuntimeError("Claude API 연결 실패. 네트워크·프록시 확인 필요") from None
    return {
        "content": "".join(block.text for block in message.content if block.type == "text"),
        "stop_reason": message.stop_reason,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
        "model": message.model,
    }
