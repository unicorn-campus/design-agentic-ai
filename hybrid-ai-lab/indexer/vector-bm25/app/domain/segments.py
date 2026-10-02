"""대상(카드 등) 경계로 문서를 먼저 끊고 색인용 머리말을 붙이는 순수 규칙임."""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
import re
import unicodedata
from typing import Any, Mapping

from app.domain.models import LoadedDocument, TextSpan


def _squash(value: str) -> str:
    """공백·대소문자·전각 차이를 없앤 비교용 문자열을 만듦."""

    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(value)).lower())


@dataclass(frozen=True)
class HeaderPolicy:
    """색인용 머리말의 서식과 본문 중복 생략 규칙을 보관함."""

    template: str = ""  # 모든 필드가 본문에 없을 때 쓸 서식
    field_templates: tuple[tuple[str, str], ...] = ()  # (필드, 그 필드만 본문에 없을 때 쓸 서식)
    separator: str = "\n"  # 머리말과 본문 사이에 넣을 문자열

    @property
    def enabled(self) -> bool:
        """이 정책이 머리말을 만들 수 있는지 반환함."""

        return bool(self.template and self.field_templates)

    @property
    def fields(self) -> tuple[str, ...]:
        """머리말에 넣을 필드를 설정에 적힌 순서대로 반환함."""

        return tuple(name for name, _template in self.field_templates)

    def full(self, values: Mapping[str, str]) -> str:
        """본문을 보지 않고 모든 필드를 넣은 머리말을 만듦.

        목적: 분할 전에 머리말 몫의 토큰을 미리 빼 두기 위해 가장 긴 형태를 구함.
        반환값: 값이 하나라도 비면 빈 문자열임.
        """

        if not self.enabled or any(not str(values.get(name, "")).strip() for name in self.fields):
            return ""
        return self.template.format(**{name: str(values[name]).strip() for name in self.fields})

    def compose(self, values: Mapping[str, str], body: str) -> str:
        """본문에 없는 값만 모아 머리말을 만듦.

        목적: 본문이 이미 카드명을 담고 있으면 같은 말을 두 번 넣지 않기 위함.
        방법: 공백·대소문자를 없앤 본문과 대조해 새 값만 남기고, 남은 필드 수에 맞는 서식을 고름.
        반환값: 새 값이 없으면 빈 문자열임.
        """

        if not self.enabled:
            return ""
        squashed = _squash(body)
        present = {
            name: str(values.get(name, "")).strip()
            for name in self.fields
            if str(values.get(name, "")).strip()
            and _squash(str(values[name])) not in squashed
        }
        if len(present) == len(self.fields):
            return self.template.format(**present)
        for name, template in self.field_templates:
            if name in present and len(present) == 1:
                return template.format(**present)
        return ""


@dataclass(frozen=True)
class SegmentPolicy:
    """문서를 대상 단위로 끊는 경계와 구간이 확정할 메타데이터 규칙을 보관함."""

    boundary_regex: str = ""  # 대상 구간이 시작하는 줄을 찾을 정규식(첫 캡처가 대상 코드)
    tail_regex: str = ""  # 마지막 구간 안에서 참고 목록이 시작하는 줄을 찾을 정규식
    key_field: str = ""  # 문맥 정보에서 대상 코드를 담은 키
    value_fields: tuple[str, ...] = ()  # 코드와 함께 구간 값으로 쓸 문맥 키
    metadata_fields: tuple[tuple[str, str], ...] = ()  # (메타데이터 키, 구간 값 이름)
    clear_keys: tuple[str, ...] = ()  # 구간 값으로 덮기 전에 지울 메타데이터 키
    ambiguity_keys: tuple[str, ...] = ()  # 모두 비어 있으면 context_ambiguous 표시를 지움
    header: HeaderPolicy = field(default_factory=HeaderPolicy)

    @property
    def enabled(self) -> bool:
        """이 정책이 하드 경계 분할을 수행하는지 반환함."""

        return bool(self.boundary_regex and self.key_field)


