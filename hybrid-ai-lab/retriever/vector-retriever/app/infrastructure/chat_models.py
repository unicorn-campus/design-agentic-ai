"""커넥터별 LangChain 채팅 모델을 설계 고정값대로 만들어 주는 공장임(C-01 ~ C-04).

하이퍼파라미터를 여기 상수로 묶어 둠 — 부르는 단계도, 게이트웨이도 값을 흔들 수 없게 함(설계 슬라이드 26·28·30·32).
재시도는 두 제공자 모두 0회로 고정함. SDK 기본값 2회가 커넥터 타임아웃을 몰래 2 ~ 3배로 늘리는 일을 막음.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq

# 커넥터ID — 오류·감사 로그가 어느 호출에서 났는지 가리키는 값임(설계 슬라이드 25)
C01 = "C-01"
C02 = "C-02"
C03 = "C-03"
C04 = "C-04"

DEFAULT_GROQ_MODEL = "openai/gpt-oss-120b"
DEFAULT_CLAUDE_MODEL = "claude-opus-5-5"

# C-03만 Claude를 씀. thinking 토큰도 이 상한 안에서 쓰이므로 설계 700으로 두면 응답이 잘림(설계 가정 4000)
DEFAULT_CLAUDE_MAX_TOKENS = 4000
DEFAULT_CLAUDE_EFFORT = "low"

# 서버측 거절 대체(fallbacks) — Opus 5.5가 안전 분류로 거절하면 같은 호출 안에서 대체 모델이 이어 받음
CLAUDE_FALLBACK_BETA = "server-side-fallback-2026-07-01"
CLAUDE_FALLBACK_MODE = "default"


@dataclass(frozen=True)
class GroqSpec:
    """Groq 커넥터 1개의 고정 하이퍼파라미터. 설계 슬라이드 26·28·32의 표를 그대로 옮긴 값임."""

    temperature: float
    max_completion_tokens: int
    seed: int


# C-04만 temperature 0.2임 — 문장을 생성하는 자리라서임(사실은 근거가 고정하므로 흔들려도 안전)
GROQ_SPECS: dict[str, GroqSpec] = {
    C01: GroqSpec(0.0, 700, 1001),
    C02: GroqSpec(0.0, 400, 1002),
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
    """Groq 커넥터(C-01·C-02·C-04) 1개가 쓸 채팅 모델을 설계 고정값으로 만듦.

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


def build_claude_chat(
    *,
    api_key: str,
    model: str = DEFAULT_CLAUDE_MODEL,
    effort: str = DEFAULT_CLAUDE_EFFORT,
    max_tokens: int = DEFAULT_CLAUDE_MAX_TOKENS,
    timeout: float,
    chat_factory: Callable[..., Any] | None = None,
    fallbacks: bool = True,
) -> BaseChatModel:
    """C-03(질문 변환)이 쓸 Claude 채팅 모델을 만듦.

    인자: api_key는 Anthropic 키(CLAUDE_API_KEY)임. 어디에도 기록하지 않음.
    인자: effort는 생각 깊이이며 지연을 낮추려고 low를 기본으로 둠(모델 기본값은 medium).
    인자: max_tokens는 생각 토큰까지 함께 쓰는 상한임. 작게 두면 JSON이 중간에 잘림.
    인자: fallbacks를 끄면 서버측 거절 대체를 붙이지 않음(대체가 막힌 환경용).
    반환값: 하이퍼파라미터가 고정된 BaseChatModel임.
    부수효과: 없음.
    왜 temperature·seed가 없나: Opus 5.5는 temperature·top_p·seed를 받으면 400으로 거절함. 생각을 끌 수도 없어
    effort만으로 깊이를 조절함(claude-api 스킬 기준). 그래서 '같은 질문엔 같은 답' 보장은 이 커넥터에 없음.
    """

    factory = chat_factory or ChatAnthropic
    options: dict[str, Any] = {
        "model": model,
        "api_key": api_key,
        "max_tokens": max_tokens,
        "max_retries": 0,
        "default_request_timeout": timeout,
        "output_config": {"effort": effort},
    }
    if fallbacks:
        # betas는 ChatAnthropic 정식 필드이고, fallbacks는 model_kwargs를 거쳐 요청 본문에 그대로 실림
        options["betas"] = [CLAUDE_FALLBACK_BETA]
        options["model_kwargs"] = {"fallbacks": CLAUDE_FALLBACK_MODE}
    return factory(**options)
