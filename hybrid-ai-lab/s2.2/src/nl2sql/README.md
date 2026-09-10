# W2 · S2.2 정형 데이터 직접 연결 실습

공통 PostgreSQL RDB의 6개 고객 세그먼트를 조회하고, 조회 결과로 Context를 만들어 Claude에 전달하는 실습임.

## 1. 교육생 작성 범위

교육생이 채울 파일은 세 파일임. 같은 이름의 `_ref.py`는 해당 파일의 정답임.  
그 외 환경 설정·PostgreSQL 연결·API 연결·실행 코드는 완성 제공됨.

| 교육생 파일 | 작성할 내용 | 정답 파일 |
|-------------|------------|-----------|
| `04_query_usage.py` | 월별 사용액 SQL의 빈칸 5개 | `04_query_usage_ref.py` |
| `04_query_delinquency.py` | 최신 연체 조회 SQL의 빈칸 2개 | `04_query_delinquency_ref.py` |
| `context_builder.py` | 제공된 함수 시그니처·고객 기본 블록에 이어 Context 본문 작성 | `context_builder_ref.py` |

기본 실행은 교육생 파일을 사용함. 빈칸이 남으면 작성 위치를 안내하며 정답으로 자동 대체하지 않음.  
강사용 `--reference` 옵션을 명시하면 세 정답 파일을 연결함. 정답을 교육생 파일에 덮어쓸 필요는 없음.

## 2. 디렉토리 구조

실습 관련 파일만 표시함. 모든 실행 명령은 `design-agentic-ai/hybrid-ai-lab/s2.2/` 기준임.

```text
design-agentic-ai/hybrid-ai-lab/s2.2/
├─ README.md                          # 주차별 안내 링크
├─ docs/S2.2-data.md                   # 테이블·컬럼·예외 사례 설명
├─ src/
│  ├─ common/                         # 완성 제공, 교육생 수정 불필요
│  │  ├─ config.py                    # .env·PostgreSQL 접속 설정
│  │  ├─ llm_client.py                # Claude 호출
│  │  ├─ database.py                  # 읽기 전용 연결·조회 지원
│  └─ nl2sql/
│     ├─ README.md                    # 이 문서
│     ├─ _bootstrap.py                # 직접 실행 시 모듈 경로 설정
│     ├─ presentation.py              # CLI·구성 요소 연결·출력
│     ├─ 01_first_call.py             # 완성 예제
│     ├─ 02_explore_schema.py         # 완성 예제
│     ├─ 03_nl2sql_demo.py            # 완성 예제
│     ├─ 04_query_products.py         # 완성 예제
│     ├─ 04_query_usage.py            # 교육생 작성
│     ├─ 04_query_usage_ref.py        # 정답
│     ├─ 04_query_delinquency.py      # 교육생 작성
│     ├─ 04_query_delinquency_ref.py  # 정답
│     ├─ context_builder.py          # 교육생 작성
│     ├─ context_builder_ref.py      # 정답
│     ├─ 05_ask_with_context.py       # 완성된 통합 실행 예제
│     ├─ application/
│     │  └─ customer_service.py      # 고객 검증·조회·조립 순서
│     └─ prompts/
│        └─ 05_ask_with_context.md   # 8개 섹션 시스템 프롬프트
├─ .env                              # 각자 설정, Git 제외
└─ requirements.txt
```

책임을 나누는 Layered Architecture 적용임.  
`presentation.py`가 입력·출력을, `application/customer_service.py`가 조회·조립 순서를 담당함.  
교육생 SQL 파일은 조회 조건을, `context_builder.py`는 조회 결과의 문장 조립을 담당함.  
DB 연결·Claude 연동은 `src/common/`에서 제공함. 스키마와 데이터는 공통 `../rdb/`에서 관리함.

## 3. 프로그램 설명표

아래 파일 경로는 `src/nl2sql/` 기준임. API 호출도 `--offline` 사용 시 요청 내용만 확인 가능함.

| 프로그램 | 제공 상태 | 역할·정상 결과 | API 호출 |
|----------|-----------|----------------|----------|
| `01_first_call.py` | 완성 | 첫 Claude 응답·종료 이유·토큰 수 확인 | 있음 |
| `02_explore_schema.py` | 완성 | DB 준비 후 테이블별 컬럼·건수 확인 | 없음 |
| `03_nl2sql_demo.py` | 완성 | 자연어로 SELECT 초안 생성·표시, 자동 실행 없음 | 있음 |
| `04_query_products.py` | 완성 | 활성 카드의 상품명·연회비·발급일·상태 조회 | 없음 |
| `04_query_usage.py` | SQL 5칸 작성 | 최근 6개월 승인 사용액 조회 | 없음 |
| `04_query_usage_ref.py` | 정답 | 월별 사용액 조회의 정답 실행 | 없음 |
| `04_query_delinquency.py` | SQL 2칸 작성 | 기준월 이하 최신 연체 1행 또는 null 조회 | 없음 |
| `04_query_delinquency_ref.py` | 정답 | 최신 연체 조회의 정답 실행 | 없음 |
| `context_builder.py` | 본문 작성 | 단위·출처·미확인 항목을 포함한 Context 조립 | 없음 |
| `context_builder_ref.py` | 정답 | Context 조립의 정답 실행 | 없음 |
| `05_ask_with_context.py` | 완성 | 세 교육생 파일을 연결하여 5요소 응답 생성 | 있음 |