@dataclass(frozen=True)
class SegmentBinding:
    """한 구간이 그 안의 모든 청크에 강제하는 값과 머리말 규칙을 함께 전달함."""

    values: tuple[tuple[str, str], ...] = ()  # 구간이 확정한 (값 이름, 값). 비면 '대상 없음' 구간임
    metadata_fields: tuple[tuple[str, str], ...] = ()
    clear_keys: tuple[str, ...] = ()
    ambiguity_keys: tuple[str, ...] = ()
    header: HeaderPolicy = field(default_factory=HeaderPolicy)

    def value_map(self) -> dict[str, str]:
        """구간이 확정한 값을 dict로 반환함."""

        return dict(self.values)

    def index_header(self, body: str) -> str:
        """이 구간의 값으로 본문에 붙일 색인용 머리말을 만듦."""

        return self.header.compose(self.value_map(), body)

    def reserved_header(self) -> str:
        """분할 전에 토큰 몫을 빼 둘 가장 긴 머리말을 만듦."""

        return self.header.full(self.value_map())

    def apply(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """구간이 확정한 대상으로 메타데이터를 덮어쓴 새 dict를 반환함.

        목적: 조각이 경계를 넘어 합쳐지며 엉뚱한 대상이 붙던 오류를 구간 기준으로 바로잡음.
        방법: 먼저 대상 관련 키를 모두 지우고 구간 값만 채운 뒤, 남은 모호성 표시를 정리함.
        반환값: 입력을 바꾸지 않은 새 dict임. '대상 없음' 구간이면 대상 키가 아예 없음.
        """

        result = {key: value for key, value in metadata.items() if key not in self.clear_keys}
        values = self.value_map()
        for target, name in self.metadata_fields:
            value = str(values.get(name, "")).strip()
            if value:
                result[target] = value
        if not any(result.get(key) for key in self.ambiguity_keys):
            # 대상이 하나로 확정되었으므로 "여러 대상에 걸침" 표시는 더 이상 맞지 않음.
            result.pop("context_ambiguous", None)
        return result


@dataclass(frozen=True)
class Segment:
    """정제 본문에서 한 대상이 차지하는 구간임."""

    start: int  # 정제 본문 기준 첫 문자 위치(포함)
    end: int  # 정제 본문 기준 끝 위치(미포함)
    binding: SegmentBinding = field(default_factory=SegmentBinding)

    @property
    def targeted(self) -> bool:
        """이 구간이 대상 하나에 속하는지 반환함. 표지·목차·참고 목록은 False임."""

        return bool(self.binding.values)


def _context_values(document: LoadedDocument, policy: SegmentPolicy) -> dict[str, dict[str, str]]:
    """문맥 구간에서 대상 코드별 값(카드명 등)을 모음."""

    found: dict[str, dict[str, str]] = {}
    for span in document.context_spans:
        value = span.value if isinstance(span.value, dict) else {}
        code = str(value.get(policy.key_field, "")).strip()
        if not code:
            continue
        entry = found.setdefault(code, {})
        for name in policy.value_fields:
            text = str(value.get(name, "")).strip()
            if text and name not in entry:
                entry[name] = text
    return found


def _tail_start(text: str, policy: SegmentPolicy, last_start: int) -> int | None:
    """문서 끝 참고 목록이 시작하는 위치를 찾음.

    목적: "D2-C001 | 참고 카드: ..." 같은 출처 목록이 마지막 대상 구간에 딸려 들어가지 않게 떼어 냄.
    방법: 마지막 구간 안에서 참고 항목 형태의 첫 줄을 찾고, 그 앞 빈 줄까지 거슬러 올라가 제목 줄도 포함함.
    반환값: 참고 목록 시작 위치이며 그런 구간이 없으면 None임.
    """

    if not policy.tail_regex:
        return None
    match = re.compile(policy.tail_regex).search(text, last_start)
    if match is None:
        return None
    blank = text.rfind("\n\n", last_start, match.start())
    return blank + 2 if blank >= 0 else match.start()


def plan_segments(document: LoadedDocument, policy: SegmentPolicy) -> tuple[Segment, ...]:
    """정제 본문을 대상 구간과 '대상 없음' 구간으로 나눔.

    목적: 분할기가 조각을 합칠 때 다른 대상의 설명까지 한 청크로 묶는 것을 막기 위함.
    방법: 경계 정규식이 잡은 줄마다 구간을 열고, 첫 경계 이전과 문서 끝 참고 목록은 대상 없음으로 둠.
    인자: policy가 꺼져 있거나 경계를 찾지 못하면 문서 전체를 대상 없는 구간 하나로 돌려줌.
    반환값: 본문 순서대로 이어 붙이면 원문 전체가 되는 구간 목록임.
    부수효과: 없음.
    """

    whole = (Segment(0, len(document.text)),)
    if not policy.enabled:
        return whole
    matches = list(re.compile(policy.boundary_regex).finditer(document.text))
    if not matches:
        return whole

    values_by_code = _context_values(document, policy)
    starts = [item.start() for item in matches]
    codes = [item.group(1) for item in matches]
    tail = _tail_start(document.text, policy, starts[-1])
    end_of_targets = tail if tail is not None else len(document.text)

    def binding(code: str | None) -> SegmentBinding:
        """구간 코드로 메타데이터·머리말 규칙을 묶음. 코드가 없으면 대상 없음 구간임."""

        values: tuple[tuple[str, str], ...] = ()
        if code:
            found = {policy.key_field: code, **values_by_code.get(code, {})}
            values = tuple(sorted(found.items()))
        return SegmentBinding(
            values=values,
            metadata_fields=policy.metadata_fields,
            clear_keys=policy.clear_keys,
            ambiguity_keys=policy.ambiguity_keys,
            header=policy.header,
        )

    segments: list[Segment] = []
    if starts[0] > 0:
        segments.append(Segment(0, starts[0], binding(None)))  # 표지·목차
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else end_of_targets
        if start < end:
            segments.append(Segment(start, end, binding(codes[index])))
    if tail is not None and tail < len(document.text):
        segments.append(Segment(tail, len(document.text), binding(None)))  # 문서 끝 참고 목록
    return tuple(segments)


def clip_spans(spans: tuple[TextSpan, ...], start: int, end: int) -> tuple[TextSpan, ...]:
    """구간과 겹치는 위치 정보만 남기고 좌표를 구간 기준으로 옮김."""

    return tuple(
        TextSpan(max(span.start, start) - start, min(span.end, end) - start, span.value)
        for span in spans
        if span.end > start and span.start < end
    )


def segment_document(document: LoadedDocument, segment: Segment) -> LoadedDocument:
    """한 구간만 담은 문서를 만들되 문서 ID·메타데이터·정책 키는 그대로 둠.

    반환값: 본문과 페이지·문맥 위치를 구간 기준으로 옮긴 새 LoadedDocument임.
    부수효과: 없음.
    """

    return dataclasses.replace(
        document,
        text=document.text[segment.start : segment.end],
        page_spans=clip_spans(document.page_spans, segment.start, segment.end),
        context_spans=clip_spans(document.context_spans, segment.start, segment.end),
    )


__all__ = [
    "HeaderPolicy",
    "Segment",
    "SegmentBinding",
    "SegmentPolicy",
    "clip_spans",
    "plan_segments",
    "segment_document",
]
