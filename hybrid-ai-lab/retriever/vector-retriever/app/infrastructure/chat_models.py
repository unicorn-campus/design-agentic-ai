"""커넥터별 LangChain 채팅 모델을 설계 고정값대로 만들어 주는 공장임(C-01 ~ C-04).

하이퍼파라미터를 여기 상수로 묶어 둠 — 부르는 단계도, 게이트웨이도 값을 흔들 수 없게 함(설계 슬라이드 26·28·30·32).
재시도는 0회로 고정함. SDK 기본값 2회가 커넥터 타임아웃을 몰래 2 ~ 3배로 늘리는 일을 막음.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq

# 커넥터ID — 오류·감사 로그가 어느 호출에서 났는지 가리키는 값임(설계 슬라이드 25)
C01 = "C-01"
C02 = "C-02"
C03 = "C-03"
C04 = "C-04"

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"


@dataclass(frozen=True)
class GroqSpec:
    """Groq 커넥터 1개의 고정 하이퍼파라미터. 설계 슬라이드 26·28·30·32의 표를 그대로 옮긴 값임."""

    temperature: float
    max_completion_tokens: int
    seed: int


# C-04만 temperature 0.2임 — 문장을 생성하는 자리라서임(사실은 근거가 고정하므로 흔들려도 안전)
GROQ_SPECS: dict[str, GroqSpec] = {
    C01: GroqSpec(0.0, 700, 1001),
    C02: GroqSpec(0.0, 400, 1002),
    C03: GroqSpec(0.0, 700, 1003),
    C04: GroqSpec(0.2, 1800, 1004),
}


def build_groq_chat(
    connector_id: str,
    *,
    api_key: str,
    model: str = DEFAULT_GROQ_MODEL,
    reasoning_effort: str = "low",
    timeout: float,
    chat_factory: Callable[..., Any] | None = None,
) -> BaseChatModel:
    """커넥터(C-01 ~ C-04) 1개가 쓸 채팅 모델을 설계 고정값으로 만듦.

    인자: connector_id는 GROQ_SPECS에 있는 값이어야 함. api_key는 비밀값 저장소에서 온 값이며 어디에도 기록하지 않음.
    인자: timeout은 SDK의 단계별 제한 시간임. 호출 전체 마감 시간은 게이트웨이가 따로 검(설계 ③).
    인자: chat_factory는 시험에서 가짜 모델을 끼우는 자리임(기본값은 langchain_groq.ChatGroq).
    반환값: 하이퍼파라미터가 고정된 BaseChatModel임.
    예외: 모르는 커넥터ID면 ValueError를 올림(설정 실수를 서버 시작 때 바로 드러나게 함).
    부수효과: 없음 — 만드는 시점에는 외부 호출을 하지 않음.
    왜 model_kwargs인가: top_p·seed·max_completion_tokens·include_reasoning은 ChatGroq의 정식 필드가 아니라
    그대로 요청 본문에 실어야 함. max_tokens 필드를 쓰면 폐기 예정인 옛 이름으로 나감(설계 [NOTES]).
    """

    spec = GROQ_SPECS.get(connector_id)
    if spec is None:
        raise ValueError(f"Groq 커넥터가 아님: {connector_id}")
    factory = chat_factory or ChatGroq
    return factory(
        model=model,
        api_key=api_key,
        temperature=spec.temperature,
        reasoning_effort=reasoning_effort,
        request_timeout=timeout,
        max_retries=0,
        model_kwargs={
            "top_p": 1,
            "max_completion_tokens": spec.max_completion_tokens,
            "seed": spec.seed,
            # 설계서의 reasoning_format=hidden은 gpt-oss가 지원하지 않아 include_reasoning=False로 대신함
            # (사용자 결정). 추론 문장을 응답에서 빼 JSON 본문만 받는 효과는 같음
            "include_reasoning": False,
        },
    )

