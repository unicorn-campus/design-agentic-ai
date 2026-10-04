"""RAGAS 0.4 지표를 평가자 LLM(llm_factory)과 KURE-v2 임베딩으로 채점하는 어댑터."""

from __future__ import annotations

from typing import Any, Callable

from app.application.ports import JudgePort


class RagasJudge(JudgePort):
    """ragas.metrics.collections 지표 6개를 들고 지표 이름으로 골라 채점함.

    평가자 LLM은 ragas llm_factory로 만듦 — 0.4의 지표 묶음은 Instructor 형식 LLM만 받고 LangChain 래퍼는 거부함
    (설치 소스 metrics/collections/base.py에서 확인). 지표 객체는 처음 쓸 때 한 번만 만듦.
    """

    def __init__(self, provider: str, llm_builder: Callable[[], Any], embeddings_builder: Callable[[], Any],
                 model: str, embedding_model: str):
        self.provider, self.model, self.embedding_model = provider, model, embedding_model
        self._llm_builder, self._embeddings_builder = llm_builder, embeddings_builder
        self._metrics: dict[str, Any] | None = None

    def describe(self) -> dict[str, str]:
        """같은 조건 확인용 평가자 정보."""

        return {"provider": self.provider, "model": self.model, "embedding_model": self.embedding_model}

    def _build(self) -> dict[str, Any]:
        """지표 객체 6개를 만듦. ContextPrecision은 정답이 있는 평가셋이라 WithReference를 씀."""

        from ragas.metrics.collections import (AnswerRelevancy, ContextEntityRecall, ContextPrecisionWithReference,
                                               ContextRecall, FactualCorrectness, Faithfulness)

        llm = self._llm_builder()
        return {
            "context_precision": ContextPrecisionWithReference(llm=llm),
            "context_recall": ContextRecall(llm=llm),
            "entity_recall": ContextEntityRecall(llm=llm),
            "faithfulness": Faithfulness(llm=llm),
            # AnswerRelevancy만 임베딩을 씀(역질문과 원래 질문의 코사인 유사도) — 첫 사용 때 KURE-v2를 올림
            "answer_relevancy": AnswerRelevancy(llm=llm, embeddings=self._embeddings_builder()),
            "factual_correctness": FactualCorrectness(llm=llm),
        }

    async def score(self, metric: str, fields: dict[str, Any]) -> tuple[float, str | None]:
        """지표 하나를 채점함. 반환값: (MetricResult.value, MetricResult.reason)."""

        if self._metrics is None:
            self._metrics = self._build()
        result = await self._metrics[metric].ascore(**fields)
        return float(result.value), getattr(result, "reason", None)


def build_llm(provider: str, *, settings: Any) -> tuple[Callable[[], Any], str]:
    """평가자별 LLM 생성 함수와 모델 이름을 돌려줌.

    local: Ollama의 OpenAI 호환 주소. reasoning_effort="none"으로 Qwen3.5의 사고를 끔 — 켜면 빈 답이 나옴(실측).
    groq: OpenAI 호환 주소. anthropic: Anthropic SDK(instructor가 도구 호출로 구조화 출력).
    temperature 0 — 같은 입력에 같은 판정이 나오게 함(로컬 평가자는 반복해도 같은 값).
    예외: API 평가자의 비밀키가 없으면 ValueError.
    """

    from ragas.llms import llm_factory

    if provider == "local":
        def make() -> Any:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(base_url=settings.ollama_base_url, api_key="ollama")  # Ollama는 키를 검사하지 않음
            return llm_factory(settings.local_model, client=client, temperature=0, reasoning_effort="none",
                               max_tokens=settings.ragas_max_tokens)
        return make, settings.local_model
    if provider == "groq":
        if not settings.groq_api_key:
            raise ValueError("GROQ_API_KEY가 없음")

        def make() -> Any:
            from openai import AsyncOpenAI

            client = AsyncOpenAI(base_url=settings.groq_base_url, api_key=settings.groq_api_key)
            return llm_factory(settings.groq_model, client=client, temperature=0, max_tokens=settings.ragas_max_tokens)
        return make, settings.groq_model
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("ANTHROPIC_API_KEY(또는 CLAUDE_API_KEY)가 없음")

        def make() -> Any:
            from anthropic import AsyncAnthropic

            from .anthropic_llm import AnthropicParseLLM

            # llm_factory(provider="anthropic")는 강제 도구 호출 · temperature를 보내 Claude Opus 5.5에서 400이 남(실측)
            # 사고(thinking)는 끌 수 없는 모델이라 출력 상한을 넉넉히 둠 — 상한에 걸리면 구조화 출력이 끊김
            client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            return AnthropicParseLLM(client, settings.anthropic_model, max_tokens=max(settings.ragas_max_tokens, 16000))
        return make, settings.anthropic_model
    raise ValueError(f"알 수 없는 평가자: {provider}")


def build_embeddings(settings: Any) -> Callable[[], Any]:
    """KURE-v2 임베딩 생성 함수 — 색인과 같은 모델 · revision을 로컬 캐시에서만 읽음(실행 중 내려받지 않음)."""

    def make() -> Any:
        from ragas.embeddings import HuggingFaceEmbeddings

        device = settings.embed_device
        if device == "auto":
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        return HuggingFaceEmbeddings(model=settings.embed_model, device=device, revision=settings.embed_revision,
                                     local_files_only=settings.hf_local_files_only)
    return make
