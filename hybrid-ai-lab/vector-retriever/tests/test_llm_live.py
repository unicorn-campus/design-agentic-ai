from __future__ import annotations

import os

import pytest

from app.application.state import AnswerDraft
from app.infrastructure.llm_client import LangChainLLMClient
from app.settings import load_settings


@pytest.mark.live_call
@pytest.mark.skipif(os.getenv("RUN_LIVE_LLM") != "1", reason="실제 LLM 호출은 명시 실행만 허용")
def test_live_structured_output() -> None:
    settings = load_settings()
    result = LangChainLLMClient(settings).complete_structured(
        "JSON 스키마를 정확히 따르는 한국어 답변 작성",
        "결론은 '확인됨', 주의사항은 빈 문자열, 근거는 빈 목록으로 답변",
        AnswerDraft,
        max_tokens=settings.LLM_MAX_TOKENS_ANSWER,
        max_attempts=1,
    )
    assert result.parsed is not None
    assert result.parsing_error is None
