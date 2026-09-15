"""CrossEncoder를 최초 사용 때 적재하는 리랭커."""

from __future__ import annotations

import math


class CrossEncoderReranker:
    def __init__(self, model_name: str, *, max_length: int = 512, predictor=None) -> None:
        self.model_name = model_name
        self.max_length = max_length
        self._model = predictor

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name, max_length=self.max_length)
        return self._model

    def score(self, query: str, texts: list[str]) -> list[float]:
        if not query.strip():
            raise ValueError("질문이 비어 있음")
        if not texts:
            return []
        model = self._load()
        try:
            import torch

            raw = model.predict(
                [(query, text) for text in texts],
                activation_fn=torch.nn.Sigmoid(),
                show_progress_bar=False,
            )
            already_sigmoid = True
        except (ImportError, TypeError):
            raw = model.predict([(query, text) for text in texts], show_progress_bar=False)
            already_sigmoid = False
        values = raw.tolist() if hasattr(raw, "tolist") else list(raw)
        if already_sigmoid:
            return [float(value) for value in values]
        return [1.0 / (1.0 + math.exp(-float(value))) for value in values]
