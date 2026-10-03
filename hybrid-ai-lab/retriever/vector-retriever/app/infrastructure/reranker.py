"""질의와 조각을 함께 읽어 관련도를 다시 매기는 Cross-Encoder 어댑터임(설계 ⑥-7)."""

from __future__ import annotations

import threading
from typing import Any, Callable, Sequence

from app.application.ports import RerankerPort

AUTO_DEVICE = "auto"


class CrossEncoderReranker(RerankerPort):
    """BAAI/bge-reranker-v2-m3으로 질의-조각 쌍에 0 ~ 1 점수를 매기는 어댑터임.

    모델 설정과 선택적 생성자를 주입받으며, 후보 뽑기·정렬·걸러내기는 수행하지 않음.
    """

    def __init__(
        self,
        model: str,
        *,
        revision: str,
        max_length: int = 1024,
        device: str = AUTO_DEVICE,
        local_files_only: bool = True,
        batch_size: int = 16,
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        """모델 식별자·revision·입력 길이 상한을 고정함.

        인자: max_length는 질의와 조각을 합쳐 읽는 토큰 상한이며 넘는 부분은 잘림(설계 ⑥-7).
        예외: 모델명·revision이 비었거나 상한·배치가 양수가 아니면 ValueError를 발생시킴.
        부수효과: 없음 — 모델 파일 읽기는 첫 score 호출까지 미룸.
        """

        if not str(model).strip() or not str(revision).strip():
            raise ValueError("리랭커 모델명과 revision은 비어 있을 수 없습니다.")
        if int(max_length) <= 0 or int(batch_size) <= 0:
            raise ValueError("리랭커 입력 길이 상한과 배치 크기는 양수여야 합니다.")
        self.model = str(model).strip()
        self.revision = str(revision).strip()
        self.max_length = int(max_length)
        self.device = str(device).strip()
        self.local_files_only = bool(local_files_only)
        self.batch_size = int(batch_size)
        self._model_factory = model_factory
        self._loaded: Any = None
        # 요청이 동시에 들어와도 모델을 두 번 올리지 않게 잠금으로 묶음.
        self._lock = threading.Lock()

    def _load(self) -> Any:
        """고정 revision 모델을 한 번만 올림.

        반환값: 적재된 CrossEncoder 객체임.
        예외: 로컬 캐시에 스냅샷이 없으면 라이브러리 예외를 그대로 올림.
        부수효과: 모델을 메모리에 올려 보관함.
        """

        if self._loaded is not None:
            return self._loaded
        with self._lock:
            if self._loaded is not None:
                return self._loaded
            factory = self._model_factory
            if factory is None:
                from sentence_transformers import CrossEncoder

                factory = CrossEncoder
            options: dict[str, Any] = {
                "revision": self.revision,
                "local_files_only": self.local_files_only,
                "max_length": self.max_length,
            }
            # auto는 PyTorch가 모르는 장치 이름이므로 인자를 생략해 라이브러리 자동 선택에 맡김.
            if self.device.lower() != AUTO_DEVICE:
                options["device"] = self.device
            self._loaded = factory(self.model, **options)
            return self._loaded

    def score(self, query: str, texts: Sequence[str]) -> list[float]:
        """질의-조각 쌍마다 0 ~ 1 관련도 점수를 반환함.

        인자: texts는 조각의 색인용 텍스트(index_text)이며 모델이 max_length 토큰까지만 읽음.
        반환값: texts와 같은 길이·같은 순서의 점수 목록임. texts가 비면 빈 목록임.
        예외: 모델 실패는 예외를 그대로 올림. 호출한 단계가 융합 결과로 대신하고 경고를 남김.
        부수효과: 첫 호출에서 모델 파일을 읽고 메모리에 유지함.
        """

        rows = [str(text) for text in texts]
        if not rows:
            return []
        import torch

        values = self._load().predict(
            [(str(query), text) for text in rows],
            batch_size=self.batch_size,
            # bge-reranker는 로짓을 내므로 Sigmoid로 0 ~ 1로 눌러 ⑥-8 상한·하한과 같은 축에 둠.
            activation_fn=torch.nn.Sigmoid(),
            show_progress_bar=False,
        )
        scores = [float(value) for value in (values.tolist() if hasattr(values, "tolist") else values)]
        if len(scores) != len(rows):
            raise ValueError("리랭커 점수 개수가 입력 조각 수와 다릅니다.")
        return scores


__all__ = ["CrossEncoderReranker"]
