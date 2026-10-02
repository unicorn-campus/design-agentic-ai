"""임베딩과 같은 revision의 토크나이저로 입력 길이를 계산하는 어댑터임."""

from __future__ import annotations

from functools import lru_cache
from typing import Any, Callable

from app.application.ports import TokenCounterPort


class ModelTokenCounter(TokenCounterPort):
    """임베딩 모델과 동일한 토크나이저로 청크의 실제 입력 토큰 수를 계산함.

    목적: 청크가 임베딩 모델의 입력 한도(800토큰)를 넘는지 미리 세어 보기 위해 사용. 
          길이를 세는 데 무거운 임베딩 모델까지 돌릴 필요는 없어서 토크나이저만 불러옮
    모델명·revision·입력 상한을 주입받으며, 토크나이저는 처음 계산할 때 지연 로딩함.
    문서 분할이나 정제는 수행하지 않음.
    """

    def __init__(self, model_name: str, revision: str, max_tokens: int = 800,
                 *, local_files_only: bool = True, tokenizer_factory: Callable[..., Any] | None = None):
        """토큰 계산 계약과 선택적 토크나이저 팩터리를 설정함.

        인자: max_tokens는 특수 토큰을 포함한 임베딩 입력 상한임.
        부수효과: 없음. 모델 파일 접근은 최초 count 호출까지 미룸.
        """
        self.model_name = model_name
        self.revision = revision
        self._max_tokens = max_tokens
        self.local_files_only = local_files_only
        self._factory = tokenizer_factory
        self._tokenizer: Any = None

    @property   # 메소드를 변수처럼 읽을 수 있게 함. 외부에서는 변수처럼 쓰이고 실제론 함수라 값이 외부에서 변경되는 것을 막고 매번 계산해서 응답하기 위해 사용
    def signature(self) -> str:
        """모델 revision과 계산 정책을 식별하는 재현성 서명을 반환함."""

        return f"{self.model_name}@{self.revision}:special-tokens-included:{self.max_tokens}"

    @property
    def max_tokens(self) -> int:
        """특수 토큰을 포함한 임베딩 입력 상한을 반환함."""

        return self._max_tokens

    @lru_cache(maxsize=4096)
    def count(self, text: str) -> int:
        """절단하지 않은 입력의 특수 토큰 포함 개수를 반환함.

        방법: 같은 문자열의 반복 계산을 최대 4,096건까지 메모리에 캐시함.
        반환값: 임베딩 모델에 전달되는 토큰 수임.
        부수효과: 최초 호출 시 로컬 모델 저장소에서 토크나이저를 읽음.
        """

        if self._tokenizer is None:
            if self._factory is None:
                from transformers import AutoTokenizer
                factory = AutoTokenizer.from_pretrained
            else:
                factory = self._factory
            self._tokenizer = factory(self.model_name, revision=self.revision,
                                      local_files_only=self.local_files_only)
        return len(self._tokenizer.encode(text, add_special_tokens=True, truncation=False, verbose=False))
