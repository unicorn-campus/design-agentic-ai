"""LanguageModelPort를 LangChain 채팅 모델로 구현한 어댑터임(커넥터 C-01 ~ C-04).

모델 객체를 밖(bootstrap)에서 받아 씀 — 지금은 C-01 ~ C-04 모두 Groq(gpt-oss-120b)임.
재시도는 0회임. 실패는 ConnectorError로 올리고, 대체 경로 선택은 부르는 단계의 몫임(설계 슬라이드 18 ~ 19).
"""

from __future__ import annotations

import inspect
import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping, Sequence

import groq
from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.application.models import (
    ActionInput,
    ActionOutput,
    AnswerInput,
    AnswerOutput,
    ConnectorError,
    ConnectorErrorKind,
    PlanInput,
    PlanOutput,
    TransformInput,
    TransformOutput,
)
from app.application.ports import LanguageModelPort
from app.domain.actions import ACTION_FINISH, ACTION_SEARCH, ACTION_TRANSFORM
from app.domain.models import QTYPE_CHITCHAT, QTYPE_COMPLEX, QTYPE_SIMPLE
from app.domain.transform_rules import ALLOWED_TECHNIQUES
from app.domain.verification import AnswerSentence, Citation
from app.infrastructure.chat_models import C01, C02, C03, C04

# 커넥터별 타임아웃(초, 설계 ③)
DEFAULT_TIMEOUTS: dict[str, float] = {C01: 2.5, C02: 1.5, C03: 1.2, C04: 2.5}

# 시스템 프롬프트 파일명 — 설계서 [NOTES] 전문을 그대로 담은 파일임(문구를 코드에 복사하지 않음)
PROMPT_FILES: dict[str, str] = {
    C01: "c01_plan.md",
    C02: "c02_action.md",
    C03: "c03_transform.md",
    C04: "c04_answer.md",
}


# ---------------------------------------------------------------- 응답 스키마(구조화 출력)
#
# 열거 값은 도메인 상수에서 가져와 규칙과 스키마가 어긋나지 않게 함. 모든 필드를 필수로 두고 extra를 막음 —
# 구조화 출력의 strict 규칙이 '모든 필드 required · 추가 필드 금지'를 요구하기 때문임. 그래서 선택 필드도
# '빈 문자열·빈 배열로 채움'으로 프롬프트에 적고 스키마에서는 필수로 둠.


class _Strict(BaseModel):
    """스키마 공통 설정. 모르는 필드가 오면 거절해 응답 형식 변화가 조용히 지나가지 않게 함."""

    model_config = ConfigDict(extra="forbid")


class PlanResult(_Strict):
    """C-01 질문 분석·계획 응답(설계 슬라이드 27)."""

    question_type: Literal[QTYPE_CHITCHAT, QTYPE_SIMPLE, QTYPE_COMPLEX] = Field(description="질문 유형")
    sub_questions: list[str] = Field(description="complex일 때 하위 질문 1 ~ 3개, 그 외 빈 배열")
    chitchat_reply: str = Field(description="chitchat일 때 1 ~ 2문장, 그 외 빈 문자열")
    reason: str = Field(description="그렇게 나눈 이유 1문장")


class ActionResult(_Strict):
    """C-02 다음 행동 선택 응답(설계 슬라이드 29)."""

    action: Literal[ACTION_SEARCH, ACTION_TRANSFORM, ACTION_FINISH] = Field(description="다음 행동 1개")
    target_sub_question_id: str = Field(description="finish면 빈 문자열")
    reason: str = Field(description="선택 이유 1문장")


class TransformResult(_Strict):
    """C-03 질문 변환 응답(설계 슬라이드 31)."""

    technique: Literal[ALLOWED_TECHNIQUES] = Field(description="변환 기법 1개")
    queries: list[str] = Field(description="검색용 질의 1 ~ 3개, keep·clarify면 빈 배열")
    include_original_query: bool = Field(description="원 질문도 함께 검색할지")
    clarify_question: str = Field(description="clarify일 때 되물을 1문장")
    reason: str = Field(description="기법 선택 이유 1문장")


class CitationItem(_Strict):
    """C-04 답변 문장 1개에 달린 인용 1건."""

    chunk_id: str = Field(description="근거 조각ID")
    quote: str = Field(description="조각 본문에서 그대로 복사")


