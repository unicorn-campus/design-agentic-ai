"""질문을 색인과 같은 규칙으로 벡터 1개로 바꾸는 임베딩 어댑터임(설계 ⑥-5 · 색인 계약 3).

왜 접두어를 붙이지 않나: 색인도 받은 문자열을 그대로 모델에 넣었으므로(색인 계약 3절),
검색 쪽에서 "query: " 같은 접두어를 붙이면 같은 뜻의 문장이 다른 방향의 벡터가 되어 코사인 비교가 어긋남.
"""

from __future__ import annotations

import threading
from typing import Any, Callable

AUTO_DEVICE = "auto"


class SentenceTransformerEmbedder:
    """고정 revision의 KURE-v2 스냅샷으로 질의 벡터를 만드는 어댑터임.

    모델 설정과 선택적 생성자를 주입받으며, 검색·저장은 수행하지 않음.
    응용 계층에 임베딩 포트가 없어 이 어댑터는 같은 계층(infrastructure)의 색인 어댑터만 사용함.
    """

    def __init__(
        self,
        model: str,
        *,
        revision: str,
        device: str = AUTO_DEVICE,
        max_seq_length: int = 800,
        dimension: int = 768,
        local_files_only: bool = True,
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        """모델 식별자·revision·입력 상한·기대 출력 차원을 고정함.

        인자: max_seq_length는 특수 토큰을 포함한 입력 토큰 상한이며 색인과 같은 800이 기본값임.
        인자: device가 "auto"이면 인자를 생략해 라이브러리가 cuda·mps·cpu 중 쓸 수 있는 장치를 고름.
        예외: 모델명·revision이 비었거나 상한·차원이 양수가 아니면 ValueError를 발생시킴.
        부수효과: 없음 — 모델 파일 읽기는 첫 embed 호출까지 미룸(서버 시작을 막지 않기 위함).
        """

        if not str(model).strip() or not str(revision).strip():
            raise ValueError("임베딩 모델명과 revision은 비어 있을 수 없습니다.")
        if int(max_seq_length) <= 0 or int(dimension) <= 0:
            raise ValueError("입력 토큰 상한과 임베딩 차원은 양수여야 합니다.")
        self.model = str(model).strip()
        self.revision = str(revision).strip()
        self.device = str(device).strip()
        self.max_seq_length = int(max_seq_length)
        self.dimension = int(dimension)
        self.local_files_only = bool(local_files_only)
        self._model_factory = model_factory
        self._loaded: Any = None
        # 여러 요청이 동시에 첫 질의를 던져도 모델이 두 번 올라가지 않게 잠금으로 묶음.
        self._lock = threading.Lock()

    def _load(self) -> Any:
        """고정 revision 모델을 한 번만 올리고 입력 상한을 적용함.

        반환값: 적재된 모델 객체임.
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
                from sentence_transformers import SentenceTransformer

                factory = SentenceTransformer
            options: dict[str, Any] = {
                "revision": self.revision,
                "local_files_only": self.local_files_only,
            }
            # auto는 PyTorch가 모르는 장치 이름이므로 인자를 생략해 라이브러리 자동 선택에 맡김.
            if self.device.lower() != AUTO_DEVICE:
                options["device"] = self.device
            model = factory(self.model, **options)
            model.max_seq_length = self.max_seq_length
            self._loaded = model
            return model

    def embed(self, text: str) -> list[float]:
        """질문 한 문장을 길이 1로 정규화된 벡터 1개로 바꿈.

        인자: text는 접두어 없이 그대로 모델에 들어감(색인 계약 3).
        반환값: 길이가 dimension인 실수 목록임.
        예외: 입력이 빈 문자열이거나 출력 차원이 기대와 다르면 ValueError를 발생시킴.
        부수효과: 첫 호출에서 모델 파일을 읽고 메모리에 유지함.
        """

        if not isinstance(text, str) or not text.strip():
            raise ValueError("임베딩 입력은 비어 있지 않은 문자열이어야 합니다.")
        values = self._load().encode(
            [text],
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        row = values[0]
        vector = [float(value) for value in (row.tolist() if hasattr(row, "tolist") else row)]
        if len(vector) != self.dimension:
            raise ValueError(
                f"임베딩 출력 차원이 색인 계약과 다릅니다: expected={self.dimension}, actual={len(vector)}"
            )
        return vector


__all__ = ["SentenceTransformerEmbedder"]
