"""카드명 별칭 생성·치환과 날짜 표기 통일이 색인·검색에서 같게 동작함을 검증함."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from app.domain.card_aliases import (
    AliasOverrides,
    AliasRules,
    build_alias_plan,
    generate_candidates,
)
from app.infrastructure.korean_tokenizer import (
    KoreanTokenizer,
    PlainNounChecker,
    lexical_policy_fingerprint,
    normalize_korean_text,
    unify_date_notation,
)
from app.infrastructure.lexical_index import AliasPolicy, LexicalIndexBuilder


RULES = AliasRules(brand_prefixes=("한빛",), suffixes=("카드",), min_length=3)
CARD_NAMES = ("한빛 모아생활", "한빛 모아생활 플러스", "한빛 대중교통", "한빛 가게모음", "한빛 가게모음 프리미엄")


def _never_common(_word: str) -> bool:
    """일반명사 충돌 판정을 끄고 규칙만 검증할 때 쓰는 가짜 판정기임."""
    return False


def test_candidates_cover_prefix_strip_and_suffix_forms():
    """정식명 하나에서 접두어 제거·접미어 결합 세 가지 호칭이 모두 만들어짐을 보증함."""
    candidates = generate_candidates(["한빛 모아생활"], RULES)
    assert {item.alias for item in candidates} == {
        "모아생활",
        "모아생활카드",
        "한빛모아생활카드",
    }
    assert {item.canonical for item in candidates} == {"한빛모아생활"}
    # 정식명이 한 단어면 띄어 쓴 형태가 없으므로 등록 표면형은 별칭 키와 같음
    assert {item.registered_surface() for item in candidates} == {item.alias for item in candidates}


def test_multiword_card_name_keeps_original_spacing_as_registered_surface():
    """여러 낱말 정식명은 접두어를 뗀 뒤에도 원래 띄어쓰기를 살린 표면형을 함께 가짐을 보증함."""
    candidates = generate_candidates(["한빛 가게모음 프리미엄"], RULES)
    by_alias = {item.alias: item for item in candidates}
    assert by_alias["가게모음프리미엄"].registered_surface() == "가게모음 프리미엄"
    # 접미어가 붙은 형태는 붙여 쓴 표면형만 둠. 접두어 제거 형태가 먼저 잡혀 결과가 같기 때문임
    assert by_alias["가게모음프리미엄카드"].registered_surface() == "가게모음프리미엄카드"
    assert by_alias["한빛가게모음프리미엄카드"].registered_surface() == "한빛가게모음프리미엄카드"


def test_short_and_ambiguous_and_common_noun_candidates_are_rejected_with_reason():
    """짧은 별칭·여러 카드를 가리키는 별칭·일반명사 별칭이 사유와 함께 제외됨을 보증함."""
    plan = build_alias_plan(
        ["한빛 가나다", "한빛 가나다카드", "한빛 가가", "한빛 대중교통"],
        rules=RULES,
        overrides=AliasOverrides(),
        is_common_noun=lambda word: word == "대중교통",
    )
    reasons = {item.alias: item.reason for item in plan.rejected}
    # "가나다카드"는 앞 카드의 애칭이면서 뒤 카드의 정식명이기도 하여 어느 쪽인지 고를 수 없음
    assert reasons["가나다카드"] == "ambiguous"
    assert reasons["한빛가나다카드"] == "ambiguous"
    assert reasons["가가"] == "too_short"
    assert reasons["대중교통"] == "common_noun"
    mapping = plan.mapping()
    assert {"가나다카드", "한빛가나다카드", "가가", "대중교통"}.isdisjoint(mapping)
    assert mapping["가나다"] == "한빛가나다"
    # "대중교통"만 일반명사이고 "대중교통카드"는 아니므로 접미어가 붙은 형태는 그대로 쓸 수 있음
    assert mapping["대중교통카드"] == "한빛대중교통"


def test_overrides_force_include_and_exclude():
    """사람이 승인한 별칭은 자동 제외를 뚫고 들어가고, 제외 목록은 자동 생성을 막음을 보증함."""
    plan = build_alias_plan(
        list(CARD_NAMES),
        rules=RULES,
        overrides=AliasOverrides(
            include=(("대중교통", "한빛 대중교통"),),
            exclude=frozenset({"모아생활"}),
        ),
        is_common_noun=lambda word: word == "대중교통",
    )
    mapping = plan.mapping()
    assert mapping["대중교통"] == "한빛대중교통"
    assert "모아생활" not in mapping
    assert {item.reason for item in plan.rejected if item.alias == "모아생활"} == {
        "excluded_by_override"
    }


def test_override_with_unknown_card_name_is_rejected():
    """승인 목록의 정식명이 카드명 목록에 없으면 색인을 멈춤을 보증함."""
    with pytest.raises(ValueError):
        build_alias_plan(
            list(CARD_NAMES),
            rules=RULES,
            overrides=AliasOverrides(include=(("없는별칭", "한빛 없는카드"),)),
            is_common_noun=_never_common,
        )


def test_plain_noun_checker_separates_dictionary_nouns_from_unknown_words():
    """사전에 실린 일반명사만 충돌로 보고, Kiwi가 통째로 묶은 미등록어는 통과시킴을 보증함."""
    pytest.importorskip("kiwipiepy")
    is_common_noun = PlainNounChecker()
    assert is_common_noun("대중교통") is True
    assert is_common_noun("장보기") is True
    assert is_common_noun("해오름마을") is False  # Kiwi가 모르는 말을 NNG 한 덩어리로 묶는 경우
    assert is_common_noun("모아생활") is False


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026년 2월", "2026-02"),
        ("2026년 2월 15일", "2026-02-15"),
        ("2026.2.15", "2026-02-15"),
        ("2026/3/1", "2026-03-01"),
        ("2026-2", "2026-02"),
        ("2026-02", "2026-02"),
        ("2026.02", "2026-02"),
        ("26년 2월", "26년 2월"),  # 두 자리 연도는 바꾸지 않음
        ("2026년 13월", "2026년 13월"),  # 달력에 없는 달은 그대로 둠
        ("d2-c001", "d2-c001"),  # 상품 코드는 건드리지 않음
        ("2026.5원", "2026.5원"),  # 뒤에 한글 단위가 붙은 소수는 날짜로 보지 않음
    ],
)
def test_date_notation_is_unified_to_iso_within_safe_bounds(text: str, expected: str):
    """여러 날짜 표기가 ISO 한 가지로 모이되 코드·소수는 그대로 남음을 보증함."""
    assert unify_date_notation(text) == expected
    assert normalize_korean_text(text) == expected


def _tokenizer(aliases: dict[str, str] | None = None) -> KoreanTokenizer:
    """실제 Kiwi로 카드명 사전과 별칭을 적용한 토크나이저를 만듦."""
    words = tuple((name, "NNP", 0.0) for name in CARD_NAMES)
    return KoreanTokenizer(None, additional_user_words=words, aliases=aliases, num_workers=1)


def test_alias_query_and_document_produce_the_same_card_token():
    """별칭으로 물어봐도 문서와 같은 카드 토큰이 나와 BM25가 맞물림을 보증함."""
    pytest.importorskip("kiwipiepy")
    plan = build_alias_plan(
        list(CARD_NAMES), rules=RULES, overrides=AliasOverrides(), is_common_noun=_never_common
    )
    tokenizer = _tokenizer(plan.surface_mapping())
    document = tokenizer.tokenize("한빛 모아생활 카드의 생활 포인트")
    assert document.count("한빛모아생활") == 1
    for question in ("모아생활 연회비", "모아생활카드 연회비", "한빛모아생활카드 연회비"):
        assert "한빛모아생활" in tokenizer.tokenize(question)

    # 별칭이 없으면 Kiwi가 "모아생활"을 동사로 쪼개 같은 토큰이 나오지 않음
    assert "한빛모아생활" not in _tokenizer().tokenize("모아생활 연회비")


def test_alias_substitution_does_not_duplicate_or_leak_into_longer_card_name():
    """별칭 치환이 같은 말을 두 번 세지 않고 더 긴 카드명을 짧은 카드로 바꾸지 않음을 보증함."""
    pytest.importorskip("kiwipiepy")
    plan = build_alias_plan(
        list(CARD_NAMES), rules=RULES, overrides=AliasOverrides(), is_common_noun=_never_common
    )
    tokenizer = _tokenizer(plan.surface_mapping())
    assert tokenizer.tokenize("한빛모아생활카드 연회비") == ["한빛모아생활", "연회비"]
    plus = tokenizer.tokenize("한빛 모아생활 플러스 전월 실적")
    assert "한빛모아생활플러스" in plus and "한빛모아생활" not in plus


def test_spaced_alias_matches_longer_card_name_before_the_shorter_one():
    """띄어 쓴 별칭으로 물어도 기본 카드가 아니라 긴 이름의 카드 토큰이 나옴을 보증함."""
    pytest.importorskip("kiwipiepy")
    plan = build_alias_plan(
        list(CARD_NAMES), rules=RULES, overrides=AliasOverrides(), is_common_noun=_never_common
    )
    tokenizer = _tokenizer(plan.surface_mapping())
    # 띄어 쓴 형태와 붙여 쓴 형태 모두 같은 긴 카드 토큰으로 모임
    for question in ("가게모음 프리미엄 혜택", "가게모음프리미엄 혜택", "가게모음 프리미엄 카드 혜택"):
        tokens = tokenizer.tokenize(question)
        assert "한빛가게모음프리미엄" in tokens, (question, tokens)
        assert "한빛가게모음" not in tokens, (question, tokens)
    # 기본 카드만 부른 질문은 그대로 기본 카드로 남음
    assert "한빛가게모음" in tokenizer.tokenize("가게모음 혜택")

    # 띄어 쓴 별칭이 없으면 기본 카드로 잘못 치환됨(이 시험이 막는 상황)
    compact_only = _tokenizer(plan.mapping())
    assert compact_only.tokenize("가게모음 프리미엄 혜택")[0] == "한빛가게모음"


def test_document_sentences_keep_their_own_card_token_after_spaced_aliases():
    """띄어 쓴 별칭을 넣어도 문서 쪽 정식명 문장이 각각 제 카드 토큰을 그대로 냄을 보증함."""
    pytest.importorskip("kiwipiepy")
    plan = build_alias_plan(
        list(CARD_NAMES), rules=RULES, overrides=AliasOverrides(), is_common_noun=_never_common
    )
    tokenizer = _tokenizer(plan.surface_mapping())
    premium = tokenizer.tokenize("한빛 가게모음 프리미엄 카드의 혜택")
    assert premium == ["한빛가게모음프리미엄", "카드", "혜택"], premium
    basic = tokenizer.tokenize("한빛 가게모음 카드의 혜택")
    assert basic == ["한빛가게모음", "카드", "혜택"], basic
    plus = tokenizer.tokenize("한빛 모아생활 플러스 전월 실적")
    assert "한빛모아생활플러스" in plus and "한빛모아생활" not in plus


def test_alias_surfaces_differing_only_in_spacing_are_rejected():
    """띄어쓰기만 다른 두 별칭은 Kiwi가 한 항목으로 보므로 함께 등록하지 못함을 보증함."""
    with pytest.raises(ValueError):
        KoreanTokenizer.normalize_aliases(
            {"가게모음 프리미엄": "한빛가게모음프리미엄", "가게모음프리미엄": "한빛가게모음프리미엄"}
        )


def test_date_question_and_document_share_one_token():
    """문서의 2026-02와 질문의 2026년 2월이 같은 토큰으로 모임을 보증함."""
    pytest.importorskip("kiwipiepy")
    tokenizer = _tokenizer()
    assert "2026-02" in tokenizer.tokenize("2026-02 승인 거래 건수")
    assert "2026-02" in tokenizer.tokenize("2026년 2월 승인 거래 건수는?")


def test_signature_changes_with_alias_map_and_keeps_card_dictionary_contract():
    """별칭이 서명에 반영되고 카드명 사전 해시 계약은 그대로임을 보증함."""
    pytest.importorskip("kiwipiepy")
    without = _tokenizer()
    with_alias = _tokenizer({"모아생활": "한빛모아생활"})
    assert without.signature != with_alias.signature
    assert without.additional_user_words_sha256 == with_alias.additional_user_words_sha256
    assert with_alias.alias_map_sha256 == hashlib.sha256(
        KoreanTokenizer.alias_payload({"모아생활": "한빛모아생활"})
    ).hexdigest()


def test_alias_payload_is_sorted_tab_separated_and_newline_terminated():
    """별칭 산출물이 정렬·중복 제거된 재현 가능한 TSV이며 띄어 쓴 표면형을 그대로 담음을 보증함."""
    payload = KoreanTokenizer.alias_payload(
        {"나카드": "한빛나", "가": "한빛가", " 다  라 ": "한빛다라"}
    )
    assert payload == "가\t한빛가\n나카드\t한빛나\n다 라\t한빛다라\n".encode("utf-8")


def test_lexical_fingerprint_follows_alias_configuration():
    """별칭 설정이 바뀌면 어휘 정책 지문이 달라짐을 보증함."""
    base = lexical_policy_fingerprint(alias_rules_sha256="a", alias_overrides_sha256="b")
    assert base != lexical_policy_fingerprint(alias_rules_sha256="a", alias_overrides_sha256="c")
    assert base == lexical_policy_fingerprint(alias_rules_sha256="a", alias_overrides_sha256="b")


def _alias_policy() -> AliasPolicy:
    """시험용 별칭 정책과 설정 지문을 만듦."""
    return AliasPolicy(rules=RULES, overrides=AliasOverrides(), rules_sha256="r1", overrides_sha256="o1")


def _benefit_chunk():
    """별칭 산출물 검증에 쓸 D2 혜택 청크를 만듦."""
    from app.domain.models import PreparedChunk

    metadata = {
        "source": "D2.pdf",
        "doc_key": "D2",
        "doc_type": "benefit_guide",
        "access_level": "public",
        "card_id": "D2-C001",
        "card_name": "한빛 모아생활",
    }
    text = "한빛 모아생활 카드의 생활 포인트 적립 안내"
    payload = json.dumps(metadata, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return PreparedChunk(
        chunk_id="D2-C001-0000",
        text=text,
        metadata=metadata,
        token_count=12,
        text_hash=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        metadata_hash=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
    )


def test_builder_publishes_alias_artifacts_and_verifies_their_hashes(tmp_path: Path):
    """별칭 TSV·검수 파일이 세대에 남고 포인터·manifest 해시로 검증됨을 보증함."""
    pytest.importorskip("kiwipiepy")
    pytest.importorskip("bm25s")
    builder = LexicalIndexBuilder(alias_policy=_alias_policy())
    search_root = tmp_path / "search_indexes"
    pointer, manifest = builder.build(
        search_root=search_root,
        generation="gen-alias",
        chunks=[_benefit_chunk()],
        collection="card_docs",
        embedding_signature="sentence-transformers:test:prompt-policy-v2",
        manifest={},
    )

    alias_path = search_root / str(pointer["card_aliases"])
    rows = dict(
        line.split("\t")
        for line in alias_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    assert rows["모아생활"] == "한빛모아생활"
    assert pointer["card_aliases_count"] == len(rows) == manifest["card_aliases"]["count"]
    assert manifest["card_aliases"]["rules_sha256"] == "r1"
    assert manifest["card_aliases"]["overrides_sha256"] == "o1"
    # 카드명 사전의 기존 계약 6키는 그대로여야 기존 Retriever가 계속 읽을 수 있음
    assert set(manifest["card_dictionary"]) == {
        "path", "sha256", "count", "source", "tag", "score"
    }

    review = json.loads(
        (alias_path.parent / "card_aliases_review.json").read_text(encoding="utf-8")
    )
    assert review["policy"] == "rule-generated-human-review-v1"
    assert {item["alias"] for item in review["accepted"]} == set(rows)

    builder.verify(search_root=search_root, generation="gen-alias")
    alias_path.write_bytes(b"\xeb\x82\x98\t\xed\x95\x9c\xeb\xb9\x9b\n")
    with pytest.raises(ValueError):
        builder.verify(search_root=search_root, generation="gen-alias")


def test_retriever_keyword_selection_rules_pass_in_its_own_environment():
    """검색기 핵심어 선별 규칙 검증 스크립트가 검색기 가상환경에서 통과함을 보증함.

    검색기 가상환경에는 pytest가 없어 순수 함수 시험을 실행 스크립트로 두고 여기서 하위 프로세스로 실행함.
    """

    retriever_root = Path(__file__).resolve().parents[3] / "retriever" / "vector-retriever"
    retriever_python = retriever_root / ".venv" / "Scripts" / "python.exe"
    if not retriever_python.is_file():
        pytest.skip("기존 Retriever 가상환경이 없습니다.")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(retriever_root)
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [str(retriever_python), str(retriever_root / "tests" / "check_keyword_rules.py")],
        cwd=retriever_root,
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "keyword-rules-ok" in result.stdout


def test_indexer_and_retriever_tokenizers_agree_on_tokens_and_signature(tmp_path: Path):
    """색인과 검색이 같은 입력에 같은 토큰·같은 서명을 내는지 검색기 가상환경으로 대조함."""
    pytest.importorskip("kiwipiepy")
    retriever_root = Path(__file__).resolve().parents[3] / "retriever" / "vector-retriever"
    retriever_python = retriever_root / ".venv" / "Scripts" / "python.exe"
    if not retriever_python.is_file():
        pytest.skip("기존 Retriever 가상환경이 없습니다.")

    plan = build_alias_plan(
        list(CARD_NAMES), rules=RULES, overrides=AliasOverrides(), is_common_noun=_never_common
    )
    samples = [
        "한빛 모아생활 카드의 생활 포인트",
        "모아생활 연회비 안 내려면 어케 해?",
        "한빛모아생활카드 연회비",
        "2026년 2월 승인 거래 건수와 합계 금액은?",
        "2026-02 승인 거래 1,234,500원",
        "한빛 모아생활 플러스 전월 실적",
    ]
    payload = {
        "cards": [list(item) for item in ((name, "NNP", 0.0) for name in CARD_NAMES)],
        "aliases": plan.surface_mapping(),
        "samples": samples,
    }
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    script = (
        "import json, sys\n"
        "from app.infrastructure.korean_tokenizer import KoreanTokenizer\n"
        "value = json.loads(open(sys.argv[1], encoding='utf-8').read())\n"
        "words = [(form, tag, float(score)) for form, tag, score in value['cards']]\n"
        "tokenizer = KoreanTokenizer(None, additional_user_words=words,"
        " aliases=value['aliases'], num_workers=1)\n"
        "print(json.dumps({'signature': tokenizer.signature,"
        " 'alias_sha256': tokenizer.alias_map_sha256,"
        " 'tokens': [tokenizer.tokenize(text) for text in value['samples']],"
        " 'typo': [list(tokenizer.tokenize_with_typo_fallback(text).original)"
        " for text in value['samples']]}, ensure_ascii=False))\n"
    )
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(retriever_root)
    # Windows 콘솔 기본 인코딩으로는 한글 토큰을 주고받을 수 없어 하위 프로세스 입출력을 UTF-8로 고정함.
    environment["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [str(retriever_python), "-c", script, str(request_path)],
        cwd=retriever_root,
        env=environment,
        text=True,
        encoding="utf-8",
        capture_output=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    remote = json.loads(result.stdout.strip().splitlines()[-1])

    tokenizer = _tokenizer(plan.surface_mapping())
    assert remote["signature"] == tokenizer.signature
    assert remote["alias_sha256"] == tokenizer.alias_map_sha256
    assert remote["tokens"] == [tokenizer.tokenize(text) for text in samples]
    # 오타 교정 폴백의 기준 토큰도 색인과 같아야 질의 경로 두 가지가 모두 맞물림
    assert remote["typo"] == remote["tokens"]
