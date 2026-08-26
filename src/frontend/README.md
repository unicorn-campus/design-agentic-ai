# Help Desk 프론트엔드

`POST /v1/inquiries`의 SSE(Server-Sent Events) 최종 응답을 표시하는 Vue.js 화면임.

## 실행

```bash
pnpm install
pnpm dev
```

API 주소가 다른 경우 `.env.local`에 아래 값을 지정함.

```text
VITE_HELP_DESK_API_BASE_URL=http://localhost:${HELP_DESK_HTTP_PORT}
```

## 시험과 빌드

```bash
pnpm test
pnpm build
```

## 화면 요소

화면 구조의 단일 근거는 `PROTOTYPE.md`임. 문의 입력, 채널 선택, 처리 상태, 근거 답변,
상담사 인계와 오류 상태만 포함함.

## 안 만든 것

- 관리자 화면: 설계서 ③에 없음
- 통계 화면: 설계서 ③에 없음
- 문의 목록 화면: 설계서 ③에 없음
