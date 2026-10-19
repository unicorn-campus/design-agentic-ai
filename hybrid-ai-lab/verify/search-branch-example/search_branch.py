"""1-b 분리형(검색 엔진) 인덱싱 파이프라인의 검색 갈래 4단계를 보여 주는 교육용 예제임.

장표의 검색 갈래와 함수가 1:1로 대응함.
  ① 청크 임베딩(바뀐 것만)        -> step1_embed_changed_chunks
       사전 검사 precheck_skip_run, 1번 check1_reusable_run,
       2번 check2_find_same_text, 3번 check3_get_vectors
  ② 키워드 분석(nori 또는 Kiwi)   -> step2_analyze_keywords
       카드명 사전과 별칭 build_keyword_dictionary, 검색 쪽 토크나이저 load_query_tokenizer,
       BM25 조절값 k1 1.5, b 0.75(인덱스 similarity)
  ③ 검색 엔진에 쓰기(문서 단위)   -> step3_write_documents
  ④ 별칭 전환(세대)               -> step4_switch_alias

검색 엔진은 OpenSearch(Apache 2.0)를 씀. Elasticsearch도 같은 모양으로 동작하나 라이선스가 AGPL/SSPL/ELv2임.
비밀번호와 키는 코드에 넣지 않고 환경변수(OPENSEARCH_URL 등)로만 받음.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from opensearchpy import OpenSearch, helpers

# 기존 1-a 구현(vector-bm25)의 토큰화·임베딩 정책을 그대로 재사용하려고 경로를 붙임.
# 같은 정책을 두 번 적으면 색인 쪽과 검색 쪽 토큰이 어긋나므로 복사하지 않고 import 함.
LAB_ROOT = Path(
    os.environ.get(
        "LAB_ROOT",
        r"C:/Users/hiond/class/design-agentic-ai/hybrid-ai-lab/indexer/vector-bm25",
    )
)
if str(LAB_ROOT) not in sys.path:
    sys.path.insert(0, str(LAB_ROOT))

from app.domain.card_aliases import AliasOverrides, AliasRules, build_alias_plan  # noqa: E402
from app.infrastructure.embedder import HuggingFaceEmbedder  # noqa: E402
from app.infrastructure.korean_tokenizer import KoreanTokenizer, PlainNounChecker  # noqa: E402

# 카드명 사전 추출과 별칭 정책 정규화는 1-a가 내부 함수로 둔 규칙임.
# 규칙을 다시 적으면 1-a와 1-b의 사전이 조용히 달라질 수 있어 그대로 가져다 씀.
from app.infrastructure.lexical_index import (  # noqa: E402
    AliasPolicy,
    _card_dictionary_words,
    _normalized_alias_policy,
)


# ---------------------------------------------------------------------------
# 공통 값과 자료 구조
# ---------------------------------------------------------------------------

#: 검색이 바라보는 이름임. 질의는 늘 이 별칭에만 붙고 실제 인덱스 이름은 모름.
DEFAULT_ALIAS = "card_chunks"

#: 회원 필터에 쓰는 메타데이터 이름임. 상담 기록(D3)에만 들어 있음.
MEMBER_FIELD = "member_pseudo_id"

#: 검색 결과 문서에서 메타데이터로 함께 저장할 항목임. 모두 정확히 일치하는 값으로 거르는 키워드형임.
KEYWORD_METADATA_FIELDS = (
    "doc_key",
    "doc_type",
    "access_level",
    "source",
    "card_id",
    "card_name",
    "product_id",
    "benefit_id",
    "record_id",
    "channel",
    "topic",
    "age_band",
    MEMBER_FIELD,
)


#: BM25 조절값. 1-a(bm25s)와 같은 값으로 맞춤. OpenSearch 기본값은 k1 1.2, b 0.75라 인덱스에 직접 지정함.
BM25_K1 = 1.5  # 같은 낱말이 반복될 때 점수가 더 오르는 정도
BM25_B = 0.75  # 긴 청크의 점수를 깎는 정도
BM25_SIMILARITY = "bm25_lab"  # text_tokens 필드에 거는 사용자 정의 BM25 이름


#: ①단계가 청크마다 남기는 판단 결과임. 장표의 「청크별 판단 순서」 갈래와 1:1로 대응함.
REUSE_SAME_ID = "reuse_same_id"  # 2번 예: 같은 ID에 같은 정제 본문
REUSE_SAME_TEXT = "reuse_same_text"  # 2번 예: ID는 달라도 같은 정제 본문
NEW_NOT_REUSABLE_RUN = "new_not_reusable_run"  # 1번 아니요: 활성 세대 없음, 임베딩 설정 변경, 강제 재색인
NEW_NO_SAME_TEXT = "new_no_same_text"  # 2번 아니요: 일치하는 기존 해시 없음
NEW_VECTOR_MISSING = "new_vector_missing"  # 3번 아니요: 고른 기존 벡터가 조회 결과에 없음


@dataclass(frozen=True)
class EmbedReport:
    """①단계가 벡터를 몇 개 새로 만들고 몇 개 다시 썼는지, 청크마다 왜 그렇게 판단했는지 알려 줌."""

    embedded_ids: tuple[str, ...]  # 이번에 새로 임베딩한 청크 ID
    reused_ids: tuple[str, ...]  # 이전 세대 벡터를 그대로 가져다 쓴 청크 ID
    reasons: Mapping[str, str]  # {chunk_id: 판단 결과 상수}. 교재와 시험에서 갈래를 확인하는 근거


@dataclass(frozen=True)
class RunContract:
    """이번 실행의 입력과 처리 설정 묶음.

    세대 인덱스의 `_meta`에 그대로 기록해 두고, 다음 실행이 사전 검사와 1번 판단에서 비교함.
    1-a 인덱서가 manifest에 남기는 값과 같은 항목임.
    """

    inputs_sha256: Mapping[str, str]  # 원천 문서별 내용 지문
    policy_signature: str  # 문서 처리 정책(분할, 머리말 등)의 지문
    profile_signature: str  # 문서 프로필(보강값, 허용 메타데이터 규칙)의 지문
    embedding_signature: str  # 모델 이름과 입력 규칙을 담은 서명 문자열
    embedding_contract: Mapping[str, Any]  # 모델, revision, 입력 상한, 차원, 정규화 등 재현에 필요한 값
    lexical_signature: str  # 토크나이저 서명. 토큰화 정책, 카드명 사전, 별칭 치환표가 모두 들어감
    keyword_dictionary: Mapping[str, Any]  # KeywordDictionary.to_meta(). 검색 쪽이 같은 토크나이저를 다시 만드는 재료

    def to_meta(self) -> dict[str, Any]:
        """인덱스 `_meta`에 넣을 JSON 모양으로 바꿈."""

        return {
            "inputs_sha256": dict(self.inputs_sha256),
            "policy_signature": self.policy_signature,
            "profile_signature": self.profile_signature,
            "embedding_signature": self.embedding_signature,
            "embedding_contract": dict(self.embedding_contract),
            "lexical_signature": self.lexical_signature,
            "keyword_dictionary": dict(self.keyword_dictionary),
        }


@dataclass(frozen=True)
class ActiveSnapshot:
    """지금 별칭이 가리키는 활성 세대의 모습. 벡터는 담지 않고 판단에 필요한 지문만 담음."""

    index: str  # 활성 세대의 실제 인덱스 이름
    manifest: Mapping[str, Any]  # 그 세대를 만들 때 기록한 RunContract(_meta)
    text_hash_by_id: Mapping[str, str]  # {chunk_id: text_hash}
    id_by_text_hash: Mapping[str, str]  # {text_hash: 그 본문을 가진 첫 chunk_id}


@dataclass(frozen=True)
class WriteReport:
    """③단계가 문서별로 몇 건을 지우고 몇 건을 넣었는지 알려 줌."""

    deleted: int  # delete_by_query로 지운 옛 청크 수
    indexed: int  # bulk로 새로 넣은 청크 수
    documents: tuple[str, ...]  # 이번에 건드린 문서(doc_id) 목록


def document_id_of(chunk: Mapping[str, Any]) -> str:
    """청크가 속한 문서 하나를 가리키는 doc_id를 뽑음.

    목적: "문서 단위로 넣고 지움"을 하려면 청크마다 어느 문서 소속인지 알아야 함.
    방법: chunk_id가 `{문서키}_{본문해시16}_{순번4}` 꼴이므로 뒤 두 칸을 떼어 문서키만 남김.
      본문이 바뀌면 chunk_id도 바뀌지만 문서키는 그대로라서 옛 청크를 정확히 찾아 지울 수 있음.
    반환값: 예) "D3_C-20260814-001".
    부수효과: 없음.
    """

    return str(chunk["chunk_id"]).rsplit("_", 2)[0]


def index_text_of(chunk: Mapping[str, Any]) -> str:
    """임베딩과 키워드 분석에 함께 넣을 색인용 본문을 돌려줌.

    머리말이 붙은 청크는 index_text를, 없으면 원래 text를 씀. 1-a의 PreparedChunk 규칙과 같음.
    """

    return str(chunk.get("index_text") or chunk["text"])


def text_hash_of(chunk: Mapping[str, Any]) -> str:
    """"같은 정제 본문인가"를 판정할 본문 지문을 만듦.

    목적: 메타데이터나 청크 ID가 바뀌어도 본문이 같으면 벡터의 뜻은 같으므로 본문만으로 지문을 냄.
    방법: 색인용 본문(머리말 포함)의 SHA-256을 구함. 1-a 인덱서의 text_hash와 같은 규칙임.
      모델이나 임베딩 설정 변경은 지문이 아닌 1번 판단(check1_reusable_run)이 따로 맡음.
    반환값: 64자 16진 문자열임.
    부수효과: 없음.
    """

    return hashlib.sha256(index_text_of(chunk).encode("utf-8")).hexdigest()


def make_embedding_contract(embedder: HuggingFaceEmbedder) -> dict[str, Any]:
    """벡터를 재사용해도 되는지 판단할 임베딩 설정 묶음을 만듦.

    1-a 설정(settings.embedding_contract)과 같은 항목임. 모델 이름이 같아도 revision이나
    입력 상한(max_seq_length)이 바뀌면 같은 본문에서 다른 벡터가 나오므로 모두 비교 대상에 넣음.
    부수효과: 차원을 읽으려고 최초 호출 때 모델을 메모리에 올림.
    """

    return {
        "model": embedder.model_name,
        "revision": embedder.revision,
        "max_seq_length": embedder.max_seq_length,
        "dimension": embedder.dimension,
        "normalize_embeddings": True,
        "pooling": "sentence-transformers-colbert-conversion-single-vector",
    }


# ---------------------------------------------------------------------------
# 단계 ① 청크 임베딩(바뀐 것만)
#   사전 검사 -> 1번 재사용 가능한 실행인가 -> 2번 같은 정제 본문이 있나 -> 3번 고른 기존 벡터가 있나
# ---------------------------------------------------------------------------


def load_active_snapshot(client: OpenSearch, name: str) -> ActiveSnapshot | None:
    """활성 세대의 기록(_meta)과 청크별 본문 지문을 읽어 옴.

    목적: 사전 검사와 1번, 2번 판단은 벡터 없이 지문만으로 하므로 벡터는 읽지 않음.
      벡터는 3번에서 재사용하기로 고른 청크만 따로 조회함.
    인자: name은 별칭 또는 인덱스 이름임. 별칭이면 지금 가리키는 인덱스를 씀.
    반환값: 활성 세대가 없으면(첫 실행) None임.
    예외: 검색 엔진 접속 실패는 호출자에게 그대로 전달함.
    부수효과: 인덱스를 읽기만 함.
    """

    targets = resolve_alias(client, name)
    if not targets:
        if not client.indices.exists(index=name):
            return None
        targets = [name]
    index = targets[0]
    mappings = client.indices.get_mapping(index=index)[index]["mappings"]
    text_hash_by_id: dict[str, str] = {}
    id_by_text_hash: dict[str, str] = {}
    for hit in helpers.scan(
        client,
        index=index,
        query={"query": {"match_all": {}}, "_source": ["chunk_id", "text_hash"]},
        preserve_order=False,
        size=1000,
    ):
        chunk_id = str(hit["_source"]["chunk_id"])
        digest = str(hit["_source"]["text_hash"])
        text_hash_by_id[chunk_id] = digest
        id_by_text_hash.setdefault(digest, chunk_id)
    return ActiveSnapshot(
        index=index,
        manifest=dict(mappings.get("_meta") or {}),
        text_hash_by_id=text_hash_by_id,
        id_by_text_hash=id_by_text_hash,
    )


def precheck_skip_run(
    active: ActiveSnapshot | None,
    run: RunContract,
    *,
    full_reindex: bool,
) -> bool:
    """사전 검사: 이번 실행 전체를 건너뛰어도 되는지 판정함.

    목적: 아무것도 바뀌지 않았는데 새 세대를 만들고 청크를 하나씩 따지는 일을 통째로 생략하기 위함.
    방법: 원천 문서, 문서 처리 정책, 문서 프로필, 임베딩 설정이 활성 세대 기록과 모두 같고
      전체 재색인 요청이 아니면 참을 돌려줌.
    반환값: 참이면 새 세대를 만들지 않고 지금 세대를 그대로 씀.
    부수효과: 없음.
    """

    if active is None or full_reindex:
        return False
    recorded = active.manifest
    expected = run.to_meta()
    return all(
        recorded.get(key) == expected[key]
        for key in (
            "inputs_sha256",
            "policy_signature",
            "profile_signature",
            "embedding_signature",
            "embedding_contract",
            # 원천이 그대로여도 사전이나 별칭이 바뀌면 문서 낱말이 달라지므로 새 세대가 필요함.
            # 이때 벡터는 1번 판단에서 그대로 재사용됨(임베딩 설정은 그대로이기 때문).
            "lexical_signature",
        )
    )


def check1_reusable_run(
    active: ActiveSnapshot | None,
    run: RunContract,
    *,
    full_reindex: bool,
) -> bool:
    """1번: 재사용 가능한 실행인지 판정함.

    조건: 활성 세대가 있음, 모델과 임베딩 설정(서명과 embedding_contract)이 같음, 강제 재색인이 아님.
    이유: 서명 문자열만 보면 모델 이름이 같고 입력 상한만 바뀐 경우를 놓쳐 옛 벡터를 잘못 재사용함.
    반환값: 거짓이면 이번 대상 청크 전부를 새로 임베딩함.
    부수효과: 없음.
    """

    if active is None or full_reindex:
        return False
    recorded = active.manifest
    return (
        recorded.get("embedding_signature") == run.embedding_signature
        and recorded.get("embedding_contract") == dict(run.embedding_contract)
    )


def check2_find_same_text(chunk: Mapping[str, Any], active: ActiveSnapshot) -> str | None:
    """2번: 활성 세대에 같은 정제 본문이 있는지 찾아 그 청크 ID를 돌려줌.

    방법: 같은 ID에 같은 text_hash가 있으면 그 ID를 먼저 고름. 없으면 ID가 달라도
      같은 text_hash를 가진 청크를 고름(앞 청크가 빠져 순번이 밀린 경우 등).
    반환값: 재사용할 기존 청크 ID, 없으면 None임.
    부수효과: 없음.
    """

    chunk_id = str(chunk["chunk_id"])
    digest = text_hash_of(chunk)
    if active.text_hash_by_id.get(chunk_id) == digest:
        return chunk_id
    return active.id_by_text_hash.get(digest)


def check3_get_vectors(
    client: OpenSearch,
    index: str,
    chunk_ids: Sequence[str],
) -> dict[str, list[float]]:
    """3번: 2번에서 고른 기존 청크의 벡터를 실제로 조회함.

    목적: 지문을 읽은 뒤 벡터를 읽기 전에 그 청크가 지워졌을 수 있으므로 실제 조회 결과로 확인함.
    방법: mget으로 고른 ID만 집어 옴. 활성 세대를 통째로 훑지 않으므로 말뭉치가 커도 바뀐 양만큼만 읽음.
    반환값: {chunk_id: 벡터} 표이며 조회되지 않은 ID는 빠져 있음.
    예외: 검색 엔진 접속 실패는 호출자에게 그대로 전달함.
    부수효과: 인덱스를 읽기만 함.
    """

    found: dict[str, list[float]] = {}
    unique_ids = list(dict.fromkeys(chunk_ids))
    for start in range(0, len(unique_ids), 500):
        batch = unique_ids[start:start + 500]
        response = client.mget(
            index=index,
            body={"docs": [{"_id": chunk_id, "_source": ["embedding"]} for chunk_id in batch]},
        )
        for doc in response["docs"]:
            if doc.get("found"):
                found[str(doc["_id"])] = list(doc["_source"]["embedding"])
    return found


def step1_embed_changed_chunks(
    chunks: Sequence[Mapping[str, Any]],
    *,
    client: OpenSearch,
    active: ActiveSnapshot | None,
    run: RunContract,
    embed: Callable[[list[str]], list[list[float]]],
    full_reindex: bool = False,
) -> tuple[dict[str, list[float]], EmbedReport]:
    """① 청크별 판단 순서(1번, 2번, 3번)를 거쳐 바뀐 청크만 임베딩하고 나머지는 기존 벡터를 씀.

    목적: 임베딩이 이 파이프라인에서 가장 느리고 비싼 구간이라 모델, 설정, 본문이 같으면 다시 계산하지 않음.
    인자: active는 load_active_snapshot 결과이며, 사전 검사는 이 함수를 부르기 전에 build_generation이 끝냄.
    반환값: ({chunk_id: 벡터}, 새로 만든 ID, 재사용 ID, 청크별 판단 결과를 담은 보고)임.
    예외: 임베딩 호출 실패나 입출력 건수 불일치를 호출자에게 전달함.
    부수효과: 활성 세대에서 고른 벡터를 읽고, 새로 임베딩할 청크가 있으면 모델로 추론함.
    """

    reasons: dict[str, str] = {}
    reuse_sources: dict[str, str] = {}  # {이번 chunk_id: 벡터를 가져올 기존 chunk_id}
    old_vectors: dict[str, list[float]] = {}

    if active is None or not check1_reusable_run(active, run, full_reindex=full_reindex):
        for chunk in chunks:
            reasons[str(chunk["chunk_id"])] = NEW_NOT_REUSABLE_RUN
    else:
        for chunk in chunks:
            chunk_id = str(chunk["chunk_id"])
            source_id = check2_find_same_text(chunk, active)
            if source_id is None:
                reasons[chunk_id] = NEW_NO_SAME_TEXT
                continue
            reuse_sources[chunk_id] = source_id
            reasons[chunk_id] = REUSE_SAME_ID if source_id == chunk_id else REUSE_SAME_TEXT
        old_vectors = check3_get_vectors(client, active.index, list(reuse_sources.values()))
        for chunk_id, source_id in list(reuse_sources.items()):
            if source_id not in old_vectors:
                reasons[chunk_id] = NEW_VECTOR_MISSING
                del reuse_sources[chunk_id]

    vectors = {chunk_id: old_vectors[source_id] for chunk_id, source_id in reuse_sources.items()}
    pending = [chunk for chunk in chunks if str(chunk["chunk_id"]) not in reuse_sources]
    if pending:
        fresh = embed([index_text_of(chunk) for chunk in pending])
        if len(fresh) != len(pending):
            raise ValueError("임베딩 입력과 출력 건수가 다릅니다.")
        vectors.update(
            (str(chunk["chunk_id"]), list(vector)) for chunk, vector in zip(pending, fresh, strict=True)
        )
    report = EmbedReport(
        embedded_ids=tuple(str(chunk["chunk_id"]) for chunk in pending),
        reused_ids=tuple(reuse_sources),
        reasons=reasons,
    )
    return vectors, report


# ---------------------------------------------------------------------------
# 단계 ② 키워드 분석(nori 또는 Kiwi 낱말)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeywordDictionary:
    """키워드 분석에 쓰는 카드명 사전과 별칭 치환표 묶음.

    두 사전은 한 쌍으로 씀. 카드명 사전만 넣으면 문서에는 "한빛가족돌봄" 한 낱말만 남는데,
    "가족돌봄"이라고만 묻는 질문은 "가족", "돌봄"으로 잘려 카드명 낱말과 겹치지 않음.
    별칭 치환표가 줄여 부른 이름을 정식 카드명 낱말로 바꿔 이 틈을 메움.
    """

    card_words: tuple[tuple[str, str, float], ...]  # (띄어 쓴 카드명, 품사 NNP, Kiwi 등록 가중치)
    aliases: tuple[tuple[str, str], ...]  # (별칭 표면형, 정식 카드 낱말). 예) ("가족돌봄", "한빛가족돌봄")
    rejected: tuple[tuple[str, str], ...]  # 자동으로 뺀 별칭과 사유. 예) ("장보기", "common_noun")

    def make_tokenizer(self) -> KoreanTokenizer:
        """이 사전으로 Kiwi 토크나이저를 만듦. 색인 쪽과 검색 쪽이 같은 함수를 거쳐 같은 토크나이저를 얻음."""

        return KoreanTokenizer(additional_user_words=self.card_words, aliases=dict(self.aliases))

    def to_meta(self) -> dict[str, Any]:
        """인덱스 `_meta`에 넣을 모양으로 바꿈. 별칭은 공백이 든 키가 있어 [표면형, 정식 낱말] 쌍 목록으로 둠."""

        return {
            "card_words": [list(word) for word in self.card_words],
            "aliases": [list(pair) for pair in self.aliases],
            "rejected": [list(pair) for pair in self.rejected],
        }

    @classmethod
    def from_meta(cls, value: Mapping[str, Any]) -> "KeywordDictionary":
        """`_meta`에서 읽은 값을 다시 사전 묶음으로 바꿈."""

        return cls(
            card_words=tuple((str(w[0]), str(w[1]), float(w[2])) for w in value.get("card_words", [])),
            aliases=tuple((str(a[0]), str(a[1])) for a in value.get("aliases", [])),
            rejected=tuple((str(r[0]), str(r[1])) for r in value.get("rejected", [])),
        )


def load_alias_policy(config_dir: Path) -> AliasPolicy:
    """1-a와 같은 설정 파일(별칭 생성 규칙, 사람 검수 목록)로 별칭 정책을 만듦.

    인자: config_dir에는 card_alias_rules.json과 card_alias_overrides.json이 있어야 함.
    반환값: 토큰화와 같은 규칙으로 정규화된 정책임. 파일 지문도 함께 담아 바뀌었는지 알 수 있게 함.
    예외: 파일이 없거나 JSON 모양이 틀리면 그대로 전달함.
    부수효과: 설정 파일 두 개를 읽음.
    """

    rules_path = config_dir / "card_alias_rules.json"
    overrides_path = config_dir / "card_alias_overrides.json"
    rules = json.loads(rules_path.read_text(encoding="utf-8"))
    overrides = json.loads(overrides_path.read_text(encoding="utf-8"))
    policy = AliasPolicy(
        rules=AliasRules(
            brand_prefixes=tuple(str(v) for v in rules.get("brand_prefixes", [])),
            suffixes=tuple(str(v) for v in rules.get("suffixes", [])),
            min_length=int(rules.get("min_length", 3)),
        ),
        overrides=AliasOverrides.from_mapping(overrides.get("include"), overrides.get("exclude")),
        rules_sha256=hashlib.sha256(rules_path.read_bytes()).hexdigest(),
        overrides_sha256=hashlib.sha256(overrides_path.read_bytes()).hexdigest(),
    )
    return _normalized_alias_policy(policy)


def build_keyword_dictionary(
    chunks: Sequence[Mapping[str, Any]],
    policy: AliasPolicy,
    *,
    is_common_noun: Callable[[str], bool] | None = None,
) -> KeywordDictionary:
    """이번에 색인할 청크에서 카드명 사전과 별칭 치환표를 만듦(1-a와 같은 규칙).

    방법: 혜택 안내서(D2) 메타데이터의 카드명을 고유명사로 모으고, 접두어와 접미어를 떼어 별칭 후보를 만든 뒤
      일반 명사와 같은 별칭(예: 장보기)은 자동으로 뺌. 그대로 두면 "장보기 할인" 같은 일반 질문이
      특정 카드명으로 바뀌어 버리기 때문임. 사람 검수 목록(추가, 제외)은 마지막에 덮어씀.
    인자: is_common_noun이 없으면 사용자 사전 없는 Kiwi로 일반 명사 여부를 판정함.
    반환값: 카드명 사전, 채택한 별칭, 자동으로 뺀 별칭과 사유를 담은 묶음임.
    예외: 같은 카드 ID에 다른 카드명이 있으면 ValueError를 전달함.
    부수효과: 판정기를 넘기지 않으면 Kiwi를 한 번 메모리에 올림.
    """

    words = _card_dictionary_words(chunks)
    plan = build_alias_plan(
        [name for name, _tag, _score in words],
        rules=policy.rules,
        overrides=policy.overrides,
        is_common_noun=is_common_noun or PlainNounChecker(),
    )
    return KeywordDictionary(
        card_words=tuple(words),
        aliases=tuple(plan.surface_mapping().items()),
        rejected=tuple((item.alias, item.reason) for item in plan.rejected),
    )


def load_query_tokenizer(client: OpenSearch, alias: str) -> KoreanTokenizer:
    """검색 쪽 토크나이저를 활성 세대의 `_meta`에서 다시 만듦.

    목적: 질문을 색인 때와 다른 사전으로 자르면 아무 오류 없이 검색만 조용히 어긋나므로,
      색인한 세대가 기록한 사전으로만 토크나이저를 만들고 서명까지 대조함.
    반환값: 활성 세대와 같은 사전과 별칭을 가진 토크나이저임.
    예외: 활성 세대가 없거나 다시 만든 토크나이저의 서명이 기록과 다르면 ValueError를 냄.
    부수효과: 인덱스 매핑을 읽고 Kiwi를 메모리에 올림.
    """

    active = load_active_snapshot(client, alias)
    if active is None:
        raise ValueError(f"활성 세대가 없습니다: {alias}")
    tokenizer = KeywordDictionary.from_meta(active.manifest.get("keyword_dictionary") or {}).make_tokenizer()
    if tokenizer.signature != active.manifest.get("lexical_signature"):
        raise ValueError("검색 쪽 토크나이저 서명이 색인 세대와 다릅니다.")
    return tokenizer


def step2_analyze_keywords(
    chunks: Sequence[Mapping[str, Any]],
    tokenizer: KoreanTokenizer,
) -> dict[str, str]:
    """② 한국어 본문을 BM25가 셀 수 있는 낱말로 잘라 공백으로 이어 붙임(Kiwi 방식).

    목적: 한국어는 띄어쓰기만으로 낱말이 나뉘지 않아 "카드로", "카드는"이 서로 다른 말이 되어 버림.
    방법: 파이썬 쪽 Kiwi로 내용어만 뽑아 공백으로 잇고, 엔진에는 whitespace 분석기로 그대로 넣음.
      엔진은 공백만 보면 되므로 색인 쪽과 질문 쪽이 똑같은 사전과 정책을 쓰게 됨.
    인자: tokenizer는 KeywordDictionary.make_tokenizer()로 만든 것이며, 질문은 load_query_tokenizer로
      같은 사전의 토크나이저를 얻어 자름.
    반환값: {chunk_id: "낱말 낱말 낱말"} 표임.
    부수효과: 형태소 분석기를 메모리에서 사용함.
    """

    texts = [index_text_of(chunk) for chunk in chunks]
    token_lists = tokenizer.tokenize_many(texts)
    return {
        str(chunk["chunk_id"]): " ".join(tokens)
        for chunk, tokens in zip(chunks, token_lists, strict=True)
    }


#: nori 방식 참고 매핑임. 엔진 안에서 한국어를 자르므로 파이썬이 낱말을 만들지 않음.
#: 쓰려면 컨테이너에 `opensearch-plugin install analysis-nori`로 플러그인을 먼저 깔아야 함.
NORI_MAPPING_EXAMPLE: dict[str, Any] = {
    "settings": {
        "index": {"knn": True},
        "analysis": {
            "tokenizer": {
                "korean_nori": {
                    "type": "nori_tokenizer",
                    "decompound_mode": "mixed",
                    # 사용자 사전은 컨테이너 안 파일 경로로만 줄 수 있어 배포 때 함께 올려야 함.
                    "user_dictionary": "userdict_ko.txt",
                }
            },
            "filter": {
                "korean_pos_filter": {
                    # 조사·어미처럼 뜻이 없는 품사를 떨어냄. Kiwi의 내용어 필터와 같은 목적임.
                    "type": "nori_part_of_speech",
                    "stoptags": ["E", "IC", "J", "MAG", "MAJ", "MM", "SP", "SSC", "SSO", "SC", "SE", "XPN", "XSA", "XSN", "XSV", "UNA", "NA", "VSV"],
                }
            },
            "analyzer": {
                "korean": {
                    "type": "custom",
                    "tokenizer": "korean_nori",
                    "filter": ["korean_pos_filter", "lowercase", "nori_readingform"],
                }
            },
        },
    },
    "mappings": {
        "properties": {
            # nori 방식에서는 원문 text 필드에 분석기를 직접 걸고 text_tokens 필드를 두지 않음.
            "text": {"type": "text", "analyzer": "korean"},
        }
    },
}


# ---------------------------------------------------------------------------
# 단계 ③ 검색 엔진에 쓰기(문서 단위로 넣고 지움)
# ---------------------------------------------------------------------------


def generation_index_name(alias: str, generation: str) -> str:
    """세대별 실제 인덱스 이름을 만듦. 예) card_chunks-gen-20261019-ab12."""

    return f"{alias}-{generation}"


def build_index_mapping(dimension: int, manifest: Mapping[str, Any]) -> dict[str, Any]:
    """세대 인덱스 하나의 설정과 필드 정의를 만듦.

    목적: 하이브리드(BM25 + 벡터)와 회원 필터를 한 인덱스에서 같이 하기 위함.
    방법: BM25는 whitespace로 자르는 text_tokens가 맡고, 벡터는 코사인 거리의 knn_vector가 맡음.
      거르기에 쓰는 값은 모두 keyword로 둬서 분석기가 쪼개지 않게 함.
      이 세대를 만든 실행 기록(RunContract)은 `_meta`에 남겨 다음 실행의 사전 검사와 1번 판단이 읽게 함.
    인자: dimension은 임베딩 모델의 실제 출력 차원임(KURE-v2는 768). manifest는 RunContract.to_meta() 값임.
    반환값: indices.create의 body로 그대로 넣을 수 있는 설정임.
    부수효과: 없음.
    """

    keyword_properties = {name: {"type": "keyword"} for name in KEYWORD_METADATA_FIELDS}
    return {
        "settings": {
            "index": {
                "knn": True,  # 이 설정이 있어야 knn_vector 필드를 검색할 수 있음
                "number_of_shards": 1,
                "number_of_replicas": 0,  # 단일 노드 실습이라 복제본을 두지 않음
                "refresh_interval": "1s",
                # 기본 BM25(k1 1.2)가 아닌 1-a와 같은 조절값을 이름 붙여 정의하고 text_tokens 필드에 검.
                "similarity": {BM25_SIMILARITY: {"type": "BM25", "k1": BM25_K1, "b": BM25_B}},
            }
        },
        "mappings": {
            "dynamic": "strict",  # 모르는 필드가 섞여 들어와 매핑이 번지는 일을 막음
            "_meta": dict(manifest),
            "properties": {
                "chunk_id": {"type": "keyword"},
                "doc_id": {"type": "keyword"},
                "text_hash": {"type": "keyword"},  # 2번 판단(같은 정제 본문)의 비교 대상
                # 원문은 보여 주기와 인용 검증용임. 검색 점수는 text_tokens가 냄.
                "text": {"type": "text", "index": False},
                "text_tokens": {"type": "text", "analyzer": "whitespace", "similarity": BM25_SIMILARITY},
                "embedding": {
                    "type": "knn_vector",
                    "dimension": int(dimension),
                    "method": {
                        "name": "hnsw",
                        "engine": "lucene",
                        # 임베딩이 L2 정규화돼 있어 코사인 거리가 맞음.
                        "space_type": "cosinesimil",
                        "parameters": {"ef_construction": 128, "m": 16},
                    },
                },
                **keyword_properties,
            },
        },
    }


def create_generation_index(
    client: OpenSearch,
    index: str,
    dimension: int,
    manifest: Mapping[str, Any],
) -> None:
    """세대 인덱스를 만듦. 같은 이름이 이미 있으면 그대로 두어 다시 돌려도 안전하게 함."""

    if client.indices.exists(index=index):
        return
    client.indices.create(index=index, body=build_index_mapping(dimension, manifest))


def to_engine_document(
    chunk: Mapping[str, Any],
    *,
    vector: Sequence[float],
    tokens: str,
) -> dict[str, Any]:
    """청크 하나를 검색 엔진에 넣을 문서 모양으로 바꿈.

    벡터를 재사용한 청크도 메타데이터는 이번 입력의 최신 값으로 다시 씀(장표: 최신 메타데이터와 함께 다시 적재).
    """

    metadata = dict(chunk.get("metadata") or {})
    document: dict[str, Any] = {
        "chunk_id": str(chunk["chunk_id"]),
        "doc_id": document_id_of(chunk),
        "text_hash": text_hash_of(chunk),
        "text": str(chunk["text"]),
        "text_tokens": tokens,
        "embedding": list(vector),
    }
    for name in KEYWORD_METADATA_FIELDS:
        value = metadata.get(name)
        if value is not None:
            document[name] = str(value)
    return document


def step3_write_documents(
    client: OpenSearch,
    index: str,
    documents: Iterable[Mapping[str, Any]],
) -> WriteReport:
    """③ 문서 단위로 옛 청크를 지우고 새 청크를 한꺼번에 넣음.

    목적: 고쳐 쓴 문서의 청크 수가 줄면 옛 청크가 주인 없이 남아(고아) 검색에 섞여 나옴.
      그래서 "낱개 수정"이 아니라 "그 문서 통째로 지우고 다시 넣기"로 처리함.
    방법: 문서별로 delete_by_query(term doc_id)를 먼저 돌리고 bulk로 새 청크를 넣음.
      _id를 chunk_id로 고정해 같은 입력을 두 번 넣어도 건수가 늘지 않게 함(멱등).
    인자: documents는 to_engine_document가 만든 문서들이며 여러 문서가 섞여 있어도 됨.
    반환값: 지운 건수, 넣은 건수, 건드린 문서 목록임.
    예외: bulk 일부 실패 시 BulkIndexError를 호출자에게 전달함.
    부수효과: 대상 인덱스만 바꾸며 별칭과 다른 세대는 건드리지 않음.
    """

    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for document in documents:
        grouped.setdefault(str(document["doc_id"]), []).append(document)
    if not grouped:
        return WriteReport(0, 0, ())

    deleted = 0
    for doc_id in grouped:
        response = client.delete_by_query(
            index=index,
            body={"query": {"term": {"doc_id": doc_id}}},
            refresh=True,
            conflicts="proceed",
        )
        deleted += int(response.get("deleted", 0))

    actions = [
        {"_index": index, "_id": document["chunk_id"], "_source": dict(document)}
        for chunk_documents in grouped.values()
        for document in chunk_documents
    ]
    helpers.bulk(client, actions, max_retries=3)
    client.indices.refresh(index=index)
    return WriteReport(deleted, len(actions), tuple(grouped))


# ---------------------------------------------------------------------------
# 단계 ④ 별칭 전환(세대)
# ---------------------------------------------------------------------------


def resolve_alias(client: OpenSearch, alias: str) -> list[str]:
    """별칭이 지금 어느 인덱스를 가리키는지 돌려줌. 없으면 빈 목록임."""

    if not client.indices.exists_alias(name=alias):
        return []
    return sorted(client.indices.get_alias(name=alias).keys())


def step4_switch_alias(client: OpenSearch, alias: str, new_index: str) -> dict[str, Any]:
    """④ 별칭을 새 세대로 한 번에 옮김.

    목적: 새 세대를 다 만든 뒤 검색이 바라보는 곳을 바꿔야 반쯤 만들어진 색인이 노출되지 않음.
    방법: remove와 add를 한 요청(update_aliases)에 함께 넣음. 두 번 나눠 부르면
      그 사이에 별칭이 아무것도 가리키지 않는 순간이 생겨 검색이 빈손으로 돌아옴.
    인자: new_index는 건수 확인까지 끝난 세대 인덱스여야 함.
    반환값: 옮기기 전후 인덱스와 엔진 응답을 담은 기록임.
    예외: 대상 인덱스가 없거나 전환에 실패하면 예외를 호출자에게 전달함.
    부수효과: 별칭만 바꿈. 옛 세대 인덱스는 지우지 않아 되돌릴 수 있음.
    """

    if not client.indices.exists(index=new_index):
        raise ValueError(f"별칭을 옮길 인덱스가 없습니다: {new_index}")
    previous = resolve_alias(client, alias)
    actions: list[dict[str, Any]] = [
        {"remove": {"index": name, "alias": alias}} for name in previous if name != new_index
    ]
    if new_index not in previous:
        actions.append({"add": {"index": new_index, "alias": alias}})
    response: dict[str, Any] = {"acknowledged": True, "skipped": True}
    if actions:
        response = client.indices.update_aliases(body={"actions": actions})
    return {"alias": alias, "from": previous, "to": [new_index], "response": response}


def verify_generation(client: OpenSearch, index: str, expected: int) -> int:
    """별칭을 옮기기 전에 세대 인덱스의 건수가 기대와 같은지 확인함.

    예외: 건수가 다르면 ValueError를 내어 덜 만들어진 세대로 전환하는 일을 막음.
    부수효과: refresh를 호출해 아직 반영되지 않은 쓰기를 눈에 보이게 함.
    """

    client.indices.refresh(index=index)
    actual = int(client.count(index=index)["count"])
    if actual != int(expected):
        raise ValueError(f"세대 건수가 다릅니다: index={index}, expected={expected}, actual={actual}")
    return actual


# ---------------------------------------------------------------------------
# 네 단계를 묶은 세대 만들기
# ---------------------------------------------------------------------------


def build_generation(
    client: OpenSearch,
    *,
    alias: str,
    generation: str,
    chunks: Sequence[Mapping[str, Any]],
    embed: Callable[[list[str]], list[list[float]]],
    run: RunContract,
    dimension: int,
    full_reindex: bool = False,
) -> dict[str, Any]:
    """사전 검사 뒤 ①~③을 순서대로 돌려 새 세대 인덱스를 완성함(별칭은 아직 옮기지 않음).

    인자: run은 이번 실행의 입력과 설정 기록이며 새 세대의 `_meta`에 남음.
      ②의 토크나이저는 run.keyword_dictionary로 만들어, `_meta`에 남는 사전과 실제로 쓴 사전이 어긋나지 않게 함.
      full_reindex가 참이면 사전 검사와 벡터 재사용을 모두 건너뛰고 전부 새로 임베딩함.
    예외: run의 사전으로 만든 토크나이저 서명이 run.lexical_signature와 다르면 ValueError를 냄.
    반환값: skipped가 참이면 사전 검사로 생략한 것이며 index는 지금 활성 세대임.
      거짓이면 새 세대 인덱스 이름, 임베딩 보고, 쓰기 보고, 확인한 건수를 담음.
    부수효과: 생략하지 않으면 새 세대 인덱스를 만들고 채움. 현재 별칭과 옛 세대는 그대로 둠.
    """

    active = load_active_snapshot(client, alias)
    if active is not None and precheck_skip_run(active, run, full_reindex=full_reindex):
        return {"skipped": True, "index": active.index}

    index = generation_index_name(alias, generation)
    vectors, embed_report = step1_embed_changed_chunks(
        chunks,
        client=client,
        active=active,
        run=run,
        embed=embed,
        full_reindex=full_reindex,
    )
    tokenizer = KeywordDictionary.from_meta(run.keyword_dictionary).make_tokenizer()
    if tokenizer.signature != run.lexical_signature:
        raise ValueError("실행 기록의 토크나이저 서명과 실제 사전이 다릅니다.")
    tokens = step2_analyze_keywords(chunks, tokenizer)
    create_generation_index(client, index, dimension, run.to_meta())
    documents = [
        to_engine_document(
            chunk,
            vector=vectors[str(chunk["chunk_id"])],
            tokens=tokens[str(chunk["chunk_id"])],
        )
        for chunk in chunks
    ]
    write_report = step3_write_documents(client, index, documents)
    count = verify_generation(client, index, len(chunks))
    return {
        "skipped": False,
        "index": index,
        "embed": embed_report,
        "write": write_report,
        "count": count,
    }


# ---------------------------------------------------------------------------
# 검색(별칭에만 질의함)
# ---------------------------------------------------------------------------


def _member_filter(member_id: str | None) -> list[dict[str, Any]]:
    """회원 필터를 쓰면 그 회원의 청크만 보게 하는 조건을 만듦."""

    return [{"term": {MEMBER_FIELD: member_id}}] if member_id else []


def search_bm25(
    client: OpenSearch,
    alias: str,
    question: str,
    tokenizer: KoreanTokenizer,
    *,
    member_id: str | None = None,
    size: int = 5,
) -> list[dict[str, Any]]:
    """BM25만으로 찾음. 질문도 색인 때와 같은 Kiwi 낱말로 잘라 넣음."""

    query_tokens = " ".join(tokenizer.tokenize(question))
    body = {
        "size": size,
        "_source": ["chunk_id", "doc_id", "doc_key", MEMBER_FIELD],
        "query": {
            "bool": {
                "must": [{"match": {"text_tokens": {"query": query_tokens, "analyzer": "whitespace"}}}],
                "filter": _member_filter(member_id),
            }
        },
    }
    return client.search(index=alias, body=body)["hits"]["hits"]


def search_knn(
    client: OpenSearch,
    alias: str,
    question: str,
    embed: Callable[[list[str]], list[list[float]]],
    *,
    member_id: str | None = None,
    size: int = 5,
) -> list[dict[str, Any]]:
    """벡터만으로 찾음. 회원 필터는 knn 안쪽 filter에 넣어야 거른 뒤 이웃을 뽑음."""

    vector = embed([question])[0]
    knn: dict[str, Any] = {"vector": vector, "k": size}
    if member_id:
        knn["filter"] = {"term": {MEMBER_FIELD: member_id}}
    body = {
        "size": size,
        "_source": ["chunk_id", "doc_id", "doc_key", MEMBER_FIELD],
        "query": {"knn": {"embedding": knn}},
    }
    return client.search(index=alias, body=body)["hits"]["hits"]


def search_hybrid(
    client: OpenSearch,
    alias: str,
    question: str,
    tokenizer: KoreanTokenizer,
    embed: Callable[[list[str]], list[list[float]]],
    *,
    member_id: str | None = None,
    size: int = 5,
) -> list[dict[str, Any]]:
    """BM25와 벡터를 함께 써서 찾음(회원 필터 포함).

    방법: bool.should 안에 match와 knn을 나란히 두어 둘 중 하나만 맞아도 후보로 올림.
    한계: 두 점수의 눈금이 달라 단순히 더해짐. 실서비스에서는 hybrid 질의와
      normalization-processor 검색 파이프라인을 붙여 점수를 0~1로 맞춰 합치는 쪽이 맞음.
    """

    query_tokens = " ".join(tokenizer.tokenize(question))
    vector = embed([question])[0]
    knn: dict[str, Any] = {"vector": vector, "k": size}
    if member_id:
        knn["filter"] = {"term": {MEMBER_FIELD: member_id}}
    body = {
        "size": size,
        "_source": ["chunk_id", "doc_id", "doc_key", MEMBER_FIELD],
        "query": {
            "bool": {
                "should": [
                    {"match": {"text_tokens": {"query": query_tokens, "analyzer": "whitespace"}}},
                    {"knn": {"embedding": knn}},
                ],
                "filter": _member_filter(member_id),
                "minimum_should_match": 1,
            }
        },
    }
    return client.search(index=alias, body=body)["hits"]["hits"]


# ---------------------------------------------------------------------------
# 조립
# ---------------------------------------------------------------------------


def make_client(url: str | None = None) -> OpenSearch:
    """검색 엔진 접속 객체를 만듦. 주소는 환경변수로만 받고 코드에 박지 않음."""

    return OpenSearch(
        hosts=[url or os.environ.get("OPENSEARCH_URL", "http://localhost:9200")],
        http_compress=True,
        timeout=60,
        max_retries=3,
        retry_on_timeout=True,
    )


def make_embedder() -> HuggingFaceEmbedder:
    """1-a와 같은 계약(KURE-v2, 768차원, L2 정규화)의 임베더를 만듦."""

    return HuggingFaceEmbedder(
        model_name=os.environ.get("EMBED_MODEL", "nlpai-lab/KURE-v2"),
        revision=os.environ.get("EMBED_REVISION", "3431f86d399d666083890dbb882aced6708873bc"),
        max_seq_length=int(os.environ.get("EMBED_MAX_TOKENS", "800")),
        batch_size=int(os.environ.get("EMBED_BATCH_SIZE", "8")),
        device=os.environ.get("EMBED_DEVICE", "cpu"),
        local_files_only=os.environ.get("HF_LOCAL_FILES_ONLY", "true").lower() == "true",
        expected_dimension=int(os.environ.get("EMBED_DIMENSION", "768")),
    )


__all__ = [
    "DEFAULT_ALIAS",
    "ActiveSnapshot",
    "BM25_B",
    "BM25_K1",
    "EmbedReport",
    "KeywordDictionary",
    "NEW_NOT_REUSABLE_RUN",
    "NEW_NO_SAME_TEXT",
    "NEW_VECTOR_MISSING",
    "NORI_MAPPING_EXAMPLE",
    "REUSE_SAME_ID",
    "REUSE_SAME_TEXT",
    "RunContract",
    "WriteReport",
    "build_generation",
    "build_index_mapping",
    "build_keyword_dictionary",
    "check1_reusable_run",
    "check2_find_same_text",
    "check3_get_vectors",
    "create_generation_index",
    "document_id_of",
    "generation_index_name",
    "load_active_snapshot",
    "load_alias_policy",
    "load_query_tokenizer",
    "make_client",
    "make_embedder",
    "make_embedding_contract",
    "precheck_skip_run",
    "resolve_alias",
    "search_bm25",
    "search_hybrid",
    "search_knn",
    "step1_embed_changed_chunks",
    "step2_analyze_keywords",
    "step3_write_documents",
    "step4_switch_alias",
    "text_hash_of",
    "to_engine_document",
    "verify_generation",
]
