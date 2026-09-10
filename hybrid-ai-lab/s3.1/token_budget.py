"""선택한 모델의 로컬 tokenizer.json으로 실제 토큰 수 계산."""
import hashlib
from pathlib import Path


class TokenBudget:
    def __init__(self, path: Path, limit: int, prefix: str = ''):
        if limit <= 0:
            raise ValueError('max-input-tokens는 양의 정수 필요')
        from tokenizers import Tokenizer
        self.tokenizer = Tokenizer.from_file(str(path))
        # 파일에 저장된 자동 절단·패딩 설정 때문에 검사 결과가 왜곡되지 않도록 해제함.
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        self.limit = limit
        self.prefix = prefix
        self.source = str(path.resolve())
        self.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

    def count(self, text: str) -> int:
        return len(self.tokenizer.encode(self.prefix + text, add_special_tokens=True).ids)
