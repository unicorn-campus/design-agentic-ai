"""search_branch.py의 네 단계를 실제 OpenSearch에 돌려 확인하는 시험 스크립트임.

a. 1세대 전체 색인 -> 활성 세대가 없어 모두 새로 임베딩, 별칭이 1세대를 가리킴
p. 사전 검사 -> 입력과 설정이 모두 같으면 새 세대를 만들지 않고 생략
b. 2세대(문서 하나 수정 + 청크 하나 삭제) -> 바뀐 청크만 새로 임베딩, 나머지는 같은 ID로 재사용
c. 별칭 전환 뒤 BM25, kNN, 하이브리드, 회원 필터 질의, 1세대 인덱스 유지
q. 키워드 분석: 카드명 사전과 별칭, 검색 쪽 토크나이저 재생성, k1 1.5, 사전 변경 시 사전 검사
f. 증분 색인(문서 단위로 지우고 넣기) -> 고아 청크 없음
g. 2번: ID만 바뀌고 본문이 같음 -> 재사용
h. 메타데이터만 바뀜 -> 벡터 재사용, 최신 메타데이터로 다시 적재
i. 1번: 임베딩 설정(embedding_contract)만 바뀜 -> 전부 새로 임베딩
j. 1번: full_reindex -> 사전 검사 통과 못 하고 전부 새로 임베딩
k. 3번: 고른 기존 벡터가 조회 결과에 없음 -> 새로 임베딩
d. 별칭을 1세대로 되돌림
"""

from __future__ import annotations

import collections
import dataclasses
import hashlib
import io
import json
import os
import sys
from pathlib import Path
from typing import Any

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import search_branch as sb

WORK = Path(__file__).resolve().parent
LOG_PATH = WORK / "run.log"
CHUNKS_PATH = sb.LAB_ROOT / "data" / "artifacts" / "birthfix-20261018b" / "prepared-chunks.json"
CONFIG_DIR = sb.LAB_ROOT / "config"
ALIAS = "card_chunks"
GEN1 = "gen-20261019-001"
GEN2 = "gen-20261019-002"
GEN_SKIP = "gen-20261019-skip"

_log_file = io.open(LOG_PATH, "w", encoding="utf-8", newline="\n")
_failures: list[str] = []


def log(message: str = "") -> None:
    print(message)
    _log_file.write(message + "\n")
    _log_file.flush()


def check(label: str, condition: bool, detail: str = "") -> None:
    """확인 항목 하나의 통과 여부를 로그에 남김. 실패해도 멈추지 않고 끝에 모아 보고함."""

    mark = "PASS" if condition else "FAIL"
    log(f"  [{mark}] {label}" + (f" | {detail}" if detail else ""))
    if not condition:
        _failures.append(label)


def copy_chunk(chunk: dict[str, Any]) -> dict[str, Any]:
    return json.loads(json.dumps(chunk, ensure_ascii=False))


def load_sample_chunks() -> list[dict[str, Any]]:
    """문서 몇 개 분량만 골라 시험용 청크 묶음을 만듦.

    고른 이유: D1(약관) 10개는 고칠 문서로, D2(혜택) 앞 6개는 벡터 재사용 증거로,
    D2 중 한빛 가족돌봄 카드 청크는 카드명 사전과 별칭 시험용으로, D3(상담) 3개는 회원 필터 시험용으로 씀.
    """

    everything = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    d1 = [c for c in everything if sb.document_id_of(c) == "D1_27223010abe31291"]
    d2_all = [c for c in everything if c["metadata"].get("doc_key") == "D2"]
    family = [c for c in d2_all[6:] if c["metadata"].get("card_name") == "한빛 가족돌봄"]
    d2 = d2_all[:6] + family
    d3 = [c for c in everything if c["metadata"].get("doc_key") == "D3"][:3]
    return d1 + d2 + d3


def file_digest(*names: str) -> str:
    """설정 파일 내용으로 지문을 만듦. 1-a가 정책과 프로필 변경을 알아채는 근거와 같은 파일임."""

    digest = hashlib.sha256()
    for name in names:
        digest.update((CONFIG_DIR / name).read_bytes())
    return digest.hexdigest()