class SentenceItem(_Strict):
    """C-04 답변 문장 1개와 그 근거 목록."""

    text: str = Field(description="답변 문장 1개")
    citations: list[CitationItem] = Field(description="그 문장의 근거 인용 목록")


class AnswerResult(_Strict):
    """C-04 답변 생성 응답(설계 슬라이드 33)."""

    sentences: list[SentenceItem] = Field(description="문장마다 인용이 달린 답변 초안")
    unresolved_sub_questions: list[str] = Field(description="근거가 부족한 하위 질문ID")
    needs_confirmation_note: str = Field(description="없으면 빈 문자열")


RESULT_SCHEMAS: dict[str, type[BaseModel]] = {
    C01: PlanResult,
    C02: ActionResult,
    C03: TransformResult,
    C04: AnswerResult,
}

# 분류 신호 → 오류 분류(설계 슬라이드 19). 5xx는 코드로 따로 판정하므로 여기에 넣지 않음
STATUS_KINDS: dict[int, ConnectorErrorKind] = {
    401: "auth",
    403: "auth",
    429: "rate_limit",
    400: "format",
    422: "format",
    498: "capacity",
    499: "cancelled",
}

# SDK 예외를 뜻별 묶음으로 봄. 제공자가 늘어도 이 묶음만 넓히면 분류 규칙은 그대로임
TIMEOUT_ERRORS = (groq.APITimeoutError,)
SCHEMA_ERRORS = (groq.APIResponseValidationError,)
STATUS_ERRORS = (groq.APIStatusError,)
CONNECTION_ERRORS = (groq.APIConnectionError,)
# 구조화 출력 파싱·검증 실패. 모델이 거절(stop_reason refusal)해 본문이 비어도 파서가 여기로 떨어짐
PARSE_ERRORS = (OutputParserException, ValidationError, json.JSONDecodeError)


def _connector_error(
    connector_id: str,
    kind: ConnectorErrorKind,
    message: str,
    *,
    status: int | None = None,
    elapsed: float = 0.0,
) -> ConnectorError:
    """ConnectorError 1건을 만듦. 소요 시간을 함께 담아 감사 로그가 타임아웃 여유를 볼 수 있게 함."""

    return ConnectorError(connector_id, kind, message, status_code=status, elapsed_seconds=elapsed)


# ---------------------------------------------------------------- 유저 프롬프트 조립


def _escape(value: Any) -> str:
    """XML 태그 안에 넣을 본문 데이터에서 태그를 여닫는 기호(`<`·`>`)만 무력화함.

    인자: 문자열이 아니면 str()로 바꿈(조각 메타데이터에 숫자가 섞여도 깨지지 않게 함).
    반환값: `<`·`>`를 실체 참조로 바꾼 문자열임. `&`·`"`는 그대로 둠.
    왜: 질문·조각 본문에 `</질문>` 같은 글자가 있어도 태그가 일찍 닫히지 않아야 함. 태그가 닫히면
    그 뒤 글자가 '데이터'가 아니라 지시문 자리로 올라가 프롬프트 인젝션이 됨(설계 슬라이드 25).
    `&`·`"`까지 바꾸면 C-04가 `&amp;`를 그대로 인용해 S-R8의 글자 대조가 실패하므로 본문에서는 바꾸지 않음.
    """

    text = str(value)
    return text.replace("<", "&lt;").replace(">", "&gt;")


def _escape_attribute(value: Any) -> str:
    """속성값(id·title)에 넣을 데이터를 무력화함. 따옴표로 속성을 닫지 못하게 `&`·`"`까지 바꿈."""

    return _escape(str(value).replace("&", "&amp;")).replace('"', "&quot;")


def _tag(name: str, body: str) -> str:
    """데이터 1덩이를 XML 태그로 감쌈. 본문은 이미 무력화된 문자열이어야 함."""

    return f"<{name}>\n{body}\n</{name}>"


def _chunk_block(chunks: Sequence[Mapping[str, Any]]) -> str:
    """조각 목록을 `<조각 id="…" title="…">본문</조각>` 줄로 바꿈.

    반환값: 조각이 없으면 빈 문자열임. id·title·본문 모두 무력화해 속성값으로도 태그를 깰 수 없게 함.
    """

    lines = []
    for chunk in chunks:
        chunk_id = _escape_attribute(chunk.get("chunk_id", ""))
        title = _escape_attribute(chunk.get("title", ""))
        text = _escape(chunk.get("text", ""))
        lines.append(f'<조각 id="{chunk_id}" title="{title}">{text}</조각>')
    return "\n".join(lines)


