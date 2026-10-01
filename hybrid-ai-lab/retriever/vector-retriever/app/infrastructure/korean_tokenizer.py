"""BM25 문서와 질의에 동일하게 적용하는 한국어 토크나이저."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Iterable, Sequence
import unicodedata


_POLICY_VERSION = 2
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


def normalize_korean_text(text: str) -> str:
    """전각 문자와 숫자 표기를 검색에 안정적인 형태로 정규화함."""

    normalized = unicodedata.normalize("NFKC", str(text)).lower()
    return _NUMBER_COMMA.sub("", normalized)


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
            "name": "kiwi-content-and-surface",
            "policy_version": _POLICY_VERSION,
            "kiwipiepy": self._version,
            "normalization": "nfkc-lower-remove-numeric-comma-v1",
            "content_tags": sorted(_CONTENT_TAGS),
            "tag_normalization": "strip-kiwi-regularity-suffix-v1",
            "surface_policy": "number-unit-code-dictionary-clean-compound-v2",
            "stopword_policy": "content-pos-filter-v1",
            "oov_handling": self._oov_handling,
            "typo_policy": self._typo_policy,
            "typo_cost_threshold": self._typo_cost_threshold,
            "user_dictionary_sha256": self._dictionary_hash,
        }
        if self._additional_user_word_count:
            value["additional_user_words_sha256"] = self._additional_dictionary_hash
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return f"kiwi:{hashlib.sha256(encoded).hexdigest()}"

    @property
    def user_dictionary_sha256(self) -> str:
        return self._dictionary_hash

    @property
    def additional_user_words_sha256(self) -> str:
        return self._additional_dictionary_hash

    def with_additional_user_words(
        self,
        words: Iterable[tuple[str, str, float]],
    ) -> KoreanTokenizer:
        """동일한 기본 설정에 추가 사용자 단어만 적용한 새 객체를 만듦."""

        return type(self)(
            self._dictionary_path,
            additional_user_words=words,
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

    def _tokens_from_analysis(self, normalized: str, analyzed: Sequence[object]) -> list[str]:
        tokens = [
            normalize_korean_text(str(getattr(token, "form"))).replace(" ", "")
            for token in analyzed
            if _base_tag(str(getattr(token, "tag"))) in _CONTENT_TAGS
        ]
        tokens = [token for token in tokens if token]

        counts = Counter(tokens)
        surface_counts: Counter[str] = Counter()
        for match in _SURFACE_TOKEN.finditer(normalized):
            surface = match.group(0)
            if len(surface) < 2:
                continue
            overlapping = self._overlapping_tokens(analyzed, match.start(), match.end())
            if self._preserve_surface(surface, overlapping):
                surface_counts[surface] += 1
        for surface, frequency in surface_counts.items():
            tokens.extend([surface] * max(0, frequency - counts[surface]))
        return tokens

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
