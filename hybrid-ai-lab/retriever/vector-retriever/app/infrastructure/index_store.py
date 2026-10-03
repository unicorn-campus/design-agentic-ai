"""W-1이 게시한 색인 세대를 읽어 검색·분석하는 어댑터와 세대 교체 관리자임(S-R1 ④ ⑤ · 부록 C).

왜 적재 전에 서명·해시를 대조하나: 벡터와 BM25는 "같은 세대의 같은 218개 조각"을 전제로 점수를 붙임.
한쪽만 다른 세대이거나 사전이 다르면 조각ID가 어긋나 엉뚱한 문서를 근거로 내놓게 됨.
그래서 서명 4종·해시 4종이 모두 맞을 때에만 그 세대를 검색에 쓰고, 어긋나면 이전 세대를 계속 씀.
"""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

from app.application.models import IndexLease, IndexUnavailableError
from app.application.ports import IndexProviderPort, SearchIndexPort
from app.domain.models import Chunk, ScoredChunk, SourceInfo

from .korean_tokenizer import (
    KoreanTokenizer,
    has_digit,
    is_code_like,
    lexical_policy_fingerprint,
)

POINTER_NAME = "active_generation.json"  # 사용 중 세대 표시 파일(data 루트에 1개)
SEARCH_POINTER_NAME = "active_index.json"  # 세대 안쪽 텍스트 색인 포인터
STATE_NAME = "generation_state.json"
READY_STATUS = "ready"  # 이 값이 아닌 세대는 읽지 않음(색인 계약 1-6)

# 출처 표시에 쓰는 메타데이터 키(설계 ⑥-9). 나머지 키는 응답에 내보내지 않음.
_TEXT_SOURCE_KEYS = ("source", "doc_key", "doc_type", "clause_no", "card_id", "card_name",
                     "benefit_id", "section_label")
_INT_SOURCE_KEYS = ("page", "page_end")


def _read_json(path: Path) -> dict[str, Any]:
    """UTF-8(BOM 허용) JSON 파일 하나를 dict로 읽음."""

    value = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON 객체가 아닙니다: {path.name}")
    return value


def _file_sha256(path: Path) -> str:
    """파일 내용의 SHA-256 16진 문자열을 반환함."""

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_inside(root: Path, relative: str, *, directory: bool) -> Path:
    """상대 경로가 루트 안의 실제 파일·디렉터리인지 확인하고 절대 경로를 반환함.

    목적: 포인터 파일에 적힌 경로가 색인 루트 밖(예: ../../)을 가리키면 그 세대를 쓰지 않기 위함.
    예외: 루트를 벗어나면 ValueError, 없으면 FileNotFoundError를 발생시킴.
    """

    path = (Path(root) / str(relative)).resolve()
    if not path.is_relative_to(Path(root)):
        raise ValueError(f"색인 경로가 허용 범위 밖을 가리킵니다: {relative}")
    if not (path.is_dir() if directory else path.is_file()):
        raise FileNotFoundError(f"색인 경로가 없습니다: {relative}")
    return path


def _read_card_words(path: Path) -> tuple[tuple[str, str, float], ...]:
    """카드명 사전 파일(`형태<탭>품사<탭>점수`)을 사용자 단어 목록으로 읽음."""

    words: list[tuple[str, str, float]] = []
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 3:
            raise ValueError(f"카드명 사전 줄 형식이 올바르지 않습니다: {raw!r}")
        words.append((parts[0], parts[1], float(parts[2])))
    return tuple(words)


def _read_aliases(path: Path) -> dict[str, str]:
    """별칭 치환표 파일(`별칭표면형<탭>정식토큰`)을 dict로 읽음."""

    aliases: dict[str, str] = {}
    for raw in Path(path).read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        parts = raw.split("\t")
        if len(parts) != 2:
            raise ValueError(f"별칭 치환표 줄 형식이 올바르지 않습니다: {raw!r}")
        aliases[parts[0]] = parts[1]
    return aliases


def _source_info(metadata: dict[str, Any]) -> SourceInfo:
    """말뭉치 메타데이터에서 출처 표시용 값만 골라 SourceInfo로 만듦."""

    values: dict[str, Any] = {}
    for key in _TEXT_SOURCE_KEYS:
        raw = metadata.get(key)
        if raw is None:
            continue
        text = str(raw).strip()
        if text:
            values[key] = text
    for key in _INT_SOURCE_KEYS:
        raw = metadata.get(key)
        if raw is None:
            continue
        values[key] = int(raw)
    return SourceInfo(**values)


