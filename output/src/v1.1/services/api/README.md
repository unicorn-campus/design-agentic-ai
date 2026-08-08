# 런치픽 API · 화면 진입점

## 적용 판정

| 항목 | 구현 | 근거 |
|------|------|------|
| 웹 프레임워크 | FastAPI REST + 자동 OpenAPI | D-03 추천값 |
| 부분 전송 | `StreamingResponse` 기반 SSE | D-03 추천값 · 추천 카드 점진 전송 |
| 화면 | React + TypeScript + Vite | D-04 · 원본 프로토타입 10개 화면 |
| 실제 외부 호출 | 미적용 | D-07에 따라 단위시험에서는 대역 사용 |

`DemoLunchPickService`는 화면·API 계약 검증용 결정론 구현체임. 실제 실행 시 동일 메서드 계약을 구현한
LangGraph 서비스로 교체해야 함.

## 최신 API 확인

2026-08-08 context7 공식 문서에서 아래 현재 사용법을 확인한 뒤 구현함.

- FastAPI: `APIRouter`, Pydantic `BaseModel` 입력 검증, 전역 예외 처리기, lifespan 사용
- SSE: `StreamingResponse`와 `text/event-stream`, `event:`·`data:` 프레임 사용
- Vite: `import.meta.env.VITE_*`, `tsc -b && vite build`, `@vitejs/plugin-react` 사용

## 실행

```powershell
cd output/src/v1.1/services
uv sync --extra dev
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000
```

- OpenAPI: `http://127.0.0.1:8000/docs`
- 상태 확인: `GET /health`
- 추천 REST: `POST /api/v1/recommendations`
- 추천 SSE: `POST /api/v1/recommendations/stream`

## 안전 경계

- 결제·해지에 `approved=true`와 길이 8자 이상의 `idempotency_key` 필수
- 입력 검증 실패 응답에 원문 입력값 미포함
- 이메일은 마스킹 응답만 제공
- API 오류는 `code`, `message`, `correlation_id`만 반환
- 브라우저가 API를 다른 출처로 직접 호출할 때만 `LUNCHPICK_CORS_ORIGINS`에 쉼표 구분 허용 출처를 설정

## 확인필요

`[확인필요]` 1건임.

| # | 항목 | 영향 |
|---|------|------|
| 1 | 실제 LangGraph 실행 서비스 주입 방식 | 데모 포트를 실제 추천 흐름으로 교체할 때 확정 필요 |
