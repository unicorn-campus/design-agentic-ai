"""표현 계층(API·CLI) 시험. 가짜 서비스를 주입해 색인·모델·LLM 없이 계약을 확인함."""

from __future__ import annotations

import io
import json
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.application.models import (
    STATUS_ANSWERED,
    STATUS_ERROR,
    AnswerSentenceOut,
    CitationOut,
    EvidenceOut,
    ScoresOut,
    SearchRequest,
    SearchResponse,
    UnresolvedOut,
)
from app.presentation.api import create_app
from app.presentation.cli import main


class FakeService:
    """RetrieverService 모양의 가짜. 받은 요청·역할을 기록하고 정해진 응답을 돌려줌."""

    def __init__(self, response: SearchResponse, health: dict[str, Any] | None = None) -> None:
        self.response = response
        self._health = health or {
            "ready": True,
            "generation": "gen-test-001",
            "chunk_count": 218,
            "loading": False,
            "last_error": None,
        }
        self.calls: list[tuple[SearchRequest, str | None]] = []

    def execute(self, request: SearchRequest, role: str | None) -> SearchResponse:
        self.calls.append((request, role))
        return self.response

    def health(self) -> dict[str, Any]:
        return dict(self._health)


def answered_response() -> SearchResponse:
    """근거·답변·확인 못 한 항목이 모두 든 정상 응답을 만듦."""

    return SearchResponse(
        request_id="req-0001",
        status=STATUS_ANSWERED,
        answer=[
            AnswerSentenceOut(
                text="연회비는 1만원임.",
                citations=[CitationOut(chunk_id="c-001", quote="연회비 1만원")],
            )
        ],
        evidence=[
            EvidenceOut(
                rank=1,
                chunk_id="c-001",
                text="연회비는 1만원이며 첫해는 면제임.",
                source="카드안내.pdf",
                doc_key="card-guide",
                page=12,
                card_name="테스트카드",
                scores=ScoresOut(vector=0.81, bm25=3.21, fused=0.74, rerank=0.91),
            )
        ],
        unresolved=[UnresolvedOut(sub_question_id="q2", question="해외 수수료", reason="근거 0건")],
        question_type="complex",
        generation="gen-test-001",
        llm_calls=3,
        timings={"S-R4": 0.42, "S-R1": 0.01},
        warnings=["리랭커 실패로 융합 점수를 씀"],
        finish_reason="verified",
    )


def error_response(code: str) -> SearchResponse:
    """오류 코드별 표준 오류 응답을 만듦."""

    return SearchResponse(
        request_id="req-0002",
        status=STATUS_ERROR,
        message="요청을 처리할 수 없습니다.",
        error_code=code,
    )


def test_api_passes_header_role_to_service() -> None:
    """역할은 X-User-Role 헤더 값으로만 서비스에 전달됨."""

    service = FakeService(answered_response())
    client = TestClient(create_app(service))

    result = client.post("/search", json={"query": "연회비"}, headers={"X-User-Role": "auditor"})

    assert result.status_code == 200
    assert result.json()["status"] == STATUS_ANSWERED
    assert service.calls[0][1] == "auditor"


def test_api_ignores_role_in_request_body() -> None:
    """요청 본문의 role은 무시되고 헤더가 없으면 역할을 None으로 넘김(서비스가 role_missing 판정)."""

    service = FakeService(error_response("role_missing"))
    client = TestClient(create_app(service))

    result = client.post("/search", json={"query": "연회비", "role": "auditor"})

    request, role = service.calls[0]
    assert role is None
    assert not hasattr(request, "role")
    assert result.status_code == 401


def test_api_passes_options_to_service() -> None:
    """답변 생성 여부·반환 수는 본문 값 그대로 서비스에 전달됨."""

    service = FakeService(answered_response())
    client = TestClient(create_app(service))

    client.post(
        "/search",
        json={"query": "연회비", "generate_answer": True, "top_k": 3},
        headers={"X-User-Role": "agent"},
    )

    request, _ = service.calls[0]
    assert (request.query, request.generate_answer, request.top_k) == ("연회비", True, 3)


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("invalid_input", 400),
        ("role_missing", 401),
        ("invalid_role", 403),
        ("index_unavailable", 503),
        ("broken_state", 500),
        ("internal_error", 500),
        ("unknown_future_code", 500),
    ],
)
def test_api_maps_error_code_to_http_status(code: str, expected: int) -> None:
    """오류 코드는 ERROR_HTTP_STATUS로 HTTP 상태에 대응되고, 모르는 코드는 500임."""

    client = TestClient(create_app(FakeService(error_response(code))))

    result = client.post("/search", json={"query": "연회비"}, headers={"X-User-Role": "agent"})

    assert result.status_code == expected
    assert result.json()["error_code"] == code


def test_api_returns_200_when_no_error_code() -> None:
    """오류 코드가 없으면 상태가 무엇이든 200으로 돌려줌."""

    response = answered_response()
    response.status = "needs_confirmation"
    client = TestClient(create_app(FakeService(response)))

    result = client.post("/search", json={"query": "연회비"}, headers={"X-User-Role": "agent"})

    assert result.status_code == 200
    assert result.json()["error_code"] is None


def test_api_rejects_malformed_body_with_422() -> None:
    """질문이 빠진 본문은 FastAPI 기본 검증이 422로 막음(서비스를 부르지 않음)."""

    service = FakeService(answered_response())
    client = TestClient(create_app(service))

    result = client.post("/search", json={"top_k": 3}, headers={"X-User-Role": "agent"})

    assert result.status_code == 422
    assert service.calls == []


