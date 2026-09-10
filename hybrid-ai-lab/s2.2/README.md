# hybrid-ai-lab 실습 교재

실습 실행 위치는 `design-agentic-ai/hybrid-ai-lab/s2.2/`임.  
실습 루트의 `.env`가 없으면 상위 `hybrid-ai-lab/.env`를 읽으므로 기존 API 키 설정 재사용 가능함.  
가상환경 생성·의존성 설치·PostgreSQL 기동 방법은 주차별 README 참조함.

```powershell
cd C:/Users/hiond/class/design-agentic-ai/hybrid-ai-lab/s2.2
python src/nl2sql/05_ask_with_context.py --reference --offline
```

주차별 디렉토리의 README에서 구조·프로그램 설명·OS와 셸별 가상환경 설정·실행 방법 확인 가능함.

| 주차 | 제공 범위 | 실습 안내 |
|------|-----------|-----------|
| W2 | S2.2 정형 데이터 조회·Context 조립·Claude 응답 | [W2 README](src/nl2sql/README.md) |

교육생 작성 파일과 해당 정답 `_ref.py`를 구분하여 제공함. 상세 작성 범위와 실행 순서는 주차별 안내 참조함.
