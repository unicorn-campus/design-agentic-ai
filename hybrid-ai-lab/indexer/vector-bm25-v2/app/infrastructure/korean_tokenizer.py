"""Indexer와 Retriever가 공유하는 한국어 BM25 토큰화 정책임."""

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
        "NNG", "NNP", "NNB", "NP", "NR", "VV", "VA", "VX", "VCP", "VCN",
        "MM", "MAG", "MAJ", "IC", "SL", "SH", "SN", "XR",
    }
)
_SURFACE_TOKEN = re.compile(r"[0-9a-z가-힣]+(?:[-_/][0-9a-z가-힣]+)*%?")
_NUMBER_COMMA = re.compile(r"(?<=\d),(?=\d)")
_ASCII_LETTER = re.compile(r"[a-z]")
_DIGIT = re.compile(r"\d")
_CODE_SEPARATOR = re.compile(r"[-_/]")


@dataclass(frozen=True)
class OOVCandidate:
    """Kiwi가 제안한 미등록어와 자동 등록하지 않는 검토용 점수를 담음."""

    form: str  # 후보 단어의 표면형
    score: float  # Kiwi가 계산한 단어 후보 점수
    frequency: int  # 전체 입력 문서에서 발견된 횟수
    pos_score: float  # 후보의 품사 적합도 점수


def normalize_korean_text(text: str) -> str:
    """NFKC·소문자 변환 후 숫자 사이 쉼표를 제거한 검색용 문자열을 반환함."""

    return _NUMBER_COMMA.sub("", unicodedata.normalize("NFKC", str(text)).lower())


def _base_tag(tag: str) -> str:
    """Kiwi 규칙성 접미사를 제거한 기본 품사 태그를 반환함."""

    return str(tag).split("-", 1)[0]


class KoreanTokenizer:
    """내용어와 카드명·코드 원형을 함께 보존하는 Kiwi 어댑터임.

    사용자 사전·동적 카드명·Kiwi 생성자를 주입받으며, BM25 점수 계산이나 파일 저장은 수행하지 않음.
    """

    def __init__(
        self,
        user_dictionary: Path | None = None,
        *,
        additional_user_words: Iterable[tuple[str, str, float]] = (),
        num_workers: int = 1,
        oov_handling: str = "chr",
        typo_policy: str = "basic",
        typo_cost_threshold: float = 2.5,
        kiwi_factory=None,
        library_version: str | None = None,
    ) -> None:
        """형태소 분석기와 검색어 보존 정책을 설정함.

        인자: typo_cost_threshold는 검색 측 오타 교정 계약에 기록할 비용 상한임.
        예외: kiwipiepy가 없거나 사용자 사전을 읽지 못하면 해당 예외를 발생시킴.
        부수효과: 사용자 사전을 읽고 Kiwi 인스턴스에 사용자 단어를 등록함.
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
        """정적 사용자 사전의 SHA-256 해시를 반환하며, 사전이 없으면 빈 문자열임."""

        return self._dictionary_hash

    @property
    def additional_user_words_sha256(self) -> str:
        """정규화된 동적 사용자 단어 사전의 SHA-256 해시를 반환함."""

        return self._additional_dictionary_hash

    @staticmethod
    def _overlapping(tokens: Sequence[object], start: int, end: int) -> list[object]:
        """문자 범위와 한 글자 이상 겹치는 Kiwi 토큰을 반환함."""

        return [
            token for token in tokens
            if int(getattr(token, "start")) < end and int(getattr(token, "end")) > start
        ]

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
            normalize_korean_text(getattr(token, "form")).replace(" ", "")
            for token in analyzed
            if _base_tag(str(getattr(token, "tag"))) in _CONTENT_TAGS
        ]
        tokens = [token for token in tokens if token]
        counts = Counter(tokens)
        surfaces: Counter[str] = Counter()
        for match in _SURFACE_TOKEN.finditer(normalized):
            surface = match.group(0)
            if len(surface) >= 2 and self._preserve_surface(
                surface, self._overlapping(analyzed, match.start(), match.end())
            ):
                surfaces[surface] += 1
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


__all__ = ["KoreanTokenizer", "OOVCandidate", "normalize_korean_text"]