def make_run(chunks: list[dict[str, Any]], embedding_signature: str,
             embedding_contract: dict[str, Any], policy: sb.AliasPolicy,
             noun_checker) -> sb.RunContract:
    """시험용 실행 기록을 만듦.

    원천 문서 지문: 이 예제는 원천 파일 대신 청킹 결과를 입력으로 받으므로
    문서(doc_id)별 청크 본문을 이어 계산함. 원천이 바뀌면 이 값도 바뀌는 점은 같음.
    """

    by_doc: dict[str, list[str]] = collections.defaultdict(list)
    for chunk in sorted(chunks, key=lambda c: str(c["chunk_id"])):
        by_doc[sb.document_id_of(chunk)].append(sb.text_hash_of(chunk))
    inputs = {doc: hashlib.sha256("".join(hashes).encode()).hexdigest() for doc, hashes in by_doc.items()}
    dictionary = sb.build_keyword_dictionary(chunks, policy, is_common_noun=noun_checker)
    return sb.RunContract(
        inputs_sha256=inputs,
        policy_signature=file_digest("document_policies.json"),
        profile_signature=file_digest("document_profiles.json", "metadata_schema.json"),
        embedding_signature=embedding_signature,
        embedding_contract=embedding_contract,
        lexical_signature=dictionary.make_tokenizer().signature,
        keyword_dictionary=dictionary.to_meta(),
    )


def rebuild_chunk_id(chunk: dict[str, Any]) -> str:
    """상위 공통 단계가 본문을 바꿨을 때 만들어 낼 chunk_id를 똑같이 계산함.

    1-a 규칙: f"{문서키}_{sha256(색인용 본문)[:16]}_{순번4}".
    """

    document_key, _old_hash, ordinal = str(chunk["chunk_id"]).rsplit("_", 2)
    return f"{document_key}_{sb.text_hash_of(chunk)[:16]}_{ordinal}"


def fetch_source(client, index: str, chunk_id: str) -> dict[str, Any] | None:
    hits = client.search(
        index=index,
        body={"size": 1, "query": {"term": {"chunk_id": chunk_id}}},
    )["hits"]["hits"]
    return dict(hits[0]["_source"]) if hits else None


def fetch_vector(client, index: str, chunk_id: str) -> list[float] | None:
    source = fetch_source(client, index, chunk_id)
    return list(source["embedding"]) if source else None


def chunk_ids_in(client, index: str, doc_id: str | None = None) -> set[str]:
    query = {"term": {"doc_id": doc_id}} if doc_id else {"match_all": {}}
    return {
        hit["_source"]["chunk_id"]
        for hit in sb.helpers.scan(
            client, index=index, query={"query": query, "_source": ["chunk_id"]},
            preserve_order=False,
        )
    }


def reason_summary(report: sb.EmbedReport) -> str:
    counts = collections.Counter(report.reasons.values())
    return ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))


def write_doc(client, index: str, chunks: list[dict[str, Any]], vectors, tokenizer) -> sb.WriteReport:
    tokens = sb.step2_analyze_keywords(chunks, tokenizer)
    documents = [
        sb.to_engine_document(c, vector=vectors[str(c["chunk_id"])], tokens=tokens[str(c["chunk_id"])])
        for c in chunks
    ]
    return sb.step3_write_documents(client, index, documents)


def cleanup(client) -> None:
    """지난 실행이 남긴 시험용 인덱스와 별칭을 지움."""

    pattern = f"{ALIAS}-gen-*"
    if client.indices.exists(index=pattern):
        client.indices.delete(index=pattern)


