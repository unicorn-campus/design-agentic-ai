"""BM25 문서와 질의에 동일하게 적용하는 한국어 토크나이저."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, Mapping, Sequence
import unicodedata

from ..domain.keywords import TermObservation


_POLICY_VERSION = 4
_NORMALIZATION_POLICY = "nfkc-lower-remove-numeric-comma-iso-date-v2"
_SURFACE_POLICY = "number-unit-code-dictionary-clean-compound-alias-v3"
# 버전 2는 띄어 쓴 별칭 표면형을 등록해 "가게모음 프리미엄"이 기본 카드로 치환되지 않게 한 정책임.
_ALIAS_POLICY = "card-name-spaced-surface-v2"
_CONTENT_TAGS = frozenset(
    {
        "NNG", "NNP", "NNB", "NP", "NR", "VV", "VA", "VX", "VCP",
        "VCN", "MM", "MAG", "MAJ", "IC", "SL", "SH", "SN", "XR",
    }
)
_SURFACE_TOKEN = re.compile(r"[0-9a-z가-힣]+(?:[-_/][0-9a-z가-힣]+)*%?")
_NUMBER_COMMA = re.compile(r"(?<=\d),(?=\d)")
_ASCII_LETTER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")
_CODE_SEPARATOR = re.compile(r"[-_/]")

# 날짜 표기 통일: 색인 문서의 "2026-02"와 질문의 "2026년 2월"이 같은 토큰이 되도록 ISO 모양으로 맞춤.
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
class TypoTokenization:
    """원문 분석과 질의 전용 오타 교정 분석을 구분해 반환함."""

    original: tuple[str, ...]
    corrected: tuple[str, ...]

    @property
    def changed(self) -> bool:
        return self.original != self.corrected


@dataclass(frozen=True)
class OOVCandidate:
    """사전 자동 등록 없이 검토 대상으로만 반환하는 미등록어 후보."""

    form: str
    score: float
    frequency: int
    pos_score: float


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
    반환값: 날짜 자리만 바뀐 문자열이며 이미 ISO 모양이면 그대로임.
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
    """전각 문자·숫자·날짜 표기를 검색에 안정적인 형태로 정규화함."""

    normalized = unicodedata.normalize("NFKC", str(text)).lower()
    return unify_date_notation(_NUMBER_COMMA.sub("", normalized))


def _base_tag(tag: str) -> str:
    """Kiwi의 ``VA-I``·``VV-R`` 활용 표지를 기본 품사로 정규화함."""

    return str(tag).split("-", 1)[0]


class KoreanTokenizer:
    """Kiwi 형태소와 제한된 원형 복합어를 함께 보존하는 토크나이저."""

    def __init__(
        self,
        user_dictionary: Path | None = None,
        *,
        additional_user_words: Iterable[tuple[str, str, float]] | None = None,
        aliases: Mapping[str, str] | None = None,
        num_workers: int | None = None,
        oov_handling: str = "chr",
        typo_policy: str = "basic",
        typo_cost_threshold: float = 2.5,
    ) -> None:
        try:
            import kiwipiepy
            from kiwipiepy import Kiwi
        except ImportError as error:  # pragma: no cover - 설치 오류 안내 경로
            raise RuntimeError("한국어 BM25를 사용하려면 kiwipiepy가 필요함") from error

        self._kiwi = Kiwi(num_workers=num_workers)
        self._version = str(getattr(kiwipiepy, "__version__", "unknown"))
        self._dictionary_path = Path(user_dictionary).resolve() if user_dictionary else None
        self._dictionary_hash = ""
        self._additional_dictionary_hash = hashlib.sha256(b"").hexdigest()
        self._num_workers = num_workers
        self._oov_handling = str(oov_handling)
        self._typo_policy = str(typo_policy)
        self._typo_cost_threshold = float(typo_cost_threshold)
        dictionary_surfaces: set[str] = set()
        if self._dictionary_path:
            payload = self._dictionary_path.read_bytes()
            self._dictionary_hash = hashlib.sha256(payload).hexdigest()
            # 공식 로더가 품사·점수·이형태·기분석 형식을 모두 처리함.
            self._kiwi.load_user_dictionary(str(self._dictionary_path))
            dictionary_surfaces.update(self._read_dictionary_surfaces(payload))

        additional_words = self._normalize_additional_words(additional_user_words or ())
        self._additional_user_word_count = len(additional_words)
        additional_payload = self.additional_user_words_payload(additional_words)
        self._additional_dictionary_hash = hashlib.sha256(additional_payload).hexdigest()
        for form, tag, score in additional_words:
            self._kiwi.add_user_word(form, tag, score)
            dictionary_surfaces.add(form.replace(" ", ""))

        self._alias_surfaces = self.normalize_aliases(aliases)
        self._alias_hash = hashlib.sha256(self.alias_payload(self._alias_surfaces)).hexdigest()
        self._aliases = {
            surface.replace(" ", ""): canonical
            for surface, canonical in self._alias_surfaces.items()
        }
        for surface in self._alias_surfaces:
            # 별칭을 사전에 올려야 Kiwi가 "모아생활"을 모으+어+생활로 쪼개지 않고 한 덩어리로 봄.
            # 띄어 쓴 표면형을 등록하면 "가게모음 프리미엄"과 "가게모음프리미엄"이 모두 같은 단어로 잡힘.
            self._kiwi.add_user_word(surface, _ALIAS_TAG, _ALIAS_SCORE)
            dictionary_surfaces.add(surface.replace(" ", ""))
        self._dictionary_surfaces = frozenset(dictionary_surfaces)

    @staticmethod
    def _normalize_additional_words(
        words: Iterable[tuple[str, str, float]],
    ) -> tuple[tuple[str, str, float], ...]:
        normalized: set[tuple[str, str, float]] = set()
        for raw_form, raw_tag, raw_score in words:
            raw_form_text = str(raw_form)
            if "\t" in raw_form_text or "\n" in raw_form_text or "\r" in raw_form_text:
                raise ValueError("추가 사용자 단어의 형태에는 탭이나 줄바꿈을 넣을 수 없음")
            form = " ".join(normalize_korean_text(raw_form_text).split())
            tag = str(raw_tag).strip()
            score = float(raw_score)
            if not form or not tag:
                raise ValueError("추가 사용자 단어의 형태와 품사는 비어 있을 수 없음")
            normalized.add((form, tag, score))
        return tuple(sorted(normalized))

    @classmethod
    def additional_user_words_payload(
        cls,
        words: Iterable[tuple[str, str, float]],
    ) -> bytes:
        """추가 사용자 단어를 결정적인 Kiwi 사전 파일 내용으로 직렬화함."""

        normalized = cls._normalize_additional_words(words)
        return "".join(
            f"{form}\t{tag}\t{score}\n" for form, tag, score in normalized
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
                raise ValueError("별칭에는 탭이나 줄바꿈을 넣을 수 없음")
            surface = " ".join(normalize_korean_text(raw_alias).split())
            canonical = normalize_korean_text(raw_canonical).replace(" ", "")
            alias = surface.replace(" ", "")
            if not alias or not canonical:
                raise ValueError("별칭과 정식 카드 토큰은 비어 있을 수 없음")
            if alias == canonical:
                raise ValueError(f"별칭과 정식 카드 토큰이 같음: {surface}")
            if keys.setdefault(alias, surface) != surface:
                # Kiwi는 사용자 단어를 공백과 무관하게 한 항목으로 보므로 띄어쓰기만 다른 중복을 금지함.
                raise ValueError(f"띄어쓰기만 다른 별칭이 함께 있음: {surface}")
            if normalized.get(surface, canonical) != canonical:
                raise ValueError(f"같은 별칭이 서로 다른 카드를 가리킴: {surface}")
            normalized[surface] = canonical
        return {surface: normalized[surface] for surface in sorted(normalized)}

    @classmethod
    def alias_payload(cls, aliases: Mapping[str, str] | None) -> bytes:
        """별칭 표면형 치환표를 결정적인 UTF-8 TSV 파일 내용으로 직렬화함."""

        return "".join(
            f"{surface}\t{canonical}\n"
            for surface, canonical in cls.normalize_aliases(aliases).items()
        ).encode("utf-8")

    @staticmethod
    def _read_dictionary_surfaces(payload: bytes) -> frozenset[str]:
        surfaces: set[str] = set()
        for raw_line in payload.decode("utf-8-sig").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            form = normalize_korean_text(line.split("\t", 1)[0]).replace(" ", "")
            if len(form) >= 2:
                surfaces.add(form)
        return frozenset(surfaces)

    @property
    def signature(self) -> str:
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
        return self._dictionary_hash

    @property
    def additional_user_words_sha256(self) -> str:
        return self._additional_dictionary_hash

    @property
    def alias_map_sha256(self) -> str:
        """정규화된 별칭 치환표 TSV의 SHA-256 해시를 반환함."""

        return self._alias_hash

    def with_additional_user_words(
        self,
        words: Iterable[tuple[str, str, float]],
        *,
        aliases: Mapping[str, str] | None = None,
    ) -> KoreanTokenizer:
        """동일한 기본 설정에 추가 사용자 단어와 별칭만 적용한 새 객체를 만듦."""

        return type(self)(
            self._dictionary_path,
            additional_user_words=words,
            aliases=aliases,
            num_workers=self._num_workers,
            oov_handling=self._oov_handling,
            typo_policy=self._typo_policy,
            typo_cost_threshold=self._typo_cost_threshold,
        )

    @staticmethod
    def _overlapping_tokens(tokens: Sequence[object], start: int, end: int) -> list[object]:
        return [
            token
            for token in tokens
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
                normalize_korean_text(str(getattr(token, "form"))).replace(" ", "")
            )
            if form == value:
                return True
        return False

    def _preserve_surface(self, surface: str, overlapping: Sequence[object]) -> bool:
        compact = surface.replace(" ", "")
        if _DIGIT.search(compact):
            return True
        if _ASCII_LETTER.search(compact) and _CODE_SEPARATOR.search(compact):
            return True
        if compact in self._dictionary_surfaces:
            return True
        base_tags = [_base_tag(str(getattr(token, "tag"))) for token in overlapping]
        return len(base_tags) >= 2 and all(tag in _CONTENT_TAGS for tag in base_tags)

    def _is_proper(self, value: str, tag: str) -> bool:
        """토큰이 고유이름(카드명·별칭·숫자·코드·날짜 표준형)인지 판정함.

        목적: 색인에 없는 말이라도 고유이름이면 핵심어로 남겨야 하므로 구분이 필요함.
        부수효과: 없음.
        """

        if value in self._dictionary_surfaces:
            return True
        if tag in {"NNP", "SL", "SH", "SN"}:
            return True
        return bool(_DIGIT.search(value) or _CODE_SEPARATOR.search(value))

    def _terms_from_analysis(
        self, normalized: str, analyzed: Sequence[object]
    ) -> list[TermObservation]:
        """BM25 토큰과 그 품사·고유이름 여부를 같은 순서로 함께 만듦.

        목적: 색인에 들어간 토큰과 글자 하나까지 같은 값을 핵심어 판정에도 쓰기 위함.
        반환값: tokenize가 내보내는 토큰과 같은 순서·같은 개수의 관찰값 목록임.
        부수효과: 없음.
        """

        terms: list[TermObservation] = []
        for token in analyzed:
            tag = _base_tag(str(getattr(token, "tag")))
            if tag not in _CONTENT_TAGS:
                continue
            value = self._substitute(
                normalize_korean_text(str(getattr(token, "form"))).replace(" ", "")
            )
            if not value:
                continue
            terms.append(TermObservation(value, tag, self._is_proper(value, tag)))

        counts = Counter(term.token for term in terms)
        surface_counts: Counter[str] = Counter()
        for match in _SURFACE_TOKEN.finditer(normalized):
            surface = match.group(0)
            if len(surface) < 2:
                continue
            overlapping = self._overlapping_tokens(analyzed, match.start(), match.end())
            if not self._preserve_surface(surface, overlapping):
                continue
            value = self._substitute(surface)
            if self._is_redundant_surface(value, overlapping, match.start(), match.end()):
                continue
            surface_counts[value] += 1
        for surface, frequency in surface_counts.items():
            extra = max(0, frequency - counts[surface])
            observation = TermObservation(surface, "SURFACE", self._is_proper(surface, "SURFACE"))
            terms.extend([observation] * extra)
        return terms

    def _tokens_from_analysis(self, normalized: str, analyzed: Sequence[object]) -> list[str]:
        return [term.token for term in self._terms_from_analysis(normalized, analyzed)]

    def observe(self, text: str) -> tuple[TermObservation, ...]:
        """문자열을 색인과 같은 토큰으로 자르고 품사·고유이름 여부를 함께 반환함.

        목적: 핵심어 선별이 색인에 실제로 들어 있는 토큰만 다루도록 보장함.
        반환값: tokenize와 같은 순서·같은 토큰에 품사와 고유이름 여부를 붙인 묶음임.
        부수효과: 형태소 분석에 메모리의 Kiwi 인스턴스를 사용함.
        """

        normalized = normalize_korean_text(text)
        analyzed = self._kiwi.tokenize(normalized, oov_handling=self._oov_handling)
        return tuple(self._terms_from_analysis(normalized, analyzed))

    def tokenize(self, text: str) -> list[str]:
        """오타 교정을 적용하지 않은 기준 토큰을 반환함."""

        normalized = normalize_korean_text(text)
        analyzed = self._kiwi.tokenize(normalized, oov_handling=self._oov_handling)
        return self._tokens_from_analysis(normalized, analyzed)

    def tokenize_many(self, texts: Iterable[str]) -> list[list[str]]:
        """색인 문서를 Kiwi iterable API로 순서 보존 병렬 분석함."""

        normalized = [normalize_korean_text(text) for text in texts]
        if not normalized:
            return []
        analyzed = self._kiwi.tokenize(normalized, oov_handling=self._oov_handling)
        return [
            self._tokens_from_analysis(text, tokens)
            for text, tokens in zip(normalized, analyzed, strict=True)
        ]

    def tokenize_with_typo_fallback(self, text: str) -> TypoTokenization:
        """원 질의와 기본 오타 교정 질의를 별도 토큰 집합으로 반환함."""

        normalized = normalize_korean_text(text)
        original = self._tokens_from_analysis(
            normalized,
            self._kiwi.tokenize(normalized, oov_handling=self._oov_handling),
        )
        corrected = self._tokens_from_analysis(
            normalized,
            self._kiwi.tokenize(
                normalized,
                oov_handling=self._oov_handling,
                typos=self._typo_policy,
                typo_cost_threshold=self._typo_cost_threshold,
            ),
        )
        return TypoTokenization(tuple(original), tuple(corrected))

    def extract_oov_candidates(
        self,
        texts: Iterable[str],
        *,
        min_cnt: int = 10,
        max_word_len: int = 10,
        min_score: float = 0.25,
        pos_score: float = -3.0,
    ) -> list[OOVCandidate]:
        """미등록어 후보만 반환하며 Kiwi 사용자 사전에는 추가하지 않음."""

        candidates = self._kiwi.extract_words(
            (normalize_korean_text(text) for text in texts),
            min_cnt=min_cnt,
            max_word_len=max_word_len,
            min_score=min_score,
            pos_score=pos_score,
        )
        return [
            OOVCandidate(
                form=str(form),
                score=float(score),
                frequency=int(frequency),
                pos_score=float(candidate_pos_score),
            )
            for form, score, frequency, candidate_pos_score in candidates
        ]
