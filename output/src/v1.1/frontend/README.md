# 런치픽 React 프로토타입

원본 `docs/plan/design/uiux/prototype`의 공통 디자인 토큰과 10개 화면 구조를 React + TypeScript로 이전함.
현재 워크스페이스에서 원본은
`C:\Users\hiond\workspace\lunch-aws-actions\docs\plan\design\uiux\prototype`에 있음.

## 화면

| 해시 경로 | 화면 | 주요 상호작용 |
|-----------|------|---------------|
| `#login` | 로그인 | 카카오 시작 버튼 |
| `#quiz` | 취향 퀴즈 | 좋아요·싫어요·건너뛰기 |
| `#location` | 위치 동의 | 허용·나중에 결정 |
| `#dietary` | 식이제한 | 민감정보 동의·알레르기·식이 유형 |
| `#home` | 추천 홈 | 추천 조회·상세·거절·수락 |
| `#navigation` | 길찾기 | 지도 딥링크 안내·식사 기록 이동 |
| `#meal` | 식사 기록 | 기록·30초 취소 안내·피드백 |
| `#insights` | 이력·인사이트 | 탭 전환·구독 이동 |
| `#profile` | 프로필 | 닉네임·알림·위치·구독 설정 |
| `#subscription` | 구독 | 결제 승인·해지 예약 승인 |

## 실행·시험

```powershell
cd output/src/v1.1/frontend
pnpm install
pnpm test
pnpm build
pnpm dev
```

API 기본 주소는 같은 출처의 `/api`임. 별도 주소가 필요하면 `.env.local`에
`VITE_API_BASE_URL=http://127.0.0.1:8000`을 설정함. API가 꺼져 있으면 추천 홈은 원본 프로토타입과
동일한 데모 데이터로 안전하게 대체됨.

## 판정

- 원본의 모바일 최대 너비 480px, 색상·간격 토큰, 카드·버튼·하단 내비게이션 유지
- 브라우저 저장소에 카드번호·CVC 저장 금지
- 결제·해지는 최종 승인 버튼을 별도로 제공
- 외부 지도는 프로토타입에서 실제 딥링크 제공자가 미확정이라 안내만 제공

## 확인필요

`[확인필요]` 1건임.

| # | 항목 | 영향 |
|---|------|------|
| 1 | 지도 딥링크 제공자·URI 규격 | 카카오맵·네이버지도 실제 앱 열기 연결 보류 |
