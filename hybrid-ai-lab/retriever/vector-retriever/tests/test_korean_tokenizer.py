"""질의 낱말이 색인 낱말과 같아지는지(표기 통일·별칭·핵심어 선별) 확인하는 시험임."""

from __future__ import annotations

from app.infrastructure.korean_tokenizer import (
    KoreanTokenizer,
    has_digit,
    is_code_like,
    lexical_policy_fingerprint,
    normalize_korean_text,
    unify_date_notation,
)

# 작은 사전: 실제 세대 사전(카드명 64 · 별칭 189)의 동작을 한 쌍으로 줄여 재현함.
CARD_WORDS = (("한빛 모아생활", "NNP", 0.0),)
ALIASES = {"모아생활": "한빛모아생활"}


def _tokenizer() -> KoreanTokenizer:
    """작은 카드명·별칭 사전을 올린 분석기를 만듦."""

    return KoreanTokenizer(None, additional_user_words=CARD_WORDS, aliases=ALIASES)


# ---------------------------------------------------------------- 표기 통일


def test_숫자_쉼표와_대소문자를_통일함():
    assert normalize_korean_text("1,313,000원") == "1313000원"
    assert normalize_korean_text("D2-C018-B01") == "d2-c018-b01"


def test_여러_날짜_표기를_iso로_통일함():
    assert normalize_korean_text("2026년 2월 15일") == "2026-02-15"
    assert normalize_korean_text("2026.2.15") == "2026-02-15"
    assert normalize_korean_text("2026/2/15") == "2026-02-15"
    assert normalize_korean_text("2026년 2월") == "2026-02"


def test_날짜가_아닌_숫자는_건드리지_않음():
    # "2026.5원"은 소수 금액일 수 있어 연·월로 바꾸지 않음(색인 계약 5-1).
    assert unify_date_notation("2026.5원") == "2026.5원"
    # 월이 범위를 벗어나면 그대로 둠.
    assert unify_date_notation("2026-13-40") == "2026-13-40"
    # 두 자리 연도 표기는 대상이 아님.
    assert unify_date_notation("26.2.15") == "26.2.15"


# ---------------------------------------------------------------- 정책 지문


def test_어휘_정책_지문은_같은_입력에_같은_값을_줌():
    first = lexical_policy_fingerprint(alias_rules_sha256="a", alias_overrides_sha256="b")
    second = lexical_policy_fingerprint(alias_rules_sha256="a", alias_overrides_sha256="b")
    other = lexical_policy_fingerprint(alias_rules_sha256="a", alias_overrides_sha256="c")
    assert first == second
    assert first != other
    assert len(first) == 64


def test_조건_낱말_판정_보조함수():
    assert has_digit("3000000원") is True
    assert has_digit("할부") is False
    assert is_code_like("d2-c018-b01") is True
    assert is_code_like("2026-02-15") is False  # 영문자가 없어 코드로 보지 않음


# ---------------------------------------------------------------- 분석기


def test_별칭을_정식_카드_토큰으로_바꿈():
    tokens = _tokenizer().tokenize("모아생활 혜택이 뭐예요")
    assert "한빛모아생활" in tokens
    assert "모아생활" not in tokens


def test_날짜와_금액이_색인과_같은_낱말로_나옴():
    # 조사를 붙이면 '2026-02-15에'가 한 낱말로 보존되므로, 날짜 뒤를 띄운 문장으로 확인함
    # (색인도 같은 규칙이므로 문서 쪽 '2026-02' 표기와 맞물림).
    tokens = _tokenizer().tokenize("2026년 2월 15일 3,000,000원 할부 결제")
    assert "2026-02-15" in tokens
    assert "3000000" in tokens
    assert "3000000원" in tokens


def test_핵심어는_명사_숫자_코드만_남김():
    terms = _tokenizer().keyword_terms("모아생활 카드로 3,000,000원을 할부로 결제했어요")
    assert "한빛모아생활" in terms
    assert "할부" in terms
    assert "3000000" in terms
    # 동사 '결제하다'의 활용형이나 조사는 핵심어가 아님.
    assert "하" not in terms
    assert "었" not in terms
    # 중복이 없어야 함.
    assert len(terms) == len(set(terms))


def test_핵심어에_코드가_통째로_남음():
    terms = _tokenizer().keyword_terms("D2-C018-B01 혜택 조건을 알려 주세요")
    assert "d2-c018-b01" in terms


def test_빈_문장은_빈_목록을_줌():
    tokenizer = _tokenizer()
    assert tokenizer.keyword_terms("   ") == []
    assert tokenizer.tokenize("") == []


def test_카드명_사전의_정식_토큰을_공개함():
    assert _tokenizer().card_tokens == frozenset({"한빛모아생활"})
