"""Indexer와 Retriever가 공유하는 한국어 BM25 토큰화 정책임."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence
import unicodedata


_POLICY_VERSION = 4
_NORMALIZATION_POLICY = "nfkc-lower-remove-numeric-comma-iso-date-v2"
_SURFACE_POLICY = "number-unit-code-dictionary-clean-compound-alias-v3"
# 버전 2는 띄어 쓴 별칭 표면형을 등록해 "가게모음 프리미엄"이 기본 카드로 치환되지 않게 한 정책임.
_ALIAS_POLICY = "card-name-spaced-surface-v2"
_CONTENT_TAGS = frozenset(
    {
        "NNG", "NNP", "NNB", "NP", "NR", "VV", "VA", "VX", "VCP", "VCN",
        "MM", "MAG", "MAJ", "IC", "SL", "SH", "SN", "XR",
    }
)
_SURFACE_TOKEN = re.compile(r"[0-9a-z가-힣]+(?:[-_/][0-9a-z가-힣]+)*%?")
_NUMBER_COMMA = re.compile(r"(?<=\d),(?=\d)")
_ASCII_LETTER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")
_CODE_SEPARATOR = re.compile(r"[-_/]")

# 날짜 표기 통일: 문서의 "2026-02"와 질문의 "2026년 2월"이 같은 토큰이 되도록 ISO 모양으로 맞춤.
# 네 자리 연도 19xx·20xx만 대상으로 삼아 상품코드(d2-c001)나 두 자리 연도 표기를 건드리지 않음.
_YEAR = r"(?:19|20)\d{2}"
_KOREAN_FULL_DATE = re.compile(rf"(?<!\d)({_YEAR})\s*년\s*(\d{{1,2}})\s*월\s*(\d{{1,2}})\s*일")
_KOREAN_YEAR_MONTH = re.compile(rf"(?<!\d)({_YEAR})\s*년\s*(\d{{1,2}})\s*월")
_SEPARATED_FULL_DATE = re.compile(
    rf"(?<![\d./-])({_YEAR})([./-])(\d{{1,2}})\2(\d{{1,2}})(?![\d./-])"
)
# 연·월만 있는 구분자 표기는 "2026.5원" 같은 소수 금액과 구분할 단서가 없어 뒤에 한글이 붙으면 건드리지 않음.
_SEPARATED_YEAR_MONTH = re.compile(rf"(?<![\d./-])({_YEAR})[./-](\d{{1,2}})(?![\d./\-가-힣])")

# 별칭은 Kiwi가 "모아생활"을 동사로 쪼개지 않도록 고유명사로 등록함. 점수는 카드명 사전과 같게 둠.
_ALIAS_TAG = "NNP"
_ALIAS_SCORE = 0.0

POLICY_DESCRIPTOR: dict[str, object] = {
    "name": "kiwi-content-and-surface",
    "policy_version": _POLICY_VERSION,
    "normalization": _NORMALIZATION_POLICY,
    "content_tags": sorted(_CONTENT_TAGS),
    "tag_normalization": "strip-kiwi-regularity-suffix-v1",
    "surface_policy": _SURFACE_POLICY,
    "alias_policy": _ALIAS_POLICY,
    "stopword_policy": "content-pos-filter-v1",
}


@dataclass(frozen=True)
class OOVCandidate:
    """Kiwi가 제안한 미등록어와 자동 등록하지 않는 검토용 점수를 담음."""

    form: str  # 후보 단어의 표면형
    score: float  # Kiwi가 계산한 단어 후보 점수
    frequency: int  # 전체 입력 문서에서 발견된 횟수
    pos_score: float  # 후보의 품사 적합도 점수


def _iso_full_date(year: str, month: str, day: str, original: str) -> str:
    """월·일이 달력 범위 안이면 ISO 날짜로 바꾸고 아니면 원문을 그대로 둠."""

    month_value, day_value = int(month), int(day)
    if not (1 <= month_value <= 12 and 1 <= day_value <= 31):
        return original
    return f"{int(year):04d}-{month_value:02d}-{day_value:02d}"


def _iso_year_month(year: str, month: str, original: str) -> str:
    """월이 1~12이면 ISO 연월로 바꾸고 아니면 원문을 그대로 둠."""

    month_value = int(month)
    if not 1 <= month_value <= 12:
        return original
    return f"{int(year):04d}-{month_value:02d}"


def unify_date_notation(text: str) -> str:
    """여러 날짜 표기를 ISO 모양(YYYY-MM-DD·YYYY-MM) 한 가지로 통일함.

    목적: 같은 시점을 가리키는 문서와 질문이 서로 다른 토큰으로 갈라지지 않게 함.
    방법: 연·월·일 표기를 먼저 바꾸고 연·월 표기를 뒤에 바꿔 더 긴 표기가 먼저 잡히게 함.
    반환값: 날짜 자리만 바뀐 문자열이며 이미 ISO 모양이면 그대로임. 청크 본문은 이 함수로 바꾸지 않음.
    부수효과: 없음.
    """

    value = _KOREAN_FULL_DATE.sub(
        lambda m: _iso_full_date(m.group(1), m.group(2), m.group(3), m.group(0)), str(text)
    )
    value = _SEPARATED_FULL_DATE.sub(
        lambda m: _iso_full_date(m.group(1), m.group(3), m.group(4), m.group(0)), value
    )
    value = _KOREAN_YEAR_MONTH.sub(
        lambda m: _iso_year_month(m.group(1), m.group(2), m.group(0)), value
    )
    return _SEPARATED_YEAR_MONTH.sub(
        lambda m: _iso_year_month(m.group(1), m.group(2), m.group(0)), value
    )


def normalize_korean_text(text: str) -> str:
    """NFKC·소문자 변환, 숫자 쉼표 제거, 날짜 표기 통일을 거친 검색용 문자열을 반환함."""

    value = _NUMBER_COMMA.sub("", unicodedata.normalize("NFKC", str(text)).lower())
    return unify_date_notation(value)


def lexical_policy_fingerprint(
    *,
    alias_rules_sha256: str,
    alias_overrides_sha256: str,
) -> str:
    """토큰화 정책과 별칭 설정의 변화를 Kiwi 없이 비교할 정적 지문을 만듦.

    목적: 원천이 그대로여도 어휘 정책이 바뀌면 BM25를 다시 만들도록 무변경 판정에 쓰기 위함.
    인자: 두 해시는 별칭 규칙·승인 설정 파일의 내용 지문임.
    반환값: SHA-256 16진 문자열임. Kiwi나 모델을 읽지 않으므로 발견 단계에서 바로 계산 가능함.
    부수효과: 없음.
    """

    value = {
        **POLICY_DESCRIPTOR,
        "alias_rules_sha256": str(alias_rules_sha256),
        "alias_overrides_sha256": str(alias_overrides_sha256),
    }
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _base_tag(tag: str) -> str:
    """Kiwi 규칙성 접미사를 제거한 기본 품사 태그를 반환함."""

    return str(tag).split("-", 1)[0]


class PlainNounChecker:
    """사용자 사전 없는 Kiwi로 별칭 후보가 일반명사 한 개인지 판정함.

    Kiwi 생성자를 주입받으며, 사전 등록이나 토큰 저장은 수행하지 않음.
    """

    def __init__(self, kiwi_factory=None, *, num_workers: int = 1) -> None:
        """사용자 단어를 하나도 넣지 않은 판정 전용 Kiwi 인스턴스를 만듦.

        예외: kiwipiepy가 없으면 RuntimeError를 발생시킴.
        부수효과: Kiwi 모델을 메모리에 올림.
        """

        if kiwi_factory is None:
            from kiwipiepy import Kiwi

            kiwi_factory = Kiwi
        self._kiwi = kiwi_factory(num_workers=num_workers)

    def __call__(self, word: str) -> bool:
        """별칭 후보가 사전 없이도 사전에 실린 일반명사 한 개로 분석되는지 반환함.

        반환값: 분석 결과가 미등록어가 아닌 일반명사(NNG) 토큰 하나뿐이면 True임.
        부수효과: 형태소 분석에 메모리의 Kiwi 인스턴스를 사용함.
        """

        analyzed = list(self._kiwi.tokenize(str(word), oov_handling="chr"))
        if len(analyzed) != 1:
            return False
        token = analyzed[0]
        # Kiwi는 모르는 말도 NNG 한 덩어리로 묶으므로, oov 표시를 함께 봐야 진짜 일반명사만 걸러 냄.
        if bool(getattr(token, "oov", False)):
            return False
        return _base_tag(str(getattr(token, "tag"))) == "NNG"


class KoreanTokenizer:
    """내용어와 카드명·코드 원형을 함께 보존하는 Kiwi 어댑터임.

    사용자 사전·동적 카드명·별칭 치환표·Kiwi 생성자를 주입받으며, BM25 점수 계산이나 파일 저장은 수행하지 않음.
    """

    def __init__(
        self,
        user_dictionary: Path | None = None,
        *,
        additional_user_words: Iterable[tuple[str, str, float]] = (),
        aliases: Mapping[str, str] | None = None,
        num_workers: int = 1,
        oov_handling: str = "chr",
        typo_policy: str = "basic",
        typo_cost_threshold: float = 2.5,
        kiwi_factory=None,
        library_version: str | None = None,
    ) -> None:
        """형태소 분석기와 검색어 보존 정책을 설정함.

        인자: typo_cost_threshold는 검색 측 오타 교정 계약에 기록할 비용 상한임.
        인자: aliases는 별칭 표면형에서 정식 카드 토큰으로 가는 치환표이며 양쪽 모두 공백이 없어야 함.
        예외: kiwipiepy가 없거나 사용자 사전을 읽지 못하면 해당 예외를 발생시킴.
        부수효과: 사용자 사전을 읽고 Kiwi 인스턴스에 사용자 단어와 별칭 표면형을 등록함.
        """

        if kiwi_factory is None:
            try:
                import kiwipiepy
                from kiwipiepy import Kiwi
            except ImportError as error:
                raise RuntimeError("BM25 색인을 만들려면 kiwipiepy가 필요합니다.") from error
            kiwi_factory = Kiwi
            library_version = str(kiwipiepy.__version__)
        self._kiwi = kiwi_factory(num_workers=num_workers)
        self._version = str(library_version or "injected")
        self._dictionary_path = Path(user_dictionary).resolve() if user_dictionary else None
        self._dictionary_hash = ""
        self._num_workers = int(num_workers)
        self._oov_handling = str(oov_handling)
        self._typo_policy = str(typo_policy)
        self._typo_cost_threshold = float(typo_cost_threshold)
        surfaces: set[str] = set()
        if self._dictionary_path:
            payload = self._dictionary_path.read_bytes()
            self._dictionary_hash = hashlib.sha256(payload).hexdigest()
            self._kiwi.load_user_dictionary(str(self._dictionary_path))
            surfaces.update(self._dictionary_surfaces_from(payload))
        words = self.normalize_additional_words(additional_user_words)
        self._additional_user_word_count = len(words)
        extra_payload = self.additional_user_words_payload(words)
        self._additional_dictionary_hash = hashlib.sha256(extra_payload).hexdigest()
        for form, tag, score in words:
            self._kiwi.add_user_word(form, tag, score)
            surfaces.add(form.replace(" ", ""))
        self._alias_surfaces = self.normalize_aliases(aliases)
        self._alias_hash = hashlib.sha256(self.alias_payload(self._alias_surfaces)).hexdigest()
        self._aliases = {
            surface.replace(" ", ""): canonical
            for surface, canonical in self._alias_surfaces.items()
        }
        for surface, _canonical in self._alias_surfaces.items():
            # 별칭을 사전에 올려야 Kiwi가 "모아생활"을 모으+어+생활로 쪼개지 않고 한 덩어리로 봄.
            # 띄어 쓴 표면형을 등록하면 "가게모음 프리미엄"과 "가게모음프리미엄"이 모두 같은 단어로 잡힘.
            self._kiwi.add_user_word(surface, _ALIAS_TAG, _ALIAS_SCORE)
            surfaces.add(surface.replace(" ", ""))
        self._dictionary_surfaces = frozenset(surfaces)

    @staticmethod
    def normalize_additional_words(
        words: Iterable[tuple[str, str, float]],
    ) -> tuple[tuple[str, str, float], ...]:
        """동적 사용자 단어를 정규화·중복 제거하여 안정적인 순서로 반환함.

        예외: 표면형에 탭·줄바꿈이 있거나 표면형·품사가 비면 ValueError를 발생시킴.
        부수효과: 없음.
        """

        normalized: set[tuple[str, str, float]] = set()
        for raw_form, raw_tag, raw_score in words:
            if any(char in str(raw_form) for char in "\t\r\n"):
                raise ValueError("사용자 단어에는 탭이나 줄바꿈을 넣을 수 없습니다.")
            form = " ".join(normalize_korean_text(raw_form).split())
            tag = str(raw_tag).strip()
            if not form or not tag:
                raise ValueError("사용자 단어의 형태와 품사는 비어 있을 수 없습니다.")
            normalized.add((form, tag, float(raw_score)))
        return tuple(sorted(normalized))

    @classmethod
    def additional_user_words_payload(cls, words: Iterable[tuple[str, str, float]]) -> bytes:
        """동적 사용자 단어를 재현 가능한 UTF-8 사전 바이트로 직렬화함."""

        return "".join(
            f"{form}\t{tag}\t{score}\n"
            for form, tag, score in cls.normalize_additional_words(words)
        ).encode("utf-8")

    @staticmethod
    def normalize_aliases(aliases: Mapping[str, str] | None) -> dict[str, str]:
        """별칭 표면형 치환표를 표준형으로 바꾸고 표면형 순으로 정렬해 반환함.

        인자: 키는 형태소 분석기에 등록할 별칭 표면형(띄어쓰기 허용), 값은 정식 카드명 토큰임.
        반환값: 표면형 오름차순으로 삽입한 dict임. 비어 있으면 빈 dict임.
        예외: 탭·줄바꿈이 있거나 비어 있거나 공백을 뺀 별칭이 정식 토큰과 같으면 ValueError를 발생시킴.
        예외: 공백만 다른 두 표면형이 함께 있으면 Kiwi가 한 항목으로 보므로 ValueError를 발생시킴.
        부수효과: 없음.
        """

        normalized: dict[str, str] = {}
        keys: dict[str, str] = {}
        for raw_alias, raw_canonical in dict(aliases or {}).items():
            if any(char in f"{raw_alias}{raw_canonical}" for char in "\t\r\n"):
                raise ValueError("별칭에는 탭이나 줄바꿈을 넣을 수 없습니다.")
            surface = " ".join(normalize_korean_text(raw_alias).split())
            canonical = normalize_korean_text(raw_canonical).replace(" ", "")
            alias = surface.replace(" ", "")
            if not alias or not canonical:
                raise ValueError("별칭과 정식 카드 토큰은 비어 있을 수 없습니다.")
            if alias == canonical:
                raise ValueError(f"별칭과 정식 카드 토큰이 같습니다: {surface}")
            if keys.setdefault(alias, surface) != surface:
                # Kiwi는 사용자 단어를 공백과 무관하게 한 항목으로 보므로 띄어쓰기만 다른 중복을 금지함.
                raise ValueError(f"띄어쓰기만 다른 별칭이 함께 있습니다: {surface}")
            if normalized.get(surface, canonical) != canonical:
                raise ValueError(f"같은 별칭이 서로 다른 카드를 가리킵니다: {surface}")
            normalized[surface] = canonical
        return {surface: normalized[surface] for surface in sorted(normalized)}

    @classmethod
    def alias_payload(cls, aliases: Mapping[str, str] | None) -> bytes:
        """별칭 표면형 치환표를 재현 가능한 UTF-8 TSV 바이트로 직렬화함."""

        return "".join(
            f"{surface}\t{canonical}\n"
            for surface, canonical in cls.normalize_aliases(aliases).items()
        ).encode("utf-8")

    @staticmethod
    def _dictionary_surfaces_from(payload: bytes) -> frozenset[str]:
        """사용자 사전 바이트에서 검색 결과에 보존할 표면형 집합을 읽음."""

        values: set[str] = set()
        for raw in payload.decode("utf-8-sig").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            value = normalize_korean_text(line.split("\t", 1)[0]).replace(" ", "")
            if len(value) >= 2:
                values.add(value)
        return frozenset(values)

    @property
    def signature(self) -> str:
        """토큰화 정책·라이브러리·사전 내용을 식별하는 SHA-256 서명을 반환함."""

        value: dict[str, object] = {
            **POLICY_DESCRIPTOR,
            "kiwipiepy": self._version,
            "oov_handling": self._oov_handling,
            "typo_policy": self._typo_policy,
            "typo_cost_threshold": self._typo_cost_threshold,
            "user_dictionary_sha256": self._dictionary_hash,
        }
        if self._additional_user_word_count:
            value["additional_user_words_sha256"] = self._additional_dictionary_hash
        if self._aliases:
            value["alias_map_sha256"] = self._alias_hash
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return f"kiwi:{hashlib.sha256(encoded).hexdigest()}"

    @property
    def user_dictionary_sha256(self) -> str:
        """정적 사용자 사전의 SHA-256 해시를 반환하며, 사전이 없으면 빈 문자열임."""

        return self._dictionary_hash

    @property
    def additional_user_words_sha256(self) -> str:
        """정규화된 동적 사용자 단어 사전의 SHA-256 해시를 반환함."""

        return self._additional_dictionary_hash

    @property
    def alias_map_sha256(self) -> str:
        """정규화된 별칭 치환표 TSV의 SHA-256 해시를 반환함."""

        return self._alias_hash

    @staticmethod
    def _overlapping(tokens: Sequence[object], start: int, end: int) -> list[object]:
        """문자 범위와 한 글자 이상 겹치는 Kiwi 토큰을 반환함."""

        return [
            token for token in tokens
            if int(getattr(token, "start")) < end and int(getattr(token, "end")) > start
        ]

    def _substitute(self, token: str) -> str:
        """별칭이면 정식 카드 토큰으로 바꾸고 아니면 그대로 돌려줌."""

        return self._aliases.get(token, token)

    def _is_redundant_surface(
        self,
        value: str,
        overlapping: Sequence[object],
        start: int,
        end: int,
    ) -> bool:
        """별칭 치환을 마친 표면형이 같은 자리의 형태소 토큰과 겹쳐 중복인지 판정함.

        목적: 별칭을 사전에 올리면서 늘어난 보존 표면형이 같은 말을 두 번 세지 않게 함.
        방법: 겹치는 내용어 토큰 중 ① 치환 결과가 같거나 ② 이 표면형을 통째로 품는 더 긴 토큰이 있으면 중복으로 봄.
        부수효과: 없음.
        """

        for token in overlapping:
            if _base_tag(str(getattr(token, "tag"))) not in _CONTENT_TAGS:
                continue
            token_start, token_end = int(getattr(token, "start")), int(getattr(token, "end"))
            if token_start <= start and end <= token_end and (token_end - token_start) > (end - start):
                return True
            form = self._substitute(
                normalize_korean_text(getattr(token, "form")).replace(" ", "")
            )
            if form == value:
                return True
        return False

    def _preserve_surface(self, surface: str, analyzed: Sequence[object]) -> bool:
        """숫자·코드·사전어·내용어 복합어의 원형을 추가 토큰으로 보존할지 판정함."""

        compact = surface.replace(" ", "")
        if _DIGIT.search(compact) or compact in self._dictionary_surfaces:
            return True
        if _ASCII_LETTER.search(compact) and _CODE_SEPARATOR.search(compact):
            return True
        tags = [_base_tag(str(getattr(token, "tag"))) for token in analyzed]
        return len(tags) >= 2 and all(tag in _CONTENT_TAGS for tag in tags)

    def _from_analysis(self, normalized: str, analyzed: Sequence[object]) -> list[str]:
        """내용어 형태소에 필요한 원형 토큰을 보충하되 같은 출현 횟수는 중복하지 않음."""

        tokens = [
            self._substitute(normalize_korean_text(getattr(token, "form")).replace(" ", ""))
            for token in analyzed
            if _base_tag(str(getattr(token, "tag"))) in _CONTENT_TAGS
        ]
        tokens = [token for token in tokens if token]
        counts = Counter(tokens)
        surfaces: Counter[str] = Counter()
        for match in _SURFACE_TOKEN.finditer(normalized):
            surface = match.group(0)
            if len(surface) < 2:
                continue
            overlapping = self._overlapping(analyzed, match.start(), match.end())
            if not self._preserve_surface(surface, overlapping):
                continue
            value = self._substitute(surface)
            if self._is_redundant_surface(value, overlapping, match.start(), match.end()):
                continue
            surfaces[value] += 1
        for surface, frequency in surfaces.items():
            tokens.extend([surface] * max(0, frequency - counts[surface]))
        return tokens

    def tokenize(self, text: str) -> list[str]:
        """문자열 하나를 BM25 색인용 내용어와 보존 표면형 목록으로 변환함.

        반환값: 정규화된 형태소와 필요한 카드명·코드 원형을 입력 출현 횟수만큼 담은 목록임.
        부수효과: 형태소 분석을 위해 메모리의 Kiwi 인스턴스를 사용함.
        """

        normalized = normalize_korean_text(text)
        analyzed = self._kiwi.tokenize(normalized, oov_handling=self._oov_handling)
        return self._from_analysis(normalized, analyzed)

    def tokenize_many(self, texts: Iterable[str]) -> list[list[str]]:
        """여러 문자열을 Kiwi 배치 분석으로 토큰화하여 입력 순서대로 반환함.

        반환값: 입력이 비면 빈 목록, 아니면 각 문서의 BM25 토큰 목록임.
        부수효과: 형태소 분석을 위해 메모리의 Kiwi 인스턴스를 사용함.
        """

        normalized = [normalize_korean_text(text) for text in texts]
        if not normalized:
            return []
        analyzed = self._kiwi.tokenize(normalized, oov_handling=self._oov_handling)
        return [
            self._from_analysis(text, tokens)
            for text, tokens in zip(normalized, analyzed, strict=True)
        ]

    def extract_oov_candidates(
        self,
        texts: Iterable[str],
        *,
        min_count: int = 10,
        max_word_length: int = 10,
        min_score: float = 0.25,
        pos_score: float = -3.0,
    ) -> list[OOVCandidate]:
        """자동 등록하지 않고 사람이 검토할 미등록어 후보를 추출함.

        인자: min_count는 최소 출현 횟수, max_word_length는 최대 글자 수이며 두 점수는 Kiwi 판정 기준임.
        반환값: Kiwi가 반환한 순서를 유지한 후보 목록임.
        부수효과: 없음. 후보를 사용자 사전에 등록하지 않음.
        """

        values = self._kiwi.extract_words(
            (normalize_korean_text(text) for text in texts),
            min_cnt=min_count,
            max_word_len=max_word_length,
            min_score=min_score,
            pos_score=pos_score,
        )
        return [
            OOVCandidate(str(form), float(score), int(frequency), float(candidate_pos_score))
            for form, score, frequency, candidate_pos_score in values
        ]


__all__ = [
    "KoreanTokenizer",
    "OOVCandidate",
    "PlainNounChecker",
    "POLICY_DESCRIPTOR",
    "lexical_policy_fingerprint",
    "normalize_korean_text",
    "unify_date_notation",
]
