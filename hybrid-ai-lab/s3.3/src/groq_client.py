"""Groq LPU의 OpenAI 호환 API를 호출하는 최소 어댑터."""

from __future__ import annotations

import os
from pathlib import Path
from time import perf_counter

import httpx
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[2]
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"


def _config_value(name: str, default: str = "") -> str:
    """루트 .env보다 실행 환경 변수를 우선하여 설정값을 읽음."""
    values = {
        **dotenv_values(ROOT / ".env"),
        **os.environ,
    }
    return values.get(name) or default


def ask_groq(
    system: str,
    user: str,
    max_tokens: int = 4000,
    temperature: float | None = None,
) -> dict:
    """Groq에서 gpt-oss-120b를 호출하고 본문·사용량·지연을 반환함."""
    api_key = _config_value("GROQ_API_KEY")
    model = _config_value("GROQ_MODEL", "openai/gpt-oss-120b")
    if not api_key:
        raise ValueError("루트 .env에 GROQ_API_KEY를 설정해야 함")

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_completion_tokens": max_tokens,
        "reasoning_effort": _config_value("GROQ_REASONING_EFFORT", "medium"),
        "response_format": {"type": "json_object"},
    }
    if temperature is not None:
        payload["temperature"] = temperature

    started = perf_counter()
    try:
        response = httpx.post(
            GROQ_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60.0,
        )
        response.raise_for_status()
    except httpx.HTTPStatusError as error:
        status = error.response.status_code
        raise RuntimeError(
            f"Groq API 호출 실패(HTTP {status}). 키 권한·모델 접근·잔액 확인 필요"
        ) from None
    except httpx.HTTPError:
        raise RuntimeError("Groq API 연결 실패. 네트워크·프록시 확인 필요") from None

    elapsed_ms = (perf_counter() - started) * 1000
    body = response.json()
    choice = body["choices"][0]
    usage = body.get("usage", {})
    return {
        "content": choice["message"].get("content", ""),
        "stop_reason": choice.get("finish_reason"),
        "usage": {
            "input_tokens": usage.get("prompt_tokens", 0),
            "output_tokens": usage.get("completion_tokens", 0),
        },
        "model": body.get("model", model),
        "elapsed_ms": round(elapsed_ms, 1),
    }
