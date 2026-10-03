"""LanguageModelPort를 Groq Chat Completions로 구현한 어댑터임(커넥터 C-01 ~ C-04).

설계 고정값을 커넥터마다 상수로 박아 둠 — 호출하는 단계가 하이퍼파라미터를 흔들 수 없게 함(설계 슬라이드 25 ~ 33).
재시도는 0회임. 실패는 ConnectorError로 올리고, 대체 경로 선택은 부르는 단계의 몫임(설계 슬라이드 18 ~ 19).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import groq

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

# 커넥터ID — 오류·감사 로그가 어느 호출에서 났는지 가리키는 값임(설계 슬라이드 25)
C01 = "C-01"
C02 = "C-02"
C03 = "C-03"
C04 = "C-04"

DEFAULT_MODEL = "openai/gpt-oss-120b"

# 커넥터별 타임아웃(초). 설계 슬라이드 18·23의 값이며 합계 최악값 26.2초가 예산 30초에 맞춰진 근거임
DEFAULT_TIMEOUTS: dict[str, float] = {C01: 2.5, C02: 1.5, C03: 1.2, C04: 2.5}

# 시스템 프롬프트 파일명 — 설계서 [NOTES] 전문을 그대로 담은 파일임(문구를 코드에 복사하지 않음)
PROMPT_FILES: dict[str, str] = {
    C01: "c01_plan.md",
    C02: "c02_action.md",
    C03: "c03_transform.md",
    C04: "c04_answer.md",
}


def _string_array(description: str) -> dict[str, Any]:
    """문자열 배열 스키마 조각을 만듦. 같은 모양이 네 커넥터에 반복되므로 한 곳에서 찍어 냄."""

    return {"type": "array", "items": {"type": "string"}, "description": description}


def _obj(properties: dict[str, Any]) -> dict[str, Any]:
    """strict 스키마 규칙(모든 필드 required · additionalProperties false)을 자동으로 채운 객체 스키마를 만듦.

    근거: Groq structured outputs는 strict:true일 때 두 조건을 모두 요구함(docs/structured-outputs).
    그래서 선택 필드도 '빈 문자열·빈 배열로 채움'으로 프롬프트에 적고 스키마에서는 필수로 둠.
    """

    return {
        "type": "object",
        "properties": properties,
        "required": list(properties),
        "additionalProperties": False,
    }


# 커넥터별 응답 스키마. 열거 값은 도메인 상수에서 가져와 규칙과 스키마가 어긋나지 않게 함
RESPONSE_SCHEMAS: dict[str, dict[str, Any]] = {
    C01: {
        "name": "plan_result",
        "strict": True,
        "schema": _obj(
            {
                "question_type": {"type": "string", "enum": [QTYPE_CHITCHAT, QTYPE_SIMPLE, QTYPE_COMPLEX]},
                "sub_questions": _string_array("complex일 때 하위 질문 1 ~ 3개, 그 외 빈 배열"),
                "chitchat_reply": {"type": "string", "description": "chitchat일 때 1 ~ 2문장, 그 외 빈 문자열"},
                "reason": {"type": "string", "description": "그렇게 나눈 이유 1문장"},
            }
        ),
    },
    C02: {
        "name": "action_result",
        "strict": True,
        "schema": _obj(
            {
                "action": {"type": "string", "enum": [ACTION_SEARCH, ACTION_TRANSFORM, ACTION_FINISH]},
                "target_sub_question_id": {"type": "string", "description": "finish면 빈 문자열"},
                "reason": {"type": "string", "description": "선택 이유 1문장"},
            }
        ),
    },
    C03: {
        "name": "transform_result",
        "strict": True,
        "schema": _obj(
            {
                "technique": {"type": "string", "enum": list(ALLOWED_TECHNIQUES)},
                "queries": _string_array("검색용 질의 1 ~ 3개, keep·clarify면 빈 배열"),
                "include_original_query": {"type": "boolean", "description": "원 질문도 함께 검색할지"},
                "clarify_question": {"type": "string", "description": "clarify일 때 되물을 1문장"},
                "reason": {"type": "string", "description": "기법 선택 이유 1문장"},
            }
        ),
    },
    C04: {
        "name": "answer_result",
        "strict": True,
        "schema": _obj(
            {
                "sentences": {
                    "type": "array",
                    "items": _obj(
                        {
                            "text": {"type": "string", "description": "답변 문장 1개"},
                            "citations": {
                                "type": "array",
                                "items": _obj(
                                    {
                                        "chunk_id": {"type": "string"},
                                        "quote": {"type": "string", "description": "조각 본문에서 그대로 복사"},
                                    }
                                ),
                            },
                        }
                    ),
                },
                "unresolved_sub_questions": _string_array("근거가 부족한 하위 질문ID"),
                "needs_confirmation_note": {"type": "string", "description": "없으면 빈 문자열"},
            }
        ),
    },
}


@dataclass(frozen=True)
class _CallSpec:
    """커넥터 1개의 고정 하이퍼파라미터. 설계 슬라이드 26·28·30·32의 표를 그대로 옮긴 값임."""

    connector_id: str
    temperature: float
    max_completion_tokens: int
    seed: int


# C-04만 temperature 0.2임 — 문장을 생성하는 자리라서임(사실은 근거가 고정하므로 흔들려도 안전)
CALL_SPECS: dict[str, _CallSpec] = {
    C01: _CallSpec(C01, 0.0, 700, 1001),
    C02: _CallSpec(C02, 0.0, 400, 1002),
    C03: _CallSpec(C03, 0.0, 700, 1003),
    C04: _CallSpec(C04, 0.2, 1800, 1004),
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


@dataclass(frozen=True)
class _Result:
    """커넥터 1회 호출의 응답 본문과 소요 시간임.

    호출마다 새로 만들어 넘김 — 어댑터 인스턴스에 호출 상태를 쌓지 않아 한 객체를 여러 요청이 함께 써도 안전함.
    """

    connector_id: str
    data: Mapping[str, Any]
    elapsed: float

    def _missing(self, key: str) -> ConnectorError:
        """필드 누락·타입 불일치를 format 오류로 만듦. 키 이름만 담고 값은 담지 않음."""

        return _connector_error(
            self.connector_id,
            "format",
            f"{self.connector_id} 응답 필드 '{key}' 누락 또는 형식 오류",
            elapsed=self.elapsed,
        )

    def text(self, key: str) -> str:
        """문자열 필드를 꺼냄. strict 스키마가 통과시켰어도 서버 쪽 변화를 대비해 다시 확인함."""

        value = self.data.get(key)
        if not isinstance(value, str):
            raise self._missing(key)
        return value

    def flag(self, key: str) -> bool:
        """불리언 필드를 꺼냄. 0·1 같은 값은 받지 않음(기법 강제 규칙이 참·거짓만 다룸)."""

        value = self.data.get(key)
        if not isinstance(value, bool):
            raise self._missing(key)
        return value

    def str_list(self, key: str) -> tuple[str, ...]:
        """문자열 배열 필드를 꺼냄. 원소 하나라도 문자열이 아니면 format 오류임."""

        value = self.data.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise self._missing(key)
        return tuple(value)

    def sentences(self) -> tuple[AnswerSentence, ...]:
        """C-04 sentences를 도메인 AnswerSentence·Citation으로 바꿈.

        반환값: 문장 순서를 지킨 AnswerSentence 묶음임. 인용이 0개인 문장도 그대로 담음 — 걸러내지 않음.
        왜: 인용 없는 문장을 실패로 판정하는 일은 S-R8 근거 검증의 몫이며, 커넥터가 미리 지우면
        '왜 실패했는지'가 사라져 재작성 사유를 만들 수 없음(설계 슬라이드 32).
        예외: 구조가 어긋나면 format 분류의 ConnectorError를 올림.
        """

        raw = self.data.get("sentences")
        if not isinstance(raw, list):
            raise self._missing("sentences")
        sentences: list[AnswerSentence] = []
        for item in raw:
            if not isinstance(item, Mapping):
                raise self._missing("sentences")
            text = item.get("text")
            citations_raw = item.get("citations")
            if not isinstance(text, str) or not isinstance(citations_raw, list):
                raise self._missing("sentences")
            citations: list[Citation] = []
            for citation in citations_raw:
                if not isinstance(citation, Mapping):
                    raise self._missing("sentences[].citations")
                chunk_id = citation.get("chunk_id")
                quote = citation.get("quote")
                if not isinstance(chunk_id, str) or not isinstance(quote, str):
                    raise self._missing("sentences[].citations")
                citations.append(Citation(chunk_id=chunk_id, quote=quote))
            sentences.append(AnswerSentence(text=text, citations=tuple(citations)))
        return tuple(sentences)


class GroqLanguageModel(LanguageModelPort):
    """Groq Chat Completions로 C-01 ~ C-04를 수행하는 어댑터임.

    클라이언트는 생성 때 1개만 만들고 max_retries=0으로 고정함 — SDK 기본값 2회 재시도가
    단계 타임아웃을 몰래 2 ~ 3배로 늘리는 일을 막음(설계 '재시도 0회').
    타임아웃은 호출마다 with_options(timeout=…)로 커넥터별 값을 씌움.
    """

    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        timeouts: Mapping[str, float] | None = None,
        reasoning_effort: str = "low",
        prompt_dir: Path | str | None = None,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        """커넥터 공통 설정을 받아 클라이언트와 시스템 프롬프트를 준비함.

        인자: api_key는 비밀값 저장소에서 환경변수로 들어온 값이며 어디에도 기록하지 않음.
        인자: timeouts는 커넥터ID → 초이며 빠진 커넥터는 DEFAULT_TIMEOUTS 값을 씀.
        인자: prompt_dir는 시스템 프롬프트 파일 폴더이며 기본값은 이 모듈 옆 prompts 폴더임.
        인자: client_factory는 시험에서 가짜 클라이언트를 끼우는 자리임(기본값은 groq.Groq).
        예외: 시스템 프롬프트 파일이 없으면 FileNotFoundError를 올림(서버 시작 때 바로 드러나게 함).
        부수효과: 없음 — 생성 시점에는 외부 호출을 하지 않음.
        """

        self._model = model
        self._reasoning_effort = reasoning_effort
        self._timeouts = {**DEFAULT_TIMEOUTS, **dict(timeouts or {})}
        base = Path(prompt_dir) if prompt_dir is not None else Path(__file__).parent / "prompts"
        self._system_prompts = {
            connector_id: (base / filename).read_text(encoding="utf-8")
            for connector_id, filename in PROMPT_FILES.items()
        }
        factory = client_factory or groq.Groq
        self._client = factory(api_key=api_key, max_retries=0)
        # 호출 전체 마감 시간을 거는 데 쓰는 스레드. SDK timeout은 연결·읽기 단계마다 따로 걸려
        # 첫 호출(연결 수립 포함)이 2.5초 타임아웃에서 3.8초까지 늘어난 실측이 있어 따로 둠
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="groq-call")

    # ------------------------------------------------------------------ 포트 구현

    def analyze_question(self, payload: PlanInput) -> PlanOutput:
        """C-01: 질문 유형과 하위 질문을 받음(포트 docstring 참조)."""

        fields: dict[str, Any] = {"max_sub_questions": payload.max_sub_questions}
        if payload.today is not None:
            # today는 선택 필드임 — 없을 때 null을 넣으면 '기준일이 없다'는 지시로 읽힐 수 있어 키째 빼 둠
            fields["today"] = payload.today
        prompt = "\n\n".join([_tag("질문", _escape(payload.user_question)), _fields(fields)])
        result = self._call(C01, prompt)
        return PlanOutput(
            question_type=result.text("question_type"),
            sub_questions=result.str_list("sub_questions"),
            chitchat_reply=result.text("chitchat_reply"),
            reason=result.text("reason"),
        )

    def choose_action(self, payload: ActionInput) -> ActionOutput:
        """C-02: 허용 행동 목록 안에서 다음 행동 1개를 받음(포트 docstring 참조)."""

        fields = {
            "allowed_actions": list(payload.allowed_actions),
            "sub_question_states": [dict(state) for state in payload.sub_question_states],
            "remaining_turns": payload.remaining_turns,
        }
        prompt = "\n\n".join([_tag("질문", _escape(payload.original_question)), _fields(fields)])
        result = self._call(C02, prompt)
        return ActionOutput(
            action=result.text("action"),
            target_sub_question_id=result.text("target_sub_question_id"),
            reason=result.text("reason"),
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
        result = self._call(C03, prompt)
        return TransformOutput(
            technique=result.text("technique"),
            queries=result.str_list("queries"),
            include_original_query=result.flag("include_original_query"),
            clarify_question=result.text("clarify_question"),
            reason=result.text("reason"),
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
        result = self._call(C04, prompt)
        return AnswerOutput(
            sentences=result.sentences(),
            unresolved_sub_questions=result.str_list("unresolved_sub_questions"),
            needs_confirmation_note=result.text("needs_confirmation_note"),
        )

    # ------------------------------------------------------------------ 호출·오류 분류

    def _call(self, connector_id: str, user_prompt: str) -> _Result:
        """커넥터 고정값으로 Groq를 1회 부르고 응답 본문을 _Result로 돌려줌.

        반환값: json_schema를 통과한 응답을 파싱한 _Result임.
        예외: 모든 실패를 ConnectorError로 바꿔 올림. 분류는 설계 슬라이드 19 표를 따름.
        부수효과: 외부 API 호출 1회. 재시도는 하지 않음.
        """

        spec = CALL_SPECS[connector_id]
        timeout = self._timeouts[connector_id]
        started = time.monotonic()
        request = self._client.with_options(timeout=timeout).chat.completions.create
        future = self._executor.submit(
            request,
            model=self._model,
            messages=[
                {"role": "system", "content": self._system_prompts[connector_id]},
                {"role": "user", "content": user_prompt},
            ],
            temperature=spec.temperature,
            top_p=1,
            max_completion_tokens=spec.max_completion_tokens,
            seed=spec.seed,
            reasoning_effort=self._reasoning_effort,
            # 설계서의 reasoning_format=hidden은 gpt-oss가 지원하지 않아 include_reasoning=False로 대신함
            # (사용자 결정). 추론 문장을 응답에서 빼 JSON 본문만 받는 효과는 같음
            include_reasoning=False,
            response_format={"type": "json_schema", "json_schema": RESPONSE_SCHEMAS[connector_id]},
        )
        try:
            # 마감 시간이 지나면 응답을 기다리지 않고 timeout으로 처리함 — 최악값 = 타임아웃이 되게 함(설계 ③).
            # 늦게 도착한 응답은 버림. 스레드는 SDK 단계별 timeout에 걸려 곧 끝나므로 쌓이지 않음
            completion = future.result(timeout=timeout)
        except FutureTimeoutError:
            future.cancel()
            raise _connector_error(
                connector_id, "timeout", f"{connector_id} 응답 시간 초과", elapsed=time.monotonic() - started
            ) from None
        except Exception as error:  # noqa: BLE001 — 분류 뒤 ConnectorError로 바꿔 올리므로 여기서 모두 받음
            raise _classify(connector_id, error, time.monotonic() - started) from error

        return _parse(connector_id, completion, time.monotonic() - started)


def _classify(connector_id: str, error: Exception, elapsed: float) -> ConnectorError:
    """SDK 예외를 설계 슬라이드 19의 분류로 바꿈.

    반환값: ConnectorError. 메시지에는 예외 종류·상태 코드만 담고 API 키·질문 원문은 넣지 않음.
    왜 순서가 중요한가: APITimeoutError는 APIConnectionError의 하위 종류라 먼저 봐야 timeout이 capacity로
    뭉개지지 않음. 429의 retry-after는 읽지 않음 — 재시도를 하지 않으므로 쓸 자리가 없음.
    """

    if isinstance(error, groq.APITimeoutError):
        return _connector_error(connector_id, "timeout", f"{connector_id} 응답 시간 초과", elapsed=elapsed)
    if isinstance(error, groq.APIResponseValidationError):
        return _connector_error(connector_id, "format", f"{connector_id} 응답이 스키마와 다름", elapsed=elapsed)
    if isinstance(error, groq.APIStatusError):
        status = getattr(error, "status_code", None)
        kind = _status_kind(status)
        return _connector_error(
            connector_id, kind, f"{connector_id} HTTP {status} 오류", status=status, elapsed=elapsed
        )
    if isinstance(error, groq.APIConnectionError):
        # 연결 실패는 '지금 받아 줄 쪽이 없음'이라 용량 부족과 같은 칸으로 봄(설계 슬라이드 19)
        return _connector_error(connector_id, "capacity", f"{connector_id} 연결 실패", elapsed=elapsed)
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


def _parse(connector_id: str, completion: Any, elapsed: float) -> _Result:
    """응답 본문 문자열을 _Result로 바꿈. 깨진 JSON·빈 본문은 format 오류임."""

    try:
        content = completion.choices[0].message.content
    except (AttributeError, IndexError, TypeError) as error:
        raise _connector_error(
            connector_id, "format", f"{connector_id} 응답 구조가 비었음", elapsed=elapsed
        ) from error
    if not isinstance(content, str) or not content.strip():
        raise _connector_error(connector_id, "format", f"{connector_id} 응답 본문이 비었음", elapsed=elapsed)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as error:
        raise _connector_error(
            connector_id, "format", f"{connector_id} 응답이 JSON이 아님", elapsed=elapsed
        ) from error
    if not isinstance(data, Mapping):
        raise _connector_error(connector_id, "format", f"{connector_id} 응답이 객체가 아님", elapsed=elapsed)
    return _Result(connector_id, data, elapsed)