class GenerationIndex(SearchIndexPort):
    """한 세대의 Chroma 컬렉션·BM25 색인·말뭉치·Kiwi 사전을 함께 들고 읽기 전용으로 검색함.

    적재된 재료를 주입받으며, 세대 고르기·대조·교체는 LocalIndexProvider가 맡음.
    """

    def __init__(
        self,
        *,
        generation: str,
        collection: Any,
        bm25: Any,
        chunks: dict[str, Chunk],
        order: Sequence[str],
        tokenizer: KoreanTokenizer,
        embedder: Any,
        document_frequency: dict[str, int],
        chunk_terms: dict[str, frozenset[str]],
    ) -> None:
        """한 세대의 검색 재료를 모아 들고 있음.

        인자: order는 말뭉치를 조각ID 오름차순으로 읽은 순서이며 BM25 행 번호와 같아야 함(색인 계약 8).
        인자: document_frequency·chunk_terms는 적재 때 1회 계산한 값임(요청마다 다시 세지 않기 위함).
        예외: 조각 수와 순서 목록 길이가 다르면 ValueError를 발생시킴.
        부수효과: 없음.
        """

        if len(order) != len(chunks):
            raise ValueError("말뭉치 조각 수와 BM25 행 순서 길이가 다릅니다.")
        self._generation = str(generation)
        self._collection = collection
        self._bm25 = bm25
        self._chunks = dict(chunks)
        self._order = tuple(str(value) for value in order)
        self._tokenizer = tokenizer
        self._embedder = embedder
        self._document_frequency = dict(document_frequency)
        self._chunk_terms = dict(chunk_terms)

    def generation_id(self) -> str:
        """이 인스턴스가 가리키는 세대ID를 반환함.

        반환값: active_generation.json의 generation 값임.
        예외: 없음.
        부수효과: 없음.
        """

        return self._generation

    def num_docs(self) -> int:
        """세대의 조각 수를 반환함.

        반환값: 말뭉치 줄 수와 같은 정수임.
        예외: 없음.
        부수효과: 없음.
        """

        return len(self._order)

    @staticmethod
    def _levels(access_levels: Sequence[str]) -> tuple[str, ...]:
        """열람 등급 목록을 중복 없이 정리해 반환함."""

        return tuple(dict.fromkeys(str(value) for value in access_levels if str(value)))

    def vector_search(self, query: str, *, access_levels: Sequence[str], k: int) -> list[ScoredChunk]:
        """질의를 임베딩해 코사인 점수가 높은 조각 k개를 찾음(뜻으로 찾기).

        인자: query는 접두어 없이 그대로 임베딩함(색인 계약 4). access_levels 밖의 조각은 순위 매기기 전에 거름.
        반환값: 점수(1 − 코사인 거리) 내림차순 목록. 후보가 k보다 적으면 있는 만큼만 돌려줌.
        예외: 임베딩·벡터 저장소 실패는 예외를 그대로 올림. 호출한 단계가 '한쪽 실패'로 처리함.
        부수효과: 없음(읽기 전용).
        """

        levels = self._levels(access_levels)
        if not levels or int(k) <= 0 or not str(query).strip():
            return []
        vector = self._embedder.embed(str(query))
        # 권한 필터를 질의 인자로 넘겨 순위를 매기기 전에 거름 — LLM이 바꿀 수 없는 서버 쪽 조건임.
        result = self._collection.query(
            query_embeddings=[vector],
            n_results=min(int(k), self.num_docs()),
            where={"access_level": {"$in": list(levels)}},
            include=["distances"],
        )
        ids = (result.get("ids") or [[]])[0]
        distances = (result.get("distances") or [[]])[0]
        found = [
            ScoredChunk(str(chunk_id), 1.0 - float(distance))
            for chunk_id, distance in zip(ids, distances)
            if str(chunk_id) in self._chunks
        ]
        found.sort(key=lambda value: (-value.score, value.chunk_id))
        return found[: int(k)]

    def keyword_search(self, query: str, *, access_levels: Sequence[str], k: int) -> list[ScoredChunk]:
        """색인과 같은 분석기로 질의를 낱말로 나눠 BM25 점수가 높은 조각 k개를 찾음(낱말로 찾기).

        인자: access_levels 밖의 조각은 점수 계산 뒤 순위를 매기기 전에 버림.
        반환값: BM25 원점수 내림차순 목록. 점수가 0인 조각은 넣지 않음. 낱말이 하나도 없으면 빈 목록임.
        예외: BM25 색인 실패는 예외를 그대로 올림.
        부수효과: 없음(읽기 전용).
        """

        levels = self._levels(access_levels)
        if not levels or int(k) <= 0:
            return []
        tokens = self._tokenizer.tokenize(query)
        vocabulary: dict[str, int] = dict(getattr(self._bm25, "vocab_dict", {}) or {})
        # bm25s는 어휘 끝에 빈 토큰("")을 한 개 더 넣는데 그 자리에는 점수 자료가 없어 조회하면 오류가 남.
        # 그래서 점수 열이 실제로 있는 토큰ID만 남김.
        column_limit = len(self._bm25.scores["indptr"]) - 1
        token_ids = [
            vocabulary[token]
            for token in tokens
            if token in vocabulary and int(vocabulary[token]) < column_limit
        ]
        if not token_ids:
            return []
        scores = self._bm25.get_scores_from_ids(token_ids)
        found: list[ScoredChunk] = []
        for row, chunk_id in enumerate(self._order):
            score = float(scores[row])
            if score <= 0.0:
                continue
            chunk = self._chunks.get(chunk_id)
            if chunk is None or chunk.access_level not in levels:
                continue
            found.append(ScoredChunk(chunk_id, score))
        found.sort(key=lambda value: (-value.score, value.chunk_id))
        return found[: int(k)]

    def get_chunks(self, chunk_ids: Iterable[str]) -> dict[str, Chunk]:
        """조각ID로 말뭉치 조각(본문 text·색인용 index_text·출처 메타데이터)을 찾음.

        반환값: 조각ID → Chunk. 없는 ID는 결과에서 빠짐. 본문은 BM25 색인이 아니라 말뭉치에서 읽음.
        예외: 없음.
        부수효과: 없음.
        """

        found: dict[str, Chunk] = {}
        for chunk_id in chunk_ids:
            chunk = self._chunks.get(str(chunk_id))
            if chunk is not None:
                found[str(chunk_id)] = chunk
        return found

    def tokens(self, text: str) -> list[str]:
        """BM25와 똑같은 분석기(표기 통일·Kiwi·카드명·별칭 사전)로 문장을 낱말 목록으로 바꿈.

        반환값: 출현 횟수만큼 담은 낱말 목록. 빈 문장이면 빈 목록임.
        예외: 없음.
        부수효과: 없음.
        """

        if not str(text or "").strip():
            return []
        return self._tokenizer.tokenize(text)

    def keyword_candidates(self, text: str) -> list[str]:
        """채점 핵심어 후보로 명사·숫자·코드 낱말만 골라 반환함(사전으로 대상명 통일 포함).

        반환값: 중복을 뺀 낱말 목록(첫 출현 순서). 동사·형용사·부사는 넣지 않음.
        예외: 없음.
        부수효과: 없음.
        """

        if not str(text or "").strip():
            return []
        return self._tokenizer.keyword_terms(text)

    def document_frequency(self, terms: Iterable[str]) -> dict[str, int]:
        """낱말마다 그 낱말이 들어 있는 조각 수를 반환함(핵심어 드묾 계산용).

        반환값: 입력 순서를 지킨 낱말 → 조각 수. 색인에 없는 낱말은 0임.
        예외: 없음.
        부수효과: 없음. 문서 빈도는 세대를 올릴 때 1회 계산해 둔 값을 씀.
        """

        return {str(term): int(self._document_frequency.get(str(term), 0)) for term in terms}

    def chunk_terms(self, chunk_ids: Iterable[str]) -> frozenset[str]:
        """조각들의 색인용 텍스트를 같은 분석기로 자른 낱말의 합집합을 반환함(핵심어 일치 확인용).

        반환값: 낱말 집합. 없는 조각ID는 무시함.
        예외: 없음.
        부수효과: 없음.
        """

        found: set[str] = set()
        for chunk_id in chunk_ids:
            found |= self._chunk_terms.get(str(chunk_id), frozenset())
        return frozenset(found)

    def target_terms(self, text: str) -> frozenset[str]:
        """문장에 나온 카드 대상명(카드명 사전·별칭 사전으로 통일한 정식 토큰)을 반환함.

        반환값: 정식 카드 토큰 집합. 대상명이 없으면 빈 집합임.
        예외: 없음.
        부수효과: 없음.
        """

        cards = self._tokenizer.card_tokens
        return frozenset(term for term in self._tokenizer.keyword_terms(text) if term in cards)

    def condition_terms(self, text: str) -> frozenset[str]:
        """문장의 조건 낱말(카드 대상명 + 숫자·날짜·금액·코드)을 반환함(하위 질문 조건 보존 검사용).

        반환값: 분석기로 통일한 낱말 집합임.
        예외: 없음.
        부수효과: 없음.
        """

        cards = self._tokenizer.card_tokens
        return frozenset(
            term
            for term in self._tokenizer.keyword_terms(text)
            if term in cards or has_digit(term) or is_code_like(term)
        )


