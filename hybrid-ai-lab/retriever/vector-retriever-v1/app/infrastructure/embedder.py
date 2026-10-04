"""질의가 들어올 때 HuggingFace 임베딩 모델을 적재하는 임베더 어댑터."""

from __future__ import annotations

from typing import Any

from ..application.ports import EmbedderPort


class LazyHuggingFaceEmbedder(EmbedderPort):
    """질의가 들어올 때까지 임베딩 모델 적재를 미룸."""

    # 목적: 지연 로딩할 임베딩 모델의 기본 정보를 준비함.
    # 작업: 모델 이름·서명·초기 차원을 저장하고 실제 모델 자리는 비워 둠.
    # 리턴값: 없음.
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.signature = f"sentence-transformers:{model_name}:prompt-policy-v2"
        self.dimension = 0
        self._model = None

    # 목적: 실제 임베딩 모델을 처음 필요할 때 한 번만 메모리에 적재함.
    # 작업: CPU용 정규화 임베딩 모델을 만들고 이후 호출에서 재사용하도록 저장함.
    # 리턴값: 현재 사용할 HuggingFace 임베딩 모델 객체임.
    def _load(self) -> Any:
        if self._model is None:
            from langchain_huggingface import HuggingFaceEmbeddings

            self._model = HuggingFaceEmbeddings(
                model_name=self.model_name,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._model

    # 목적: 검색 질문을 벡터 저장소와 비교할 숫자 벡터로 변환함.
    # 작업: 모델을 준비해 질문을 임베딩하고 실제 벡터 차원을 갱신함.
    # 리턴값: 질문을 나타내는 float 값의 벡터 목록임.
    def embed_query(self, text: str) -> list[float]:
        values = list(self._load().embed_query(text))
        self.dimension = len(values)
        return values


__all__ = ["LazyHuggingFaceEmbedder"]