def _fields(payload: Mapping[str, Any]) -> str:
    """태그로 감싸지 않는 나머지 필드를 JSON 1덩이로 바꿈.

    왜: 목록·객체 필드는 태그보다 JSON이 읽기 쉽고, 값에 따옴표가 섞여도 json이 알아서 피함.
    """

    return json.dumps(payload, ensure_ascii=False, indent=2)


def _structured(model: Any, schema: type[BaseModel]) -> Any:
    """채팅 모델에 구조화 출력(json_schema)을 씌운 실행 사슬을 만듦.

    방법: strict 인자를 받는 제공자(Groq)에만 strict=True를 넘김. 그 인자가 없는 제공자는
    넘기면 조용히 무시되므로, 넘기는지 여부를 서명으로 보고 정함.
    반환값: invoke(메시지 목록) → 스키마 인스턴스를 돌려주는 Runnable임.
    예외: 제공자가 json_schema 방식을 지원하지 않으면 그 제공자의 예외를 그대로 올림.
    """

    options: dict[str, Any] = {"method": "json_schema"}
    if "strict" in inspect.signature(model.with_structured_output).parameters:
        options["strict"] = True
    return model.with_structured_output(schema, **options)


class LangChainLanguageModel(LanguageModelPort):
    """LangChain 채팅 모델로 C-01 ~ C-04를 수행하는 어댑터임.

    모델 객체는 밖(bootstrap)에서 이미 설정을 마친 채로 들어옴 — 어댑터는 하이퍼파라미터를 건드리지 않고
    프롬프트 조립·구조화 출력·마감 시간·오류 분류만 책임짐.
    """

    def __init__(
        self,
        models: Mapping[str, Any],
        timeouts: Mapping[str, float] | None = None,
        prompt_dir: Path | str | None = None,
    ) -> None:
        """커넥터별 모델과 타임아웃을 받아 구조화 출력 사슬과 시스템 프롬프트를 준비함.

        인자: models는 커넥터ID("C-01" ~ "C-04") → 설정이 끝난 LangChain 채팅 모델임. 네 개가 모두 있어야 함.
        인자: timeouts는 커넥터ID → 초이며 빠진 커넥터는 DEFAULT_TIMEOUTS 값을 씀.
        인자: prompt_dir는 시스템 프롬프트 파일 폴더이며 기본값은 이 모듈 옆 prompts 폴더임.
        예외: 커넥터가 빠지면 ValueError, 프롬프트 파일이 없으면 FileNotFoundError를 올림
        (둘 다 서버 시작 때 바로 드러나게 함).
        부수효과: 없음 — 생성 시점에는 외부 호출을 하지 않음.
        """

        missing = [connector_id for connector_id in PROMPT_FILES if connector_id not in models]
        if missing:
            raise ValueError(f"커넥터 모델이 빠짐: {', '.join(missing)}")
        self._timeouts = {**DEFAULT_TIMEOUTS, **dict(timeouts or {})}
        base = Path(prompt_dir) if prompt_dir is not None else Path(__file__).parent / "prompts"
        self._system_prompts = {
            connector_id: (base / filename).read_text(encoding="utf-8")
            for connector_id, filename in PROMPT_FILES.items()
        }
        self._chains = {
            connector_id: _structured(models[connector_id], RESULT_SCHEMAS[connector_id])
            for connector_id in PROMPT_FILES
        }
        # 호출 전체 마감 시간을 거는 데 쓰는 스레드. SDK timeout은 연결·읽기 단계마다 따로 걸려
        # 첫 호출(연결 수립 포함)이 2.5초 타임아웃에서 3.8초까지 늘어난 실측이 있어 따로 둠
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm-call")

    # ------------------------------------------------------------------ 포트 구현

    def analyze_question(self, payload: PlanInput) -> PlanOutput:
        """C-01: 질문 유형과 하위 질문을 받음(포트 docstring 참조)."""

        fields: dict[str, Any] = {"max_sub_questions": payload.max_sub_questions}
        if payload.today is not None:
            # today는 선택 필드임 — 없을 때 null을 넣으면 '기준일이 없다'는 지시로 읽힐 수 있어 키째 빼 둠
            fields["today"] = payload.today
        prompt = "\n\n".join([_tag("질문", _escape(payload.user_question)), _fields(fields)])
        result: PlanResult = self._call(C01, prompt)
        return PlanOutput(
            question_type=result.question_type,
            sub_questions=tuple(result.sub_questions),
            chitchat_reply=result.chitchat_reply,
            reason=result.reason,
        )

    def choose_action(self, payload: ActionInput) -> ActionOutput:
        """C-02: 허용 행동 목록 안에서 다음 행동 1개를 받음(포트 docstring 참조)."""

        fields = {
            "allowed_actions": list(payload.allowed_actions),
            "sub_question_states": [dict(state) for state in payload.sub_question_states],
            "remaining_turns": payload.remaining_turns,
        }
        prompt = "\n\n".join([_tag("질문", _escape(payload.original_question)), _fields(fields)])
        result: ActionResult = self._call(C02, prompt)
        return ActionOutput(
            action=result.action,
            target_sub_question_id=result.target_sub_question_id,
            reason=result.reason,
        )

    def transform_query(self, payload: TransformInput) -> TransformOutput:
        """C-03: 변환 기법 1개와 검색용 질의를 받음(포트 docstring 참조)."""

        fields = {
            "target_sub_question": payload.target_sub_question,
            "grading_evidence": dict(payload.grading_evidence),
            "previous_attempts": [dict(attempt) for attempt in payload.previous_attempts],
            "technique_guide": [dict(guide) for guide in payload.technique_guide],
            "allowed_techniques": list(payload.allowed_techniques),
        }
        prompt = "\n\n".join(
            [
                _tag("원질문", _escape(payload.original_question)),
                _tag("검색결과", _chunk_block(payload.result_chunks)),
                _fields(fields),
            ]
        )
        result: TransformResult = self._call(C03, prompt)
        return TransformOutput(
            technique=result.technique,
            queries=tuple(result.queries),
            include_original_query=result.include_original_query,
            clarify_question=result.clarify_question,
            reason=result.reason,
        )

    def generate_answer(self, payload: AnswerInput) -> AnswerOutput:
        """C-04: 문장마다 인용이 달린 답변 초안을 받음(포트 docstring 참조)."""

        fields = {
            "sub_questions": [dict(item) for item in payload.sub_questions],
            "rewrite_reason": payload.rewrite_reason,
            "attempt_no": payload.attempt_no,
        }
        prompt = "\n\n".join(
            [
                _tag("원질문", _escape(payload.original_question)),
                _tag("근거", _chunk_block(payload.evidence_chunks)),
                _fields(fields),
            ]
        )
        result: AnswerResult = self._call(C04, prompt)
        return AnswerOutput(
            sentences=_sentences(result),
            unresolved_sub_questions=tuple(result.unresolved_sub_questions),
            needs_confirmation_note=result.needs_confirmation_note,
        )

    # ------------------------------------------------------------------ 호출·오류 분류

    def _call(self, connector_id: str, user_prompt: str) -> Any:
        """커넥터 1개를 1회 부르고 검증을 마친 응답 스키마 인스턴스를 돌려줌.

        반환값: RESULT_SCHEMAS[connector_id] 인스턴스임.
        예외: 모든 실패를 ConnectorError로 바꿔 올림. 분류는 설계 슬라이드 19 표를 따름.
        부수효과: 외부 API 호출 1회. 재시도는 하지 않음.
        """

        timeout = self._timeouts[connector_id]
        started = time.monotonic()
        messages = [
            SystemMessage(content=self._system_prompts[connector_id]),
            HumanMessage(content=user_prompt),
        ]
        future = self._executor.submit(self._chains[connector_id].invoke, messages)
        try:
            # 마감 시간이 지나면 응답을 기다리지 않고 timeout으로 처리함 — 최악값 = 타임아웃이 되게 함(설계 ③).
            # 늦게 도착한 응답은 버림. 스레드는 SDK 단계별 timeout에 걸려 곧 끝나므로 쌓이지 않음
            result = future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise _connector_error(
                connector_id, "timeout", f"{connector_id} 응답 시간 초과", elapsed=time.monotonic() - started
            ) from None
        except Exception as error:  # noqa: BLE001 — 분류 뒤 ConnectorError로 바꿔 올리므로 여기서 모두 받음
            raise _classify(connector_id, error, time.monotonic() - started) from error

        elapsed = time.monotonic() - started
        if not isinstance(result, RESULT_SCHEMAS[connector_id]):
            # 구조화 출력이 꺼지거나 바뀌면 dict가 돌아올 수 있음 — 조용히 넘기지 않고 형식 오류로 세움
            raise _connector_error(
                connector_id, "format", f"{connector_id} 응답이 약속한 구조가 아님", elapsed=elapsed
            )
        return result