def main() -> int:
    client = sb.make_client(os.environ.get("OPENSEARCH_URL", "http://localhost:19200"))
    info = client.info()
    import opensearchpy

    log(f"OpenSearch {info['version']['distribution']} {info['version']['number']}")
    log(f"opensearch-py {'.'.join(str(part) for part in opensearchpy.__version__)}")
    plugins = {row["component"] for row in client.cat.plugins(format="json")}
    log(f"analysis-nori 플러그인 설치됨: {'analysis-nori' in plugins} "
        f"(없으면 NORI_MAPPING_EXAMPLE은 이 컨테이너에서 쓸 수 없음)")
    log(f"chunks={CHUNKS_PATH}")
    cleanup(client)

    policy = sb.load_alias_policy(CONFIG_DIR)
    noun_checker = sb.PlainNounChecker()  # 일반 명사 판정용 Kiwi는 한 번만 띄워 여러 실행 기록에 같이 씀
    embedder = sb.make_embedder()
    signature = embedder.signature
    contract = sb.make_embedding_contract(embedder)
    dimension = int(contract["dimension"])
    log(f"embedding signature={signature}")
    log(f"embedding contract={json.dumps(contract, ensure_ascii=False)}")
    log("")

    base_chunks = load_sample_chunks()
    run1 = make_run(base_chunks, signature, contract, policy, noun_checker)
    dictionary1 = sb.KeywordDictionary.from_meta(run1.keyword_dictionary)
    tokenizer = dictionary1.make_tokenizer()  # 색인 쪽(증분 색인 시험에서 씀)
    log(f"카드명 사전 {len(dictionary1.card_words)}개, 별칭 {len(dictionary1.aliases)}개, "
        f"자동 제외 {list(dictionary1.rejected)}")
    log(f"tokenizer signature={tokenizer.signature}")
    log(f"시험 입력: 청크 {len(base_chunks)}개, 문서 {len(run1.inputs_sha256)}개")

    def build(generation: str, chunks: list[dict[str, Any]], run: sb.RunContract,
              full_reindex: bool = False) -> dict[str, Any]:
        return sb.build_generation(
            client, alias=ALIAS, generation=generation, chunks=chunks,
            embed=embedder.embed, run=run, dimension=dimension, full_reindex=full_reindex,
        )

    # ------------------------------------------------------------------
    log("")
    log("=== a. 1세대 전체 색인 ===")
    gen1 = build(GEN1, base_chunks, run1)
    index1 = gen1["index"]
    log(f"  index={index1} embedded={len(gen1['embed'].embedded_ids)} "
        f"reused={len(gen1['embed'].reused_ids)} count={gen1['count']}")
    log(f"  판단: {reason_summary(gen1['embed'])}")
    switch1 = sb.step4_switch_alias(client, ALIAS, index1)
    log(f"  alias switch: {json.dumps(switch1, ensure_ascii=False)}")
    check("a-1 활성 세대가 없어 모두 1번 아니요로 새로 임베딩",
          set(gen1["embed"].reasons.values()) == {sb.NEW_NOT_REUSABLE_RUN}
          and len(gen1["embed"].embedded_ids) == len(base_chunks),
          f"{len(gen1['embed'].embedded_ids)}/{len(base_chunks)}")
    check("a-2 별칭이 1세대를 가리킴", sb.resolve_alias(client, ALIAS) == [index1],
          str(sb.resolve_alias(client, ALIAS)))
    alias_count = int(client.count(index=ALIAS)["count"])
    check("a-3 별칭으로 센 건수가 입력과 같음", alias_count == len(base_chunks),
          f"alias={alias_count} input={len(base_chunks)}")
    same_hash = sum(sb.text_hash_of(c) == c.get("text_hash") for c in base_chunks)
    check("a-4 예제의 text_hash가 1-a 인덱서가 만든 text_hash와 같음", same_hash == len(base_chunks),
          f"{same_hash}/{len(base_chunks)}")
    snapshot1 = sb.load_active_snapshot(client, ALIAS)
    check("a-5 1세대 _meta에 이번 실행 기록이 남음",
          snapshot1 is not None and dict(snapshot1.manifest) == run1.to_meta())

    # ------------------------------------------------------------------
    log("")
    log("=== p. 사전 검사(입력과 설정이 모두 같음) ===")
    skipped = build(GEN_SKIP, base_chunks, run1)
    log(f"  결과: {skipped}")
    check("p-1 사전 검사가 실행 전체를 생략함", skipped.get("skipped") is True and skipped["index"] == index1)
    skip_index = sb.generation_index_name(ALIAS, GEN_SKIP)
    check("p-2 새 세대 인덱스를 만들지 않음", not client.indices.exists(index=skip_index), skip_index)
    check("p-3 full_reindex면 사전 검사가 생략하지 않음",
          sb.precheck_skip_run(snapshot1, run1, full_reindex=True) is False)

    # ------------------------------------------------------------------
    log("")
    log("=== b. 2세대(문서 하나 수정 + 청크 하나 삭제) ===")
    changed_doc = "D1_27223010abe31291"
    old_doc_chunks = [c for c in base_chunks if sb.document_id_of(c) == changed_doc]
    edited = copy_chunk(old_doc_chunks[0])
    edited["text"] = edited["text"] + "\n※ 2026-10-19 개정: 해외 이용 환율 적용 기준을 바꿨습니다."
    edited["index_text"] = ""
    edited["text_hash"] = sb.text_hash_of(edited)
    stale_chunk_id = str(old_doc_chunks[0]["chunk_id"])
    edited["chunk_id"] = rebuild_chunk_id(edited)
    edited["metadata"] = {**edited["metadata"], "chunk_id": edited["chunk_id"]}
    removed_chunk_id = str(old_doc_chunks[-1]["chunk_id"])
    new_doc_chunks = [edited] + old_doc_chunks[1:-1]
    gen2_chunks = new_doc_chunks + [c for c in base_chunks if sb.document_id_of(c) != changed_doc]
    run2 = make_run(gen2_chunks, signature, contract, policy, noun_checker)
    log(f"  수정: {stale_chunk_id} -> {edited['chunk_id']}")
    log(f"  삭제: {removed_chunk_id}")
    check("b-0 원천 지문이 달라 사전 검사가 생략하지 않음",
          sb.precheck_skip_run(snapshot1, run2, full_reindex=False) is False)

    gen2 = build(GEN2, gen2_chunks, run2)
    index2 = gen2["index"]
    log(f"  index={index2} embedded={len(gen2['embed'].embedded_ids)} "
        f"reused={len(gen2['embed'].reused_ids)} count={gen2['count']}")
    log(f"  판단: {reason_summary(gen2['embed'])}")
    check("b-1 고친 청크 1건만 2번 아니요로 새로 임베딩",
          list(gen2["embed"].embedded_ids) == [edited["chunk_id"]]
          and gen2["embed"].reasons[edited["chunk_id"]] == sb.NEW_NO_SAME_TEXT,
          str(list(gen2["embed"].embedded_ids)))
    check("b-2 나머지는 같은 ID로 재사용",
          len(gen2["embed"].reused_ids) == len(gen2_chunks) - 1
          and all(gen2["embed"].reasons[i] == sb.REUSE_SAME_ID for i in gen2["embed"].reused_ids),
          f"reused={len(gen2['embed'].reused_ids)}")
    doc_ids_now = chunk_ids_in(client, index2, changed_doc)
    check("b-3 2세대 건수가 입력과 같음", gen2["count"] == len(gen2_chunks),
          f"actual={gen2['count']} expected={len(gen2_chunks)}")
    check("b-4 고친 청크의 옛 ID와 뺀 청크가 2세대에 없음",
          stale_chunk_id not in doc_ids_now and removed_chunk_id not in doc_ids_now)
    reuse_probe = [c for c in base_chunks if c["metadata"].get("doc_key") == "D2"][0]["chunk_id"]
    v1 = fetch_vector(client, index1, reuse_probe)
    v2 = fetch_vector(client, index2, reuse_probe)
    check("b-5 바뀌지 않은 문서의 벡터가 1세대와 완전히 같음(재사용)",
          v1 is not None and v1 == v2, f"chunk={reuse_probe}")

    # ------------------------------------------------------------------
    log("")
    log("=== c. 별칭 전환 뒤 검색 ===")
    switch2 = sb.step4_switch_alias(client, ALIAS, index2)
    log(f"  alias switch: {json.dumps(switch2, ensure_ascii=False)}")
    check("c-1 별칭이 2세대를 가리킴", sb.resolve_alias(client, ALIAS) == [index2],
          str(sb.resolve_alias(client, ALIAS)))
    check("c-2 1세대 인덱스는 지워지지 않고 남아 있음", bool(client.indices.exists(index=index1)), index1)
    query_tokenizer = sb.load_query_tokenizer(client, ALIAS)  # 검색 쪽은 활성 세대 _meta의 사전으로 만듦
    question = "해외에서 카드를 쓰면 환율은 어떻게 적용되나요?"
    bm25_hits = sb.search_bm25(client, ALIAS, question, query_tokenizer, size=3)
    knn_hits = sb.search_knn(client, ALIAS, question, embedder.embed, size=3)
    hybrid_hits = sb.search_hybrid(client, ALIAS, question, query_tokenizer, embedder.embed, size=3)
    log(f"  질문: {question}")
    for name, hits in (("BM25", bm25_hits), ("kNN", knn_hits), ("hybrid", hybrid_hits)):
        log(f"  {name}: " + ", ".join(f"{h['_source']['chunk_id']}({h['_score']:.4f})" for h in hits))
    check("c-3 BM25, kNN, 하이브리드 질의가 모두 결과를 돌려줌",
          len(bm25_hits) > 0 and len(knn_hits) > 0 and len(hybrid_hits) > 0,
          f"{len(bm25_hits)}/{len(knn_hits)}/{len(hybrid_hits)}건")
    member = next(c["metadata"]["member_pseudo_id"] for c in base_chunks if c["metadata"].get("member_pseudo_id"))
    member_hits = sb.search_hybrid(client, ALIAS, "상담에서 무엇을 물어봤나요?", query_tokenizer, embedder.embed,
                                   member_id=member, size=5)
    check("c-4 회원 필터가 그 회원 청크만 돌려줌",
          len(member_hits) > 0 and all(h["_source"].get("member_pseudo_id") == member for h in member_hits),
          f"{len(member_hits)}건")

    # ------------------------------------------------------------------
    log("")
    log("=== q. 키워드 분석: 카드명 사전과 별칭, k1 1.5 ===")
    dictionary2 = sb.KeywordDictionary.from_meta(run2.keyword_dictionary)
    aliases2 = dict(dictionary2.aliases)
    log(f"  카드명 사전 {[w for w, _t, _s in dictionary2.card_words]}")
    log(f"  가족돌봄 별칭: {[(k, v) for k, v in aliases2.items() if '가족돌봄' in k]}")
    log(f"  자동 제외: {list(dictionary2.rejected)}")
    check("q-1 카드명 사전에 한빛 가족돌봄, 별칭에 가족돌봄 → 한빛가족돌봄이 있음",
          any(w == "한빛 가족돌봄" for w, _t, _s in dictionary2.card_words)
          and aliases2.get("가족돌봄") == "한빛가족돌봄")
    check("q-2 일반 명사와 같은 별칭(장보기)은 자동으로 빠짐",
          ("장보기", "common_noun") in dictionary2.rejected and "장보기" not in aliases2)
    family_q = "가족돌봄 카드 할인 조건이 뭐예요?"
    q_tokens = query_tokenizer.tokenize(family_q)
    log(f"  질문 낱말: {q_tokens}")
    check("q-3 검색 쪽 토크나이저를 _meta로 다시 만들어 서명이 색인과 같음",
          query_tokenizer.signature == run2.lexical_signature, query_tokenizer.signature)
    check("q-4 줄여 부른 질문이 정식 카드명 낱말로 바뀜", "한빛가족돌봄" in q_tokens, str(q_tokens))
    family_hits = sb.search_bm25(client, ALIAS, family_q, query_tokenizer, size=3)
    top_card = None
    if family_hits:
        top_card = (fetch_source(client, ALIAS, family_hits[0]["_source"]["chunk_id"]) or {}).get("card_name")
    log("  BM25: " + ", ".join(f"{h['_source']['chunk_id']}({h['_score']:.4f})" for h in family_hits))
    check("q-5 BM25 1등이 한빛 가족돌봄 카드 청크", top_card == "한빛 가족돌봄", str(top_card))

    settings = client.indices.get_settings(index=index2)[index2]["settings"]["index"]
    similarity = settings.get("similarity", {}).get(sb.BM25_SIMILARITY, {})
    field = client.indices.get_mapping(index=index2)[index2]["mappings"]["properties"]["text_tokens"]
    log(f"  similarity 설정: {similarity}, text_tokens similarity={field.get('similarity')}")
    check("q-6 인덱스에 k1 1.5, b 0.75 BM25를 정의하고 text_tokens에 걺",
          float(similarity.get("k1", 0)) == 1.5 and float(similarity.get("b", 0)) == 0.75
          and field.get("similarity") == sb.BM25_SIMILARITY)
    explained = client.search(index=ALIAS, body={
        "size": 1, "explain": True,
        "query": {"match": {"text_tokens": {"query": " ".join(q_tokens), "analyzer": "whitespace"}}},
    })["hits"]["hits"][0]["_explanation"]

    def find_k1(node: dict[str, Any]) -> float | None:
        if str(node.get("description", "")).startswith("k1"):
            return float(node["value"])
        for child in node.get("details", []):
            found = find_k1(child)
            if found is not None:
                return found
        return None

    k1_used = find_k1(explained)
    check("q-7 실제 점수 계산(explain)에 k1 1.5가 쓰임", k1_used == 1.5, f"k1={k1_used}")

    excluded = dataclasses.replace(policy, overrides=sb.AliasOverrides(exclude=frozenset({"가족돌봄"})))
    run_x = make_run(gen2_chunks, signature, contract, excluded, noun_checker)
    active_q = sb.load_active_snapshot(client, ALIAS)
    check("q-8 별칭이 바뀌면 토크나이저 서명이 바뀌어 사전 검사가 생략하지 않음",
          run_x.lexical_signature != run2.lexical_signature
          and sb.precheck_skip_run(active_q, run_x, full_reindex=False) is False)
    check("q-9 그래도 임베딩 설정은 같아 벡터는 재사용 가능(1번 예)",
          sb.check1_reusable_run(active_q, run_x, full_reindex=False) is True)

    # ------------------------------------------------------------------
    log("")
    log("=== f. 증분 색인: 활성 2세대에 고친 문서를 원래 10건으로 되돌려 씀(문서 단위로 지우고 넣기) ===")
    active2 = sb.load_active_snapshot(client, ALIAS)
    vectors_f, report_f = sb.step1_embed_changed_chunks(
        old_doc_chunks, client=client, active=active2, run=run2, embed=embedder.embed)
    log(f"  판단: {reason_summary(report_f)}")
    write_f = write_doc(client, index2, old_doc_chunks, vectors_f, tokenizer)
    log(f"  deleted={write_f.deleted} indexed={write_f.indexed}")
    check("f-1 2세대에 없던 본문 2건만 새로 임베딩, 8건 재사용",
          len(report_f.embedded_ids) == 2 and len(report_f.reused_ids) == 8, reason_summary(report_f))
    check("f-2 그 문서의 옛 청크 9건을 통째로 지우고 10건을 넣음",
          write_f.deleted == len(new_doc_chunks) and write_f.indexed == len(old_doc_chunks),
          f"deleted={write_f.deleted} indexed={write_f.indexed}")
    check("f-3 고아 청크 없음(고쳤던 청크 ID가 사라짐)",
          edited["chunk_id"] not in chunk_ids_in(client, index2, changed_doc)
          and len(chunk_ids_in(client, index2, changed_doc)) == len(old_doc_chunks))

    # ------------------------------------------------------------------
    log("")
    log("=== g. 2번: ID만 바뀌고 본문은 같음 ===")
    renamed = copy_chunk([c for c in base_chunks if c["chunk_id"] == reuse_probe][0])
    renamed["chunk_id"] = str(renamed["chunk_id"]).rsplit("_", 1)[0] + "_0099"
    vectors_g, report_g = sb.step1_embed_changed_chunks(
        [renamed], client=client, active=sb.load_active_snapshot(client, ALIAS), run=run2, embed=embedder.embed)
    log(f"  {reuse_probe} -> {renamed['chunk_id']} 판단: {reason_summary(report_g)}")
    check("g-1 ID가 달라도 같은 정제 본문이라 재사용",
          report_g.reasons[renamed["chunk_id"]] == sb.REUSE_SAME_TEXT and not report_g.embedded_ids)
    check("g-2 가져온 벡터가 원래 청크 벡터와 같음", vectors_g[renamed["chunk_id"]] == v2)

    # ------------------------------------------------------------------
    log("")
    log("=== h. 메타데이터만 바뀜 ===")
    probe_doc = sb.document_id_of({"chunk_id": reuse_probe})
    doc_chunks_h = [copy_chunk(c) for c in base_chunks if sb.document_id_of(c) == probe_doc]
    target = next(c for c in doc_chunks_h if c["chunk_id"] == reuse_probe)
    old_access = target["metadata"].get("access_level")
    target["metadata"]["access_level"] = "restricted-test"
    vectors_h, report_h = sb.step1_embed_changed_chunks(
        doc_chunks_h, client=client, active=sb.load_active_snapshot(client, ALIAS), run=run2, embed=embedder.embed)
    write_h = write_doc(client, index2, doc_chunks_h, vectors_h, tokenizer)
    stored = fetch_source(client, index2, reuse_probe) or {}
    log(f"  문서 {probe_doc}: 청크 {len(doc_chunks_h)}개, access_level {old_access} -> restricted-test, "
        f"판단: {reason_summary(report_h)}")
    check("h-1 메타데이터만 바뀌면 벡터 재사용", not report_h.embedded_ids
          and report_h.reasons[reuse_probe] == sb.REUSE_SAME_ID)
    check("h-2 재사용한 청크도 최신 메타데이터로 다시 적재",
          stored.get("access_level") == "restricted-test" and stored.get("embedding") == v2,
          f"access_level={stored.get('access_level')} deleted={write_h.deleted} indexed={write_h.indexed}")

    # ------------------------------------------------------------------
    subset = [c for c in base_chunks if c["metadata"].get("doc_key") == "D2"]
    log("")
    log("=== i. 1번: 서명은 그대로, 임베딩 설정(max_seq_length)만 바뀜 ===")
    changed_contract = {**contract, "max_seq_length": int(contract["max_seq_length"]) // 2}
    run_i = make_run(gen2_chunks, signature, changed_contract, policy, noun_checker)
    log(f"  서명 같음: {run_i.embedding_signature == signature}, "
        f"max_seq_length {contract['max_seq_length']} -> {changed_contract['max_seq_length']}")
    active_i = sb.load_active_snapshot(client, ALIAS)
    check("i-1 1번 판단이 재사용 불가로 봄",
          sb.check1_reusable_run(active_i, run_i, full_reindex=False) is False)
    _, report_i = sb.step1_embed_changed_chunks(
        subset, client=client, active=active_i, run=run_i, embed=embedder.embed)
    check("i-2 대상 전부 새로 임베딩", len(report_i.embedded_ids) == len(subset)
          and set(report_i.reasons.values()) == {sb.NEW_NOT_REUSABLE_RUN}, reason_summary(report_i))

    log("")
    log("=== j. 1번: full_reindex ===")
    _, report_j = sb.step1_embed_changed_chunks(
        subset, client=client, active=active_i, run=run2, embed=embedder.embed, full_reindex=True)
    check("j-1 설정이 같아도 full_reindex면 전부 새로 임베딩", len(report_j.embedded_ids) == len(subset)
          and set(report_j.reasons.values()) == {sb.NEW_NOT_REUSABLE_RUN}, reason_summary(report_j))

    # ------------------------------------------------------------------
    log("")
    log("=== k. 3번: 지문을 읽은 뒤 그 청크가 지워져 벡터가 없음 ===")
    stale_snapshot = sb.load_active_snapshot(client, ALIAS)
    victim = next(c for c in base_chunks if c["metadata"].get("doc_key") == "D3")
    client.delete(index=index2, id=victim["chunk_id"], refresh=True)
    log(f"  지문 읽은 뒤 삭제: {victim['chunk_id']}")
    _, report_k = sb.step1_embed_changed_chunks(
        [victim], client=client, active=stale_snapshot, run=run2, embed=embedder.embed)
    check("k-1 2번은 예였지만 3번 조회에 없어 새로 임베딩",
          report_k.reasons[victim["chunk_id"]] == sb.NEW_VECTOR_MISSING
          and list(report_k.embedded_ids) == [victim["chunk_id"]], reason_summary(report_k))

    # ------------------------------------------------------------------
    log("")
    log("=== d. 1세대로 되돌리기 ===")
    rollback = sb.step4_switch_alias(client, ALIAS, index1)
    log(f"  alias switch: {json.dumps(rollback, ensure_ascii=False)}")
    check("d-1 별칭이 다시 1세대를 가리킴", sb.resolve_alias(client, ALIAS) == [index1],
          str(sb.resolve_alias(client, ALIAS)))
    rolled_count = int(client.count(index=ALIAS)["count"])
    check("d-2 되돌린 뒤 건수가 1세대 건수와 같음", rolled_count == len(base_chunks),
          f"alias={rolled_count} gen1={len(base_chunks)}")
    back_hits = sb.search_bm25(client, ALIAS, question, sb.load_query_tokenizer(client, ALIAS), size=3)
    check("d-3 되돌린 별칭으로도 검색이 됨", len(back_hits) > 0, f"{len(back_hits)}건")

    log("")
    log("=== 요약 ===")
    log(f"  실패 {len(_failures)}건" + ("" if not _failures else ": " + ", ".join(_failures)))
    return 1 if _failures else 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception:  # 실패도 그대로 로그에 남김
        import traceback

        log("")
        log("=== 예외로 중단 ===")
        log(traceback.format_exc())
        code = 2
    _log_file.close()
    sys.exit(code)