05번 응답의 5요소는 결론·근거·출처·예측값·주의사항임.  
거래가 없는 달의 0원 보충은 제공 코드에서 처리하며, 교육생은 SQL의 지정 빈칸만 작성함.

## 4. 가상환경 설정 · OS와 셸별

Python 3.11 이상 사용 권장임. `.venv`는 OS별로 새로 생성하며 Windows와 Linux 사이에 공유하지 않음.  
터미널을 새로 열 때마다 저장소 루트로 이동한 뒤 활성화 명령 재실행이 필요함.

### Windows · PowerShell

```powershell
cd "$HOME/class/design-agentic-ai/hybrid-ai-lab/s2.2"
python --version
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

PowerShell 정책으로 활성화가 차단되면 활성화 없이 가상환경 Python 직접 사용 가능함.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe src/nl2sql/02_explore_schema.py
```

### Windows · CMD

```bat
cd /d "%USERPROFILE%\class\design-agentic-ai\hybrid-ai-lab\s2.2"
python --version
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

### Windows · Git Bash

```bash
cd ~/class/design-agentic-ai/hybrid-ai-lab/s2.2
python --version
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

### macOS·Linux·WSL · Bash 또는 Zsh

```bash
cd ~/class/design-agentic-ai/hybrid-ai-lab/s2.2
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

WSL에서는 WSL 홈에 둔 저장소와 Linux 가상환경 사용 기준임.  
Linux에서 venv 모듈 누락 오류가 나면 해당 배포판의 Python venv 패키지 설치 필요함.

### macOS·Linux · Fish

```fish
cd ~/class/design-agentic-ai/hybrid-ai-lab/s2.2
python3 -m venv .venv
source .venv/bin/activate.fish
python -m pip install -r requirements.txt
```

### 환경 확인과 종료

활성화 후 아래 출력 경로에 저장소의 `.venv`가 포함되면 선택된 Python 확인 완료임.

```text
python -c "import sys; print(sys.executable)"
python -m pip --version
```

가상환경 종료 명령은 위 셸 모두 `deactivate`임.

## 5. PostgreSQL과 API 키 설정

저장소 루트에 `.env`가 없을 때만 `.env.example`을 복사하여 `.env` 생성함.  
기존 `.env`가 있으면 파일을 유지하고 필요한 값만 편집함.

```dotenv
CLAUDE_API_KEY=발급받은_API_키
S22_DB_DSN=host=localhost port=5432 dbname=cardlab user=lab_user
S22_DB_PASSWORD=공통_RDB_실습계정_비밀번호
```

`S22_DB_DSN`을 생략하면 `localhost:5432`의 `cardlab` DB와 읽기 전용 `lab_user`를 사용함.  
`S22_DB_PASSWORD`를 생략하면 로컬 `../rdb/compose.yml`의 실습용 설정을 읽음.  
운영 환경에서는 `S22_DB_DSN`과 `S22_DB_PASSWORD`를 비밀값 저장소에서 주입해야 함.  
모델은 코드에서 `claude-sonnet-5`로 고정됨. API 키는 Claude 호출에만 필요함.

## 6. 실행 방법

아래 명령은 가상환경 활성화 후 모든 OS·셸에서 동일하게 사용 가능함.  
VS Code에서 파일이 있는 `src/nl2sql/`가 아닌 저장소 루트 터미널에서 실행함.

### 6.1 데이터 준비와 완성 예제 확인

먼저 프로젝트 루트에서 공통 RDB를 기동함.

```text
docker compose -f ../rdb/compose.yml up -d
docker compose -f ../rdb/compose.yml ps
```

```text
python src/nl2sql/02_explore_schema.py
python src/nl2sql/04_query_products.py --segment 2
python src/nl2sql/01_first_call.py
python src/nl2sql/03_nl2sql_demo.py
```

02번·04번 상품 조회는 API 키 없이 실행 가능함. 01번·03번은 Claude 호출을 포함함.  
프로그램은 공통 RDB의 `public` 스키마를 `lab_user`로 읽기만 함. 데이터 생성·변경은 수행하지 않음.  
기준 데이터는 고객 600명, 카드 1,200건, 상품 64건, 상품·브랜드 연회비 133건임.  
전체 테이블과 최신 건수는 [공통 RDB 안내](../../../rdb/README.md)에서 확인 가능함.

### 6.2 교육생 코드 작성과 확인

먼저 `04_query_usage.py`의 SQL 5칸, `04_query_delinquency.py`의 SQL 2칸을 작성한 뒤 각각 실행함.

```text
python src/nl2sql/04_query_usage.py --segment 2
python src/nl2sql/04_query_delinquency.py --segment 2
```

다음으로 `context_builder.py`의 함수 본문을 작성한 뒤 Context와 통합 입력을 확인함.

```text
python src/nl2sql/context_builder.py --segment 2
python src/nl2sql/05_ask_with_context.py --segment 2 --offline
```

미완성 안내가 나오면 표시된 파일의 빈칸을 채운 후 다시 실행함.  
`--offline`은 API 호출만 생략하는 옵션이며, 교육생 코드 작성은 필요함.  
Context의 금액·단위·출처·확인 필요 항목을 점검한 뒤 실제 API를 호출함.

```text
python src/nl2sql/05_ask_with_context.py --segment 2
```

정상 종료 응답의 `stop_reason`은 `end_turn`임. `max_tokens`는 출력 상한으로 중단된 상태임.

### 6.3 강사용 정답 실행

교육생 파일이 미완성이어도 아래 명령으로 정답 결과 확인 가능함.  
04번 정답 파일의 직접 실행은 해당 조회의 정답을 사용함. Context 정답 실행은 정답 조회와 조립을 사용함.

```text
python src/nl2sql/04_query_usage_ref.py --segment 2
python src/nl2sql/04_query_delinquency_ref.py --segment 2
python src/nl2sql/context_builder_ref.py --segment 2
python src/nl2sql/05_ask_with_context.py --reference --offline --segment 2
python src/nl2sql/05_ask_with_context.py --reference --segment 2
```

일반 파일에 `--reference`를 지정하여 같은 정답 조회를 실행하는 방법도 지원함.

```text
python src/nl2sql/04_query_usage.py --reference --segment 2
python src/nl2sql/04_query_delinquency.py --reference --segment 2
```

### 6.4 조별 고객과 질문 변경

| 조 | 세그먼트 | 대표 고객 |
|----|----------|-----------|
| 1 | 신규 가입 | M-1001 |
| 2 | 장기 보유 | M-1042 |
| 3 | VIP | M-3001 |
| 4 | 휴면 직전 | M-4001 |
| 5 | 다중 카드 | M-5001 |
| 6 | 연회비 부담 | M-6001 |

각 세그먼트에 고객 100명씩 포함됨. 세그먼트는 실습 시나리오의 지정값이며 예측 모델의 분류 결과는 아님.

```text
python src/nl2sql/05_ask_with_context.py --segment 6 --question "보유 상품과 연회비를 요약해 주세요"
python src/nl2sql/04_query_usage.py --member-id M-1042 --base-date 2026-08-31
python src/nl2sql/context_builder_ref.py --member-id M-3100
python src/nl2sql/05_ask_with_context.py --help
```

위 교육생 실행 명령은 세 파일 작성 후 사용함. 정답으로 확인할 경우 `--reference` 추가 가능함.  
`--segment` 기본값은 2이며, `--member-id`를 함께 지정하면 고객 ID가 우선됨.  
기준일 기본값은 `2026-08-31`, 지원 범위는 `2026-03-01` ~ `2026-08-31`임.  
`--question`은 01번·05번에서 사용함. 03번은 지정된 SQL 생성 질문으로 실행됨.  
M-1042의 3월 ~ 8월 사용액은 1,574,000 / 1,495,000 / 1,416,000 / 1,338,000 /  
1,259,000 / 1,180,000원임.  
M-3100의 연체 자료는 누락 사례이며, Context에 `확인 필요` 표시가 정상임.

### 6.5 연결 검증

`02_explore_schema.py`에서 8개 `public` 테이블과 행 수가 출력되면 연결·권한·스키마 확인 완료임.  
`05_ask_with_context.py --reference --offline`에서 상품·사용액·연체 Context가 출력되면 통합 조회 확인 완료임.  
macOS·Linux·기타 셸의 환경 설정 명령은 해당 OS에서 별도 확인 필요함.

## 7. 관련 자료

- [데이터 설명서](../../docs/S2.2-data.md): 컬럼 기준·데이터 의미·조회 범위 설명
- [공통 RDB 안내](../../../rdb/README.md): PostgreSQL 기동·계정·전체 테이블 설명
- [05번 프롬프트](prompts/05_ask_with_context.md): 8개 섹션 시스템 프롬프트
- [프롬프트 작성 가이드](../../../../references/prompt-guide.md): 섹션 명칭·작성 규칙

05번 프롬프트는 `[목표]`·`[역할]`·`[맥락]`·`[입력]`·`[처리]`·`[출력]`·`[제약조건]`·`[예시]` 순서임.  
질문과 조회 결과는 별도 입력으로 전달되며, API 키는 프롬프트에 포함하지 않음.