def test_api_health_returns_200_when_ready() -> None:
    """쓸 수 있는 세대가 있으면 상태 확인이 200과 세대 정보를 돌려줌."""

    client = TestClient(create_app(FakeService(answered_response())))

    result = client.get("/health")

    assert result.status_code == 200
    assert result.json() == {
        "ready": True,
        "generation": "gen-test-001",
        "chunk_count": 218,
        "loading": False,
        "last_error": None,
    }


def test_api_health_returns_503_when_not_ready() -> None:
    """세대를 올리는 중이거나 실패하면 상태 확인이 503을 돌려줌(배포 점검·롤백 신호)."""

    health = {
        "ready": False,
        "generation": None,
        "chunk_count": 0,
        "loading": True,
        "last_error": "signature_mismatch",
    }
    client = TestClient(create_app(FakeService(answered_response(), health)))

    result = client.get("/health")

    assert result.status_code == 503
    assert result.json()["loading"] is True


def test_api_lifespan_does_not_assemble_when_service_injected() -> None:
    """서비스를 주입하면 서버 시작 때 bootstrap을 부르지 않음(색인·모델 없이 시험 가능)."""

    service = FakeService(answered_response())
    with TestClient(create_app(service)) as client:
        assert client.get("/health").status_code == 200


def test_cli_prints_summary_and_returns_zero() -> None:
    """사람이 읽는 요약에 상태·답변·근거·확인 못 한 항목·시간·호출 수가 모두 나옴."""

    service = FakeService(answered_response())
    output, errors = io.StringIO(), io.StringIO()

    code = main(
        ["--query", "연회비", "--role", "auditor"],
        service=service,
        stdout=output,
        stderr=errors,
    )
    text = output.getvalue()

    assert code == 0
    assert "상태: answered" in text
    assert "연회비는 1만원임." in text
    assert "카드안내.pdf · p.12 · 테스트카드 · 조각 c-001" in text
    assert "vector=0.810 bm25=3.210 fused=0.740 rerank=0.910" in text
    assert "q2 해외 수수료 — 근거 0건" in text
    assert "S-R1 0.01s, S-R4 0.42s" in text
    assert "LLM 호출 수: 3" in text
    assert errors.getvalue() == ""


def test_cli_passes_role_and_options() -> None:
    """--role·--generate-answer·--top-k가 그대로 서비스에 전달됨."""

    service = FakeService(answered_response())
    main(
        ["--query", "연회비", "--role", "agent", "--generate-answer", "--top-k", "7"],
        service=service,
        stdout=io.StringIO(),
    )

    request, role = service.calls[0]
    assert role == "agent"
    assert (request.generate_answer, request.top_k) == (True, 7)


def test_cli_json_option_prints_raw_response() -> None:
    """--json은 응답 원본을 JSON으로 출력함."""

    service = FakeService(answered_response())
    output = io.StringIO()

    main(["--query", "연회비", "--role", "agent", "--json"], service=service, stdout=output)
    payload = json.loads(output.getvalue())

    assert payload["request_id"] == "req-0001"
    assert payload["evidence"][0]["chunk_id"] == "c-001"


def test_cli_returns_one_on_error_status() -> None:
    """응답 상태가 오류면 종료 코드 1을 돌려줌(셸에서 실패를 알 수 있게)."""

    service = FakeService(error_response("index_unavailable"))
    output = io.StringIO()

    code = main(["--query", "연회비", "--role", "agent"], service=service, stdout=output)

    assert code == 1
    assert "오류 코드: index_unavailable" in output.getvalue()


def test_cli_returns_two_on_missing_role() -> None:
    """--role이 없으면 서비스를 부르지 않고 종료 코드 2를 돌려줌."""

    service = FakeService(answered_response())
    errors = io.StringIO()

    code = main(["--query", "연회비"], service=service, stdout=io.StringIO(), stderr=errors)

    assert code == 2
    assert service.calls == []
    assert "인자 오류" in errors.getvalue()


def test_cli_returns_two_on_unknown_role() -> None:
    """정의되지 않은 역할은 CLI 단계에서 막음(권한 규칙이 소유한 역할 목록만 허용)."""

    service = FakeService(answered_response())

    code = main(
        ["--query", "연회비", "--role", "admin"],
        service=service,
        stdout=io.StringIO(),
        stderr=io.StringIO(),
    )

    assert code == 2
    assert service.calls == []


def test_api_responses_declare_utf8_charset() -> None:
    """Windows PowerShell 5.1이 한글을 깨지 않고 읽도록 /search·/health 응답이 charset=utf-8을 밝힘."""

    client = TestClient(create_app(FakeService(answered_response())))

    search = client.post("/search", json={"query": "연회비"}, headers={"X-User-Role": "agent"})
    health = client.get("/health")

    assert search.headers["content-type"] == "application/json; charset=utf-8"
    assert health.headers["content-type"] == "application/json; charset=utf-8"


def test_cli_shows_clause_number_as_stored() -> None:
    """색인의 clause_no는 '제5조'처럼 '조'를 이미 담고 있으므로 CLI가 '조'를 덧붙이지 않음(실행에서 '제11조조' 발견)."""

    response = answered_response()
    response.evidence[0].clause_no = "제5조"
    out = io.StringIO()
    main(["--query", "연회비", "--role", "agent"], service=FakeService(response), stdout=out, stderr=io.StringIO())
    assert "제5조" in out.getvalue() and "제5조조" not in out.getvalue()