def _sentences(result: AnswerResult) -> tuple[AnswerSentence, ...]:
    """C-04 응답을 도메인 AnswerSentence·Citation으로 바꿈.

    반환값: 문장 순서를 지킨 AnswerSentence 묶음임. 인용이 0개인 문장도 그대로 담음 — 걸러내지 않음.
    왜: 인용 없는 문장을 실패로 판정하는 일은 S-R8 근거 검증의 몫이며, 커넥터가 미리 지우면
    '왜 실패했는지'가 사라져 재작성 사유를 만들 수 없음(설계 슬라이드 32).
    """

    return tuple(
        AnswerSentence(
            text=sentence.text,
            citations=tuple(
                Citation(chunk_id=citation.chunk_id, quote=citation.quote) for citation in sentence.citations
            ),
        )
        for sentence in result.sentences
    )


def _causes(error: BaseException) -> Iterator[BaseException]:
    """예외와 그 원인 사슬을 바깥에서 안쪽 순서로 훑음.

    왜: LangChain이 SDK 예외를 한 겹 감싸는 경우가 있어, 겉만 보면 모든 실패가 unknown으로 뭉개짐.
    반환값: 같은 예외를 두 번 내지 않는 반복자임(순환 참조로 무한 반복하지 않게 함).
    """

    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _classify(connector_id: str, error: Exception, elapsed: float) -> ConnectorError:
    """SDK·파서 예외를 설계 슬라이드 19의 분류로 바꿈.

    반환값: ConnectorError. 메시지에는 예외 종류·상태 코드만 담고 API 키·질문 원문은 넣지 않음.
    왜 순서가 중요한가: APITimeoutError는 APIConnectionError의 하위 종류라 먼저 봐야 timeout이 capacity로
    뭉개지지 않음. 429의 retry-after는 읽지 않음 — 재시도를 하지 않으므로 쓸 자리가 없음.
    """

    for cause in _causes(error):
        if isinstance(cause, TIMEOUT_ERRORS):
            return _connector_error(connector_id, "timeout", f"{connector_id} 응답 시간 초과", elapsed=elapsed)
        if isinstance(cause, SCHEMA_ERRORS):
            return _connector_error(connector_id, "format", f"{connector_id} 응답이 스키마와 다름", elapsed=elapsed)
        if isinstance(cause, STATUS_ERRORS):
            status = getattr(cause, "status_code", None)
            return _connector_error(
                connector_id, _status_kind(status), f"{connector_id} HTTP {status} 오류", status=status, elapsed=elapsed
            )
        if isinstance(cause, CONNECTION_ERRORS):
            # 연결 실패는 '지금 받아 줄 쪽이 없음'이라 용량 부족과 같은 칸으로 봄(설계 슬라이드 19)
            return _connector_error(connector_id, "capacity", f"{connector_id} 연결 실패", elapsed=elapsed)
        if isinstance(cause, PARSE_ERRORS):
            return _connector_error(
                connector_id, "format", f"{connector_id} 응답을 약속한 형식으로 읽지 못함", elapsed=elapsed
            )
    return _connector_error(
        connector_id, "unknown", f"{connector_id} 알 수 없는 오류: {type(error).__name__}", elapsed=elapsed
    )


def _status_kind(status: int | None) -> ConnectorErrorKind:
    """HTTP 상태 코드를 오류 분류로 바꿈. 표에 없는 5xx는 용량 부족, 나머지는 unknown임."""

    if status is None:
        return "unknown"
    if status in STATUS_KINDS:
        return STATUS_KINDS[status]
    if status >= 500:
        return "capacity"
    return "unknown"
