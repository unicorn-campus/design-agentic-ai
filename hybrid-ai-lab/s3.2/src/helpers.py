"""강사 제공: 모델 호출, 영속 컬렉션, 메타데이터 변환."""
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import hashlib
import json
import math
import os

from dotenv import dotenv_values

BASE = Path(__file__).resolve().parents[1]
_env = {**dotenv_values(BASE.parent / '.env'), **dotenv_values(BASE / '.env'), **os.environ}


@dataclass(frozen=True)
class Settings:
    db_path: Path
    collection: str = 'card_docs'
    backend: str = 'sentence-transformers'
    model: str = 'nlpai-lab/KURE-v1'


_path = Path(_env.get('DB_PATH') or 'data/chroma/group1')
_settings = Settings(
    db_path=(_path if _path.is_absolute() else BASE / _path).resolve(),
    model=_env.get('EMBED_MODEL') or 'nlpai-lab/KURE-v1',
)


def configure(*, db_path=None, collection=None, backend=None, model=None) -> Settings:
    """CLI에서 선택한 설정 공유. 상대 DB 경로는 s3.2 기준임."""
    global _settings
    path = Path(db_path) if db_path is not None else _settings.db_path
    backend = backend or _settings.backend
    if backend not in ('sentence-transformers', 'smoke'):
        raise ValueError('backend는 sentence-transformers 또는 smoke임')
    _settings = Settings(
        (path if path.is_absolute() else BASE / path).resolve(),
        collection or _settings.collection, backend, model or _settings.model,
    )
    return _settings


def settings() -> Settings:
    return _settings


@lru_cache(maxsize=8)
def _client(path: str):
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    return chromadb.PersistentClient(path=path, settings=ChromaSettings(anonymized_telemetry=False))


def get_collection(name: str = 'card_docs'):
    """코사인 컬렉션 열기. 모델이 달라지면 같은 저장소 재사용을 차단함."""
    config = settings()
    actual_name = config.collection if name == 'card_docs' else name
    signature = ('smoke-sha256-bigram-v1' if config.backend == 'smoke'
                 else f'sentence-transformers:{config.model}:prompt-policy-v2')
    col = _client(str(config.db_path)).get_or_create_collection(
        name=actual_name,
        embedding_function=None,
        configuration={'hnsw': {'space': 'cosine'}},
        metadata={'lab_embedding': signature},
    )
    if (col.metadata or {}).get('lab_embedding') != signature:
        raise ValueError('컬렉션의 임베딩 모델이 다름. 새 --db-path 또는 --collection 지정 필요')
    if col.configuration.get('hnsw', {}).get('space') != 'cosine':
        raise ValueError('이 실습은 cosine 거리 컬렉션이 필요함')
    return col


@lru_cache(maxsize=2)
def _model(name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError('실제 모델 사용 전 requirements-model.txt 설치 필요') from exc
    return SentenceTransformer(name, trust_remote_code=False)


def embed_texts(texts: list[str], kind: str = 'passage') -> list[list[float]]:
    """적재는 passage, 검색은 query. 테스트용 벡터는 뜻 검색 평가에 사용 불가."""
    if kind not in ('passage', 'query'):
        raise ValueError('kind는 passage 또는 query임')
    if any(not isinstance(text, str) or not text.strip() for text in texts):
        raise ValueError('임베딩 입력은 비어 있지 않은 문자열이어야 함')
    if not texts:
        return []
    config = settings()
    if config.backend == 'smoke':
        vectors = []
        for text in texts:
            vec = [0.0] * 384
            value = text.strip().lower()
            for i in range(max(1, len(value) - 1)):
                token = value[i:i + 2].encode('utf-8')
                vec[int.from_bytes(hashlib.sha256(token).digest()[:4], 'big') % 384] += 1
            norm = math.sqrt(sum(x * x for x in vec))
            vectors.append([x / norm for x in vec])
        return vectors
    model = _model(config.model)
    # e5 계열만 영문 접두어가 필요함. KURE-v1은 공식 예시처럼 원문을 그대로 사용함.
    is_e5 = 'e5' in config.model.lower()
    prepared = [f'{kind}: {text}' for text in texts] if is_e5 else texts
    if not is_e5:
        prompt_key = 'query' if kind == 'query' else 'document'
        prefix = model.prompts.get(prompt_key, model.prompts.get('passage', '') if kind == 'passage' else '')
        prepared = [prefix + text for text in texts]
    counts = model.tokenizer(prepared, truncation=False, add_special_tokens=True)['input_ids']
    if any(len(tokens) > model.max_seq_length for tokens in counts):
        raise ValueError(f'모델 입력 한도 {model.max_seq_length}토큰 초과: S3.1에서 재분할 필요')
    # 접두어는 위에서 이미 붙였으므로 encode의 자동 프롬프트를 비움.
    return model.encode(prepared, prompt='', normalize_embeddings=True,
                        show_progress_bar=False, convert_to_numpy=True).tolist()


def sanitize_metadata(metadata: dict) -> dict:
    """None 키 제거, 구조 값은 JSON 문자열로 보존. 권한 키는 반드시 검사함."""
    if metadata.get('access_level') not in ('public', 'internal', 'restricted'):
        raise ValueError('access_level 누락 또는 허용 값 오류')
    if metadata.get('doc_type') not in ('regulation', 'benefit_guide', 'consult_log'):
        raise ValueError('doc_type 누락 또는 허용 값 오류')
    result = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if not isinstance(key, str):
            raise ValueError('메타데이터 키는 문자열이어야 함')
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(f'유한하지 않은 메타데이터 값: {key}')
        result[key] = value if isinstance(value, (str, int, float, bool)) else json.dumps(value, ensure_ascii=False)
    return result
