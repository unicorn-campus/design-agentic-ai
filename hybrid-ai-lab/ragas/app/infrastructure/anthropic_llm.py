"""Claude 평가자 — ragas가 요구하는 구조화 출력 LLM 형식을 Anthropic SDK의 messages.parse로 구현함."""

from __future__ import annotations

import asyncio
from typing import Any, TypeVar

from pydantic import BaseModel
from ragas.llms.base import InstructorBaseRagasLLM

ModelT = TypeVar("ModelT", bound=BaseModel)
FALLBACK_BETA = "server-side-fallback-2026-07-01"  # fallbacks="default"와 짝인 헤더(배열 꼴은 -06-01)


class ClaudeRefusalError(RuntimeError):
    """평가자(와 대체 모델)가 안전 분류로 응답을 거절함 — 그 칸은 failed_scores에 기록됨."""


class AnthropicParseLLM(InstructorBaseRagasLLM):
    """ragas 지표가 부르는 generate · agenerate를 Claude 구조화 출력(output_format)으로 처리함.

    ragas llm_factory의 Anthropic 경로(instructor)는 특정 도구 강제 호출로 JSON을 받는데, Claude Opus 5.5는
    강제 도구 호출과 temperature · top_p를 모두 400으로 거부함 — 그래서 SDK의 messages.parse를 직접 씀.
    판정 흔들림은 temperature 대신 effort(기본 medium을 명시)와 반복 채점(--repeat)으로 다룸.
    """

    def __init__(self, client: Any, model: str, *, max_tokens: int, effort: str = "medium"):
        self.client, self.model, self.max_tokens, self.effort = client, model, max_tokens, effort

    async def agenerate(self, prompt: str, response_model: type[ModelT]) -> ModelT:
        """프롬프트 하나를 보내 response_model 모양으로 검증된 결과를 돌려줌.

        방법: 안전 분류가 거절하면 서버가 대체 모델로 다시 돌리도록 fallbacks="default"를 켬(대체까지 거절하면 예외).
        예외: 끝내 거절이면 ClaudeRefusalError, 출력 길이 상한에 걸려 구조가 끊기면 ValueError.
        부수효과: Claude API 호출 1회(요금 발생).
        """

        response = await self.client.beta.messages.parse(
            model=self.model,
            max_tokens=self.max_tokens,
            messages=[{"role": "user", "content": prompt}],
            output_format=response_model,
            output_config={"effort": self.effort},
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        if response.stop_reason == "refusal":
            category = getattr(response.stop_details, "category", None) if response.stop_details else None
            raise ClaudeRefusalError(f"평가자가 거절함(분류: {category})")
        if response.stop_reason == "max_tokens" or response.parsed_output is None:
            raise ValueError(f"구조화 출력이 완성되지 않음(stop_reason={response.stop_reason})")
        return response.parsed_output

    def generate(self, prompt: str, response_model: type[ModelT]) -> ModelT:
        """동기 호출 — ragas 지표의 sync 경로용. 실행 중인 이벤트 루프 안에서는 agenerate를 써야 함."""

        return asyncio.run(self.agenerate(prompt, response_model))