class LocalIndexProvider(IndexProviderPort):
    """같은 PC의 data 폴더에서 '사용 중 세대'를 골라 올려 두고 요청마다 빌려주는 관리자임.

    색인 루트·임베더·기대 임베딩 계약을 주입받으며, 색인 파일을 고치지 않음(읽기 전용).
    """

    def __init__(
        self,
        data_root: Path,
        *,
        embedder: Any,
        expected_embedding_contract: dict[str, Any],
        background_reload: bool = True,
        tokenizer_factory: Callable[..., KoreanTokenizer] | None = None,
    ) -> None:
        """색인 루트와 대조 기준을 설정함.

        인자: data_root는 active_generation.json이 있는 폴더이며 모든 세대 경로가 이 밑에 있어야 함.
        인자: expected_embedding_contract는 model·revision·dimension·normalize_embeddings 4개 키를 가져야 함.
        예외: 기대 임베딩 계약에 빠진 키가 있으면 ValueError를 발생시킴.
        부수효과: 없음 — 색인 적재는 load_initial·acquire에서 함.
        """

        missing = [
            key
            for key in ("model", "revision", "dimension", "normalize_embeddings")
            if key not in dict(expected_embedding_contract or {})
        ]
        if missing:
            raise ValueError(f"기대 임베딩 계약에 빠진 키가 있습니다: {missing}")
        self.data_root = Path(data_root).resolve()
        self.background_reload = bool(background_reload)
        self._embedder = embedder
        self._expected = dict(expected_embedding_contract)
        self._tokenizer_factory = tokenizer_factory or KoreanTokenizer
        self._lock = threading.Lock()
        self._current: GenerationIndex | None = None
        self._loading = False
        self._loading_generation = ""
        self._last_error = ""
        # 대조에 실패한 세대를 기억해 매 요청마다 같은 적재를 되풀이하지 않음(요청 지연·CPU 낭비 방지).
        self._failed: dict[str, str] = {}
        self._reload_thread: threading.Thread | None = None

    # ------------------------------------------------------------------ 포트 구현

    def acquire(self) -> IndexLease:
        """이번 요청이 쓸 세대를 돌려줌.

        방법: 사용 중 세대 표시 파일을 읽어 올려 둔 세대와 다르면 새 세대를 따로 올리고 서명·해시를 대조함.
        대조가 끝나기 전에는 올려 둔 세대를 돌려주고, 통과하면 다음 요청부터 새 세대를 씀.
        반환값: IndexLease(index=SearchIndexPort, warnings). 경고에는 '새 세대 적재 중'·'새 세대 대조 실패' 등이 담김.
        예외: 올려 둔 세대도 없고 새로 올릴 수도 없으면 IndexUnavailableError를 발생시킴.
        부수효과: 새 세대를 백그라운드에서 적재할 수 있음.
        """

        try:
            pointer = _read_json(self.data_root / POINTER_NAME)
            generation = str(pointer["generation"]).strip()
            if not generation:
                raise ValueError("사용 중 세대 표시 파일에 generation이 없습니다.")
        except Exception as error:  # noqa: BLE001 — 표시 파일 오류는 모두 '세대 못 고름'으로 다룸
            message = f"사용 중 세대 표시 파일을 읽지 못했습니다: {error}"
            with self._lock:
                self._last_error = message
                current = self._current
            if current is None:
                raise IndexUnavailableError(message) from error
            return IndexLease(current, ("사용 중 세대 표시 파일을 읽지 못해 올려 둔 세대를 계속 씀",))

        with self._lock:
            current = self._current
            if current is not None and current.generation_id() == generation:
                return IndexLease(current, ())

        if current is None:
            return IndexLease(self._load_now(pointer, generation), ())
        if not self.background_reload:
            return self._swap_now(pointer, generation, current)
        return IndexLease(current, self._request_reload(pointer, generation))

    def status(self) -> dict[str, Any]:
        """상태 확인(health)용 정보를 반환함.

        반환값: ready(bool)·generation·chunk_count·loading(bool)·last_error 키를 가진 dict임.
        예외: 없음.
        부수효과: 없음.
        """

        with self._lock:
            current = self._current
            return {
                "ready": current is not None,
                "generation": None if current is None else current.generation_id(),
                "chunk_count": 0 if current is None else current.num_docs(),
                "loading": self._loading,
                "last_error": self._last_error,
            }

    # ------------------------------------------------------------------ 적재·교체

    def load_initial(self) -> bool:
        """서버 시작 때 사용 중 세대를 동기로 올림.

        왜 예외를 올리지 않나: 색인이 아직 없어도 서버는 떠서 상태 확인에 사유를 보여 줘야 하기 때문임.
        반환값: 적재 성공 여부임. 실패 사유는 status()의 last_error에 남음.
        예외: 없음.
        부수효과: 세대 재료(Chroma·BM25·Kiwi 사전)를 메모리에 올림.
        """

        try:
            pointer = _read_json(self.data_root / POINTER_NAME)
            generation = str(pointer["generation"]).strip()
            index = self._load_generation(pointer, generation)
        except Exception as error:  # noqa: BLE001 — 시작 때 어떤 실패든 서버를 막지 않음
            with self._lock:
                self._last_error = f"시작 적재 실패: {error}"
            return False
        with self._lock:
            self._current = index
            self._last_error = ""
            self._failed.pop(index.generation_id(), None)
        return True

    def wait_for_reload(self, timeout: float = 120.0) -> None:
        """진행 중인 백그라운드 적재가 끝날 때까지 기다림(시험에서 교체를 확인하는 용도).

        인자: timeout은 기다릴 최대 초임.
        반환값: 없음.
        예외: 없음 — 시간이 지나면 그냥 돌아옴.
        부수효과: 없음.
        """

        with self._lock:
            thread = self._reload_thread
        if thread is not None:
            thread.join(timeout)

    def _load_now(self, pointer: dict[str, Any], generation: str) -> GenerationIndex:
        """올려 둔 세대가 없을 때 동기로 적재하고 실패하면 검색을 거부함."""

        try:
            index = self._load_generation(pointer, generation)
        except Exception as error:  # noqa: BLE001 — 사유를 상태에 남기고 표준 오류로 바꿈
            message = f"색인 세대를 올리지 못했습니다({generation}): {error}"
            with self._lock:
                self._last_error = message
                self._failed[generation] = message
            raise IndexUnavailableError(message) from error
        with self._lock:
            self._current = index
            self._last_error = ""
            self._failed.pop(generation, None)
        return index

    def _swap_now(
        self,
        pointer: dict[str, Any],
        generation: str,
        current: GenerationIndex,
    ) -> IndexLease:
        """백그라운드 적재를 끄고 쓸 때 쓰는 동기 교체. 실패하면 이전 세대를 그대로 씀."""

        try:
            index = self._load_generation(pointer, generation)
        except Exception as error:  # noqa: BLE001 — 대조 실패는 경고로 남기고 이전 세대 유지
            message = f"새 세대 대조 실패({generation}): {error}"
            with self._lock:
                self._last_error = message
                self._failed[generation] = message
            return IndexLease(current, (message,))
        with self._lock:
            self._current = index
            self._last_error = ""
            self._failed.pop(generation, None)
        return IndexLease(index, ())

    def _request_reload(self, pointer: dict[str, Any], generation: str) -> tuple[str, ...]:
        """새 세대 적재를 백그라운드 스레드 하나로 시작하고 이번 요청에 붙일 경고를 만듦."""

        with self._lock:
            if generation in self._failed:
                return (f"새 세대 대조 실패({generation}) — 이전 세대를 계속 씀",)
            if self._loading:
                return (f"새 세대 적재 중({self._loading_generation}) — 이번 요청은 이전 세대로 처리함",)
            self._loading = True
            self._loading_generation = generation
            thread = threading.Thread(
                target=self._reload,
                args=(pointer, generation),
                name="index-reload",
                daemon=True,
            )
            self._reload_thread = thread
        thread.start()
        return (f"새 세대 적재 중({generation}) — 이번 요청은 이전 세대로 처리함",)

    def _reload(self, pointer: dict[str, Any], generation: str) -> None:
        """백그라운드에서 새 세대를 올리고 통과하면 사용 세대를 바꿈."""

        try:
            index = self._load_generation(pointer, generation)
        except Exception as error:  # noqa: BLE001 — 실패해도 이전 세대로 서비스를 이어 감
            with self._lock:
                self._last_error = f"새 세대 대조 실패({generation}): {error}"
                self._failed[generation] = self._last_error
                self._loading = False
                self._loading_generation = ""
            return
        with self._lock:
            self._current = index
            self._last_error = ""
            self._failed.pop(generation, None)
            self._loading = False
            self._loading_generation = ""

    # ------------------------------------------------------------------ 대조(부록 C)

    def _load_generation(self, pointer: dict[str, Any], generation: str) -> GenerationIndex:
        """세대 하나를 대조한 뒤 검색할 수 있는 상태로 올림.

        순서: 파일만 보는 가벼운 대조를 먼저 다 하고, 통과한 뒤에 무거운 적재(Kiwi·BM25·Chroma)를 함.
        반환값: 대조를 모두 통과한 GenerationIndex임.
        예외: 어느 대조든 어긋나면 ValueError·FileNotFoundError를 발생시킴(그 세대를 쓰지 않음).
        부수효과: Chroma·BM25·Kiwi 사전을 메모리에 올림.
        """

        paths = self._verify_files(pointer, generation)
        return self._build_index(pointer, generation, paths)

    def _verify_files(self, pointer: dict[str, Any], generation: str) -> dict[str, Any]:
        """파일만 읽어 상태·경로·서명 3종·해시 3종과 조각 수를 대조함."""

        if not generation or generation in {".", ".."} or any(c in generation for c in "/\\"):
            raise ValueError(f"generation 형식이 올바르지 않습니다: {generation!r}")

        chroma_dir = _resolve_inside(self.data_root, str(pointer["chroma_path"]), directory=True)
        search_root = _resolve_inside(self.data_root, str(pointer["search_index_root"]), directory=True)
        # 두 색인이 같은 세대 폴더 밑에 있어야 벡터와 BM25의 조각이 어긋나지 않음(색인 계약 1-6).
        if chroma_dir.parent != search_root.parent:
            raise ValueError("벡터 저장소와 텍스트 색인이 같은 세대 폴더 밑에 없습니다.")

        state = _read_json(chroma_dir.parent / STATE_NAME)
        if str(state.get("status")) != READY_STATUS:
            raise ValueError(f"세대 상태가 {READY_STATUS}가 아닙니다: {state.get('status')!r}")
        if str(state.get("generation")) != generation:
            raise ValueError("세대 상태 파일의 generation이 표시 파일과 다릅니다.")

        search_pointer = _read_json(search_root / SEARCH_POINTER_NAME)
        if str(search_pointer.get("generation")) != generation:
            raise ValueError("텍스트 색인 포인터의 generation이 표시 파일과 다릅니다.")

        manifest_path = _resolve_inside(search_root, str(search_pointer["manifest"]), directory=False)
        corpus_path = _resolve_inside(search_root, str(search_pointer["corpus"]), directory=False)
        bm25_dir = _resolve_inside(search_root, str(search_pointer["bm25"]), directory=True)
        card_path = _resolve_inside(search_root, str(search_pointer["card_dictionary"]), directory=False)
        alias_path = _resolve_inside(search_root, str(search_pointer["card_aliases"]), directory=False)
        manifest = _read_json(manifest_path)
        if str(manifest.get("generation")) != generation:
            raise ValueError("manifest의 generation이 표시 파일과 다릅니다.")

        self._verify_signatures(pointer, state, manifest)
        chunk_count = self._verify_hashes(
            pointer, search_pointer, manifest, corpus_path, card_path, alias_path
        )
        return {
            "chroma_dir": chroma_dir,
            "bm25_dir": bm25_dir,
            "corpus_path": corpus_path,
            "card_path": card_path,
            "alias_path": alias_path,
            "manifest": manifest,
            "chunk_count": chunk_count,
            "embedding_signature": str(pointer["embedding_signature"]),
            "collection": str(pointer["collection"]),
        }

    def _verify_signatures(
        self,
        pointer: dict[str, Any],
        state: dict[str, Any],
        manifest: dict[str, Any],
    ) -> None:
        """서명 4종 중 파일만으로 볼 수 있는 3종을 대조함(Kiwi 서명은 적재 때 봄)."""

        signature = str(pointer["embedding_signature"])
        others = {
            "세대 상태": str(state.get("embedding_signature")),
            "manifest": str(manifest.get("embedding_signature")),
            "manifest.vector": str((manifest.get("vector") or {}).get("embedding_signature")),
        }
        for where, value in others.items():
            if value != signature:
                raise ValueError(f"임베딩 서명이 표시 파일과 {where}에서 다릅니다: {value!r}")

        contract = dict(manifest.get("embedding_contract") or {})
        if str(contract.get("model")) != str(self._expected["model"]):
            raise ValueError(f"임베딩 모델이 기대값과 다릅니다: {contract.get('model')!r}")
        if str(contract.get("revision")) != str(self._expected["revision"]):
            raise ValueError(f"임베딩 revision이 기대값과 다릅니다: {contract.get('revision')!r}")
        if int(contract.get("dimension", -1)) != int(self._expected["dimension"]):
            raise ValueError(f"임베딩 차원이 기대값과 다릅니다: {contract.get('dimension')!r}")
        if bool(contract.get("normalize_embeddings")) != bool(self._expected["normalize_embeddings"]):
            raise ValueError("임베딩 정규화 설정이 기대값과 다릅니다.")
        if int(pointer.get("embedding_dimension", -1)) != int(self._expected["dimension"]):
            raise ValueError("표시 파일의 임베딩 차원이 기대값과 다릅니다.")

        aliases = dict(manifest.get("card_aliases") or {})
        fingerprint = lexical_policy_fingerprint(
            alias_rules_sha256=str(aliases.get("rules_sha256", "")),
            alias_overrides_sha256=str(aliases.get("overrides_sha256", "")),
        )
        if fingerprint != str(manifest.get("lexical_policy_fingerprint")):
            raise ValueError("어휘 정책 지문이 manifest 값과 다릅니다 — 색인과 검색의 분석기 정책이 어긋남")

    @staticmethod
    def _verify_hashes(
        pointer: dict[str, Any],
        search_pointer: dict[str, Any],
        manifest: dict[str, Any],
        corpus_path: Path,
        card_path: Path,
        alias_path: Path,
    ) -> int:
        """해시 4종(말뭉치·카드명 사전·별칭 사전·조각 수)을 포인터·manifest·실제 파일에서 대조함."""

        corpus_hash = _file_sha256(corpus_path)
        if str(search_pointer.get("corpus_sha256")) != corpus_hash:
            raise ValueError("말뭉치 해시가 텍스트 색인 포인터와 다릅니다.")
        if str(manifest.get("corpus_sha256")) != corpus_hash:
            raise ValueError("말뭉치 해시가 manifest와 다릅니다.")

        card_hash = _file_sha256(card_path)
        if str(search_pointer.get("card_dictionary_sha256")) != card_hash:
            raise ValueError("카드명 사전 해시가 텍스트 색인 포인터와 다릅니다.")
        if str((manifest.get("card_dictionary") or {}).get("sha256")) != card_hash:
            raise ValueError("카드명 사전 해시가 manifest와 다릅니다.")

        alias_hash = _file_sha256(alias_path)
        if str(search_pointer.get("card_aliases_sha256")) != alias_hash:
            raise ValueError("별칭 사전 해시가 텍스트 색인 포인터와 다릅니다.")
        if str((manifest.get("card_aliases") or {}).get("sha256")) != alias_hash:
            raise ValueError("별칭 사전 해시가 manifest와 다릅니다.")

        chunk_count = int(pointer["chunk_count"])
        corpus_lines = sum(1 for line in corpus_path.read_bytes().splitlines() if line.strip())
        if int(search_pointer.get("chunk_count", -1)) != chunk_count:
            raise ValueError("조각 수가 텍스트 색인 포인터와 다릅니다.")
        if int(manifest.get("chunk_count", -1)) != chunk_count:
            raise ValueError("조각 수가 manifest와 다릅니다.")
        if corpus_lines != chunk_count:
            raise ValueError(f"말뭉치 줄 수가 조각 수와 다릅니다: {corpus_lines} != {chunk_count}")
        return chunk_count

    # ------------------------------------------------------------------ 무거운 적재

    def _build_index(
        self,
        pointer: dict[str, Any],
        generation: str,
        paths: dict[str, Any],
    ) -> GenerationIndex:
        """대조를 통과한 세대의 말뭉치·Kiwi 사전·BM25·Chroma를 올리고 나머지 대조를 마침."""

        chunks, order, index_texts = self._read_corpus(paths["corpus_path"])
        manifest = paths["manifest"]

        tokenizer = self._tokenizer_factory(
            None,
            additional_user_words=_read_card_words(paths["card_path"]),
            aliases=_read_aliases(paths["alias_path"]),
        )
        if tokenizer.signature != str(manifest.get("tokenizer_signature")):
            raise ValueError(
                "조립한 Kiwi 서명이 manifest와 다릅니다 — 질의 낱말이 색인 낱말과 어긋남: "
                f"{tokenizer.signature}"
            )

        bm25 = self._load_bm25(paths["bm25_dir"])
        num_docs = int((getattr(bm25, "scores", None) or {}).get("num_docs", -1))
        if num_docs != paths["chunk_count"]:
            raise ValueError(f"BM25 문서 수가 조각 수와 다릅니다: {num_docs} != {paths['chunk_count']}")

        collection = self._open_collection(paths["chroma_dir"], paths["collection"])
        metadata = dict(getattr(collection, "metadata", None) or {})
        stored = str(metadata.get("embedding_model_signature"))
        if stored != paths["embedding_signature"]:
            raise ValueError(f"Chroma 컬렉션의 임베딩 서명이 표시 파일과 다릅니다: {stored!r}")
        count = int(collection.count())
        if count != paths["chunk_count"]:
            raise ValueError(f"Chroma 조각 수가 말뭉치와 다릅니다: {count} != {paths['chunk_count']}")

        # 문서 빈도와 조각별 낱말 집합은 요청마다 세면 느려서 적재 때 한 번만 계산함.
        per_chunk = tokenizer.tokenize_many(index_texts)
        document_frequency: dict[str, int] = {}
        chunk_terms: dict[str, frozenset[str]] = {}
        for chunk_id, tokens in zip(order, per_chunk, strict=True):
            terms = frozenset(tokens)
            chunk_terms[chunk_id] = terms
            for term in terms:
                document_frequency[term] = document_frequency.get(term, 0) + 1

        return GenerationIndex(
            generation=generation,
            collection=collection,
            bm25=bm25,
            chunks=chunks,
            order=order,
            tokenizer=tokenizer,
            embedder=self._embedder,
            document_frequency=document_frequency,
            chunk_terms=chunk_terms,
        )

    @staticmethod
    def _read_corpus(path: Path) -> tuple[dict[str, Chunk], tuple[str, ...], list[str]]:
        """말뭉치를 파일 순서(조각ID 오름차순 = BM25 행 번호)대로 읽음(색인 계약 8)."""

        chunks: dict[str, Chunk] = {}
        order: list[str] = []
        index_texts: list[str] = []
        for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            chunk_id = str(row["chunk_id"])
            text = str(row["text"])
            # index_text가 없는 조각은 text가 곧 색인용 텍스트임(색인 계약 9-9).
            index_text = str(row.get("index_text") or text)
            metadata = dict(row.get("metadata") or {})
            chunks[chunk_id] = Chunk(
                chunk_id=chunk_id,
                text=text,
                index_text=index_text,
                access_level=str(metadata.get("access_level", "")),
                source=_source_info(metadata),
            )
            order.append(chunk_id)
            index_texts.append(index_text)
        if len(chunks) != len(order):
            raise ValueError("말뭉치에 중복 조각ID가 있습니다.")
        return chunks, tuple(order), index_texts

    @staticmethod
    def _load_bm25(bm25_dir: Path) -> Any:
        """저장된 bm25s 색인을 읽음. k1·b는 색인 때 점수에 들어갔으므로 바꾸지 않음."""

        import bm25s

        return bm25s.BM25.load(str(bm25_dir), load_corpus=False, mmap=False, show_progress=False)

    @staticmethod
    def _open_collection(chroma_dir: Path, collection: str) -> Any:
        """세대 폴더의 Chroma 컬렉션을 읽기용으로 엶."""

        import chromadb

        client = chromadb.PersistentClient(path=str(chroma_dir))
        return client.get_collection(name=collection)


__all__ = ["GenerationIndex", "LocalIndexProvider", "POINTER_NAME", "READY_STATUS"]
