"""고정된 Hugging Face 스냅샷을 설정한 출력 차원의 단일 벡터로 변환하는 어댑터임."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from app.application.ports import EmbedderPort


LEGACY_SIGNATURE_PREFIX = "sentence-transformers:"
AUTO_DEVICE = "auto"


class HuggingFaceEmbedder(EmbedderPort):
    """SentenceTransformer 변환 규칙을 명시해 재현 가능한 벡터를 생성함.

    모델 설정과 선택적 팩터리를 주입받으며, 청킹·저장·검색은 수행하지 않음.
    """

    def __init__(
        self,
        model_name: str,
        *,
        revision: str,
        max_seq_length: int,
        batch_size: int = 32,
        device: str = "cpu",
        local_files_only: bool = True,
        expected_dimension: int | None = None,
        model_factory: Callable[..., Any] | None = None,
    ) -> None:
        """모델 revision, 입력 상한, 배치 크기와 출력 차원 계약을 설정함.

        인자: max_seq_length는 특수 토큰을 포함한 모델 입력 토큰 상한임.
        인자: device가 "auto"이면 장치를 지정하지 않아 라이브러리가 cuda·mps·cpu 중 사용 가능한 장치를 고름.
        예외: 빈 모델 식별자나 양수가 아닌 상한·배치·차원을 받으면 ValueError를 발생시킴.
        부수효과: 없음. 모델 파일 접근은 최초 임베딩 또는 dimension 조회까지 미룸.
        """

        if not model_name.strip() or not revision.strip():
            raise ValueError("임베딩 모델명과 revision은 비어 있을 수 없습니다.")
        if max_seq_length <= 0 or batch_size <= 0:
            raise ValueError("입력 토큰 상한과 배치 크기는 양수여야 합니다.")
        if expected_dimension is not None and expected_dimension <= 0:
            raise ValueError("예상 임베딩 차원은 양수여야 합니다.")
        self.model_name = model_name.strip()
        self.revision = revision.strip()
        self.max_seq_length = int(max_seq_length)
        self.batch_size = int(batch_size)
        self.device = device.strip()
        self.local_files_only = bool(local_files_only)
        self.expected_dimension = expected_dimension
        self._model_factory = model_factory
        self._model: Any = None
        self._dimension = 0
        self._resolved_device = ""

    @property
    def signature(self) -> str:
        """기존 Retriever와 호환되는 컬렉션 서명을 반환함."""

        return f"{LEGACY_SIGNATURE_PREFIX}{self.model_name}:prompt-policy-v2"

    @property
    def dimension(self) -> int:
        """모델이 출력하는 단일 벡터의 차원을 반환함.

        부수효과: 최초 조회 시 모델을 로드함.
        """

        if not self._dimension:
            self._load()
        return self._dimension

    @property
    def contract(self) -> dict[str, Any]:
        """manifest에 기록할 실제 모델 계약을 반환함.

        반환값: revision·풀링·정규화·입력 상한·차원 등 재현에 필요한 값임.
        부수효과: 최초 조회 시 모델을 로드함.
        """

        return {
            "backend": "sentence-transformers",
            "model": self.model_name,
            "revision": self.revision,
            "signature": self.signature,
            "pooling": "sentence-transformers-colbert-conversion-single-vector",
            "normalize_embeddings": True,
            "normalization": "float-l2-after-encode-v1",
            "max_seq_length": self.max_seq_length,
            "dimension": self.dimension,
            # auto는 실행 환경마다 결과가 달라지므로 요청값이 아니라 실제 선택된 장치를 기록함.
            "device": self._resolved_device or self.device,
            "local_files_only": self.local_files_only,
        }

    def _factory(self) -> Callable[..., Any]:
        """주입된 팩터리 또는 SentenceTransformer 생성자를 반환함."""

        if self._model_factory is not None:
            return self._model_factory
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer

    def _load(self) -> Any:
        """고정 revision의 모델을 한 번 로드하고 입력 상한과 출력 차원을 검증함."""

        if self._model is not None:
            return self._model
        options: dict[str, Any] = {"revision": self.revision, "local_files_only": self.local_files_only}
        # auto는 PyTorch가 모르는 장치 이름이므로 인자를 생략해 라이브러리의 자동 선택에 맡김.
        if self.device.lower() != AUTO_DEVICE:
            options["device"] = self.device
        model = self._factory()(self.model_name, **options)
        model.max_seq_length = self.max_seq_length
        getter = getattr(model, "get_embedding_dimension", None)
        if getter is None:
            getter = getattr(model, "get_sentence_embedding_dimension")
        dimension = int(getter())
        if dimension <= 0:
            raise ValueError("임베딩 출력 차원을 확인할 수 없습니다.")
        if self.expected_dimension is not None and dimension != self.expected_dimension:
            raise ValueError(
                "임베딩 모델 출력 차원이 설정과 다릅니다: "
                f"expected={self.expected_dimension}, actual={dimension}"
            )
        self._model = model
        self._dimension = dimension
        self._resolved_device = str(getattr(model, "device", "") or self.device)
        return model

    def embed(self, texts: list[str]) -> list[list[float]]:
        """비어 있지 않은 문자열 배치를 길이 1의 단일 벡터로 변환함.

        방법: 모델 정규화를 적용한 뒤 저장 직전 float 값으로 L2 정규화를 다시 검증함.
        반환값: 입력 순서를 유지하며 L2 노름이 1인 모델 출력 차원의 벡터 목록임.
        예외: 빈 입력 문자열, 행 수·차원 불일치, 유한하지 않은 값이나 0 노름이면 ValueError를 발생시킴.
        부수효과: 최초 호출 시 모델 파일을 읽고 메모리에 유지함. local_files_only가 False이면 다운로드할 수 있음.
        """

        if not texts:
            return []
        if any(not isinstance(text, str) or not text.strip() for text in texts):
            raise ValueError("임베딩 입력은 비어 있지 않은 문자열이어야 합니다.")
        values = self._load().encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        rows = values.tolist() if hasattr(values, "tolist") else [list(row) for row in values]
        if len(rows) != len(texts):
            raise ValueError("임베딩 입력과 출력 행 수가 일치하지 않습니다.")
        expected = self.dimension
        normalized_rows: list[list[float]] = []
        for row in rows:
            if len(row) != expected or any(not math.isfinite(float(value)) for value in row):
                raise ValueError("임베딩 출력 차원 또는 숫자 값이 올바르지 않습니다.")
            norm = math.sqrt(sum(float(value) ** 2 for value in row))
            if not math.isfinite(norm) or norm <= 0:
                raise ValueError("임베딩 출력의 L2 노름이 올바르지 않습니다.")
            # KURE-v2의 단일 벡터 변환은 normalize_embeddings=True에서도 저정밀도 반올림으로
            # 실제 노름이 약 0.997 ~ 1.003이 될 수 있어 저장 직전에 float 값으로 다시 정규화함.
            normalized = [float(value) / norm for value in row]
            checked_norm = math.sqrt(sum(value * value for value in normalized))
            if not math.isclose(checked_norm, 1.0, rel_tol=1e-6, abs_tol=1e-6):
                raise ValueError("임베딩 출력을 L2 정규화할 수 없습니다.")
            normalized_rows.append(normalized)
        return normalized_rows


def cached_snapshot_path(model_name: str, revision: str, cache_root: Path | None = None) -> Path:
    """다운로드 없이 사용할 로컬 Hugging Face 스냅샷 경로를 확인함.

    반환값: 지정한 모델과 revision의 캐시 디렉터리 절대 경로임.
    예외: 디렉터리가 없거나 모델 저장소 밖을 가리키면 FileNotFoundError를 발생시킴.
    부수효과: 없음.
    """

    root = cache_root or Path.home() / ".cache" / "huggingface" / "hub"
    repository = root / ("models--" + model_name.replace("/", "--"))
    snapshot = (repository / "snapshots" / revision).resolve()
    if not snapshot.is_dir() or not snapshot.is_relative_to(repository.resolve()):
        raise FileNotFoundError(f"로컬 모델 스냅샷이 없습니다: {model_name}@{revision}")
    return snapshot


__all__ = ["HuggingFaceEmbedder", "cached_snapshot_path"]
