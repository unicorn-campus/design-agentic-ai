# S2.3 문서 추출·정제 실습

`../docs/`의 합성 PDF·상담 TXT를 읽어 본문과 메타데이터를 가진 문서로 변환하는 강사 제공 프로그램임.  
교육생은 프로그램 실행, 원문 대조, 상담 분리 확인, 메타데이터 수정·검증을 수행함.  
프로그램은 완성본으로 제공하며 교육생용 빈칸이나 `_ref.py` 파일을 두지 않음.

## (1) 디렉토리 구조

```text
hybrid-ai-lab/
├── docs/                         # 입력 원문 PDF 2개·상담 TXT 6개
│   ├── D1_개인회원표준약관_합성.pdf
│   ├── D2_카드혜택안내_합성.pdf
│   ├── D3_S01_신규가입_상담이력_합성.txt
│   ├── ...                       # S02 ~ S06 상담 원문
│   └── _instructor/              # 정답·검증 자료: 추출 대상에서 제외
├── rdb/                          # PostgreSQL 실습 구성
└── s2.3/
    ├── README.md
    ├── parse_docs.py             # 실행 진입점
    ├── requirements.txt
    ├── config/
    │   ├── document_profiles.json
    │   └── metadata_schema.json
    ├── docprep/
    │   ├── presentation/cli.py
    │   ├── application/
    │   │   ├── pipeline.py
    │   │   └── ports.py
    │   ├── domain/
    │   │   ├── consultations.py
    │   │   └── validation.py
    │   └── infrastructure/
    │       ├── pdf_reader.py
    │       └── file_store.py
    ├── tests/
    └── data/parsed/              # 실행 후 생성되는 결과
        ├── D1_개인회원표준약관_합성.md
        ├── D2_카드혜택안내_합성.md
        ├── pages/               # PDF 페이지별 Markdown
        ├── records/             # 상담 1건당 Markdown 1개
        ├── documents.jsonl
        ├── manifest.json
        ├── report.csv           # --report 사용 시
        ├── report.json          # 상세 보고·확인 사항
        └── validation.json      # --validate 사용 시
```

## (2) 프로그램 설명과 계층 구조

명령 해석 → 작업 조정 → 업무 규칙·파일 처리 순서로 책임을 나눈 Layered Architecture임.  
업무 규칙을 담은 domain 계층과 PDF·파일 처리를 담은 infrastructure 계층을 분리함.

| 파일 | 계층·역할 |
|---|---|
| `parse_docs.py` | 명령 실행 진입점 |
| `docprep/presentation/cli.py` | 옵션 해석, 경로 결정, 실행 결과 안내 |
| `docprep/application/pipeline.py` | 입력 선택부터 추출·정제·검증·저장까지 작업 조정 |
| `docprep/application/ports.py` | PDF 읽기·결과 저장의 인터페이스 정의 |
| `docprep/domain/consultations.py` | 상담 경계 분리와 식별정보 정제 규칙 |
| `docprep/domain/validation.py` | 메타데이터의 필수 값·자료형·허용 값 검증 |
| `docprep/infrastructure/pdf_reader.py` | PyMuPDF를 이용한 PDF 본문 추출과 여백 처리 |
| `docprep/infrastructure/file_store.py` | Markdown·JSONL·보고서 파일 읽기와 저장 |
| `config/document_profiles.json` | 문서 종류별 기본 메타데이터 설정 |
| `config/metadata_schema.json` | 필수 키·자료형·허용 값 등 검증 기준 |
| `tests/` | 추출·정제·검증 동작을 확인하는 자동 테스트 |

외부 AI API, API Key, PostgreSQL 연결 없이 로컬 파일만으로 실행 가능함.  
원문의 회원번호가 이미 `member.member_id`이므로 `private.member_id_map` 조회가 필요하지 않음.

## (3) 가상환경 설정

Python 3.10 이상이 필요함. 아래 명령은 저장소의 `hybrid-ai-lab/s2.3`로 이동한 뒤 실행함.  
설치 패키지는 `requirements.txt`의 PyMuPDF·PyYAML이며 설치 시 인터넷 연결이 필요함.

### Windows PowerShell

```powershell
cd C:\Users\hiond\class\design-agentic-ai\hybrid-ai-lab\s2.3
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

가상환경 활성화가 실행 정책으로 차단되면 활성화 없이 다음 명령으로 설치·실행 가능함.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe parse_docs.py --report --split-by header --pseudonymize --validate
```

### Windows 명령 프롬프트(cmd)

```bat
cd /d C:\Users\hiond\class\design-agentic-ai\hybrid-ai-lab\s2.3
py -3 -m venv .venv
.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
```

### Windows Git Bash

```bash
cd /c/Users/hiond/class/design-agentic-ai/hybrid-ai-lab/s2.3
py -3 -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements.txt
```

### macOS·Linux Bash 또는 Zsh

```bash
cd ~/class/design-agentic-ai/hybrid-ai-lab/s2.3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

저장소를 다른 곳에 복제한 경우 첫 번째 `cd` 경로만 실제 위치로 변경함.  
실습 종료 시 활성화한 가상환경은 `deactivate`로 해제함.

## (4) 실행 방법

### 전체 추출·정제·검증

현재 위치가 `s2.3`인 경우 아래 명령을 사용함.

```bash
python parse_docs.py --report --split-by header --pseudonymize --validate
```

`--in`, `--out` 생략 시 스크립트 위치를 기준으로 `../docs/`, `data/parsed/`를 사용함.  
경로를 직접 입력한 경우 해당 상대 경로는 터미널의 현재 위치를 기준으로 해석함.

현재 위치가 `hybrid-ai-lab`인 경우 실행 파일과 출력 경로를 아래처럼 지정함.  
먼저 `s2.3`에서 만든 가상환경을 활성화한 상태를 전제로 함.

```bash
python s2.3/parse_docs.py --in docs --out s2.3/data/parsed --report --split-by header --pseudonymize --validate
```

### 조별 상담 파일 선택

다음 명령은 PDF 2개와 1조 상담 파일을 함께 처리함. `--segment` 값은 1 ~ 6 중 선택함.

```bash
python parse_docs.py --segment 1 --report --split-by header --pseudonymize --validate
```

| 조 | 세그먼트 | 상담 건수 |
|---|---|---|
| 1 | 신규가입 | 2명·8건 |
| 2 | 장기보유 | 2명·8건 |
| 3 | VIP | 2명·8건 |
| 4 | 휴면직전 | 2명·8건 |
| 5 | 다중카드 | 2명·8건 |
| 6 | 연회비부담 | 2명·8건 |

### 추출·분리 방식 비교

다음 명령은 모두 `s2.3` 위치 기준이며 결과를 별도 폴더에 저장함.

```bash
python parse_docs.py --out data/with_margins --keep-margins --report --pseudonymize
python parse_docs.py --out data/raw_pii --report --split-by header
python parse_docs.py --out data/split_rule --report --split-by rule --pseudonymize
python parse_docs.py --out data/split_date --report --split-by date --pseudonymize
```

`--keep-margins`는 PDF 머리말·꼬리말을 포함하여 정제 전후를 비교하는 옵션임.  
`--pseudonymize`를 생략한 `data/raw_pii`에는 합성 식별정보가 남으므로 정제 비교 실습에만 사용함.  
상담 분리는 `[상담ID]` 헤더를 기준으로 하는 `header`가 기본 실습 방식임.  
`date`는 본문 날짜로 상담이 잘리는 오류를 안내하고 중단하는 비교 옵션임.  
`rule`은 구분선으로 상담 1건을 식별할 수 있는지 검사하며 빈 조각·병합을 발견하면 중단함.  
오류 메시지를 기록하고 `header`로 다시 실행한 뒤 원문과 대조함.

### 메타데이터 수정 후 재검사

`data/parsed/pages/` 또는 `records/`의 Markdown 상단 YAML 영역을 수정한 뒤 아래 명령을 실행함.

```bash
python parse_docs.py --validate-only --in data/parsed
```

`--validate-only`는 원문을 다시 추출하지 않고 저장된 결과의 메타데이터를 검사하여 터미널에 출력함.  
`--validate`는 추출 실행에 검증을 함께 붙이는 옵션임. 두 옵션의 용도를 구분함.

조별로 검증 기준을 바꾸려면 스키마 사본을 만든 뒤 필수 키나 허용 값을 수정하여 지정함.

```bash
python parse_docs.py --validate-only --in data/parsed --schema config/metadata_schema.json
```

문서 종류별 기본 값을 변경할 때는 `config/document_profiles.json`을 수정하거나 사본을 지정함.

```bash
python parse_docs.py --metadata config/document_profiles.json --report --pseudonymize --validate
```

기본 값을 바꿔 다시 추출하면 새 결과에 반영되므로 교육생의 수동 수정 결과는 별도 폴더에 보관함.

## (5) 교재 기능과 결과 확인

| 교재 활동 | 프로그램 기능 | 확인할 결과 |
|---|---|---|
| 활동 1: PDF 추출 | 문자 PDF 추출, 상하단 여백 처리, 페이지 출처 보존 | PDF 원문과 `pages/` 본문 대조 |
| 활동 1: 추출 결과표 | `--report` | `report.csv`의 쪽수·글자 수·제거 줄 수 |
| 활동 2: 상담 분리 | `--split-by header` | `records/`의 상담별 파일, 파일별 8건 |
| 활동 2: 분리 오류 비교 | `--split-by rule` 또는 `date` | 경계 오류 메시지와 `header` 결과 대조 |
| 활동 2: 식별정보 처리 | `--pseudonymize` | 삭제·가명화·나이대 변환 결과 |
| 활동 3: 메타데이터 부착 | 문서 프로필의 기본 값 적용 | Markdown YAML과 JSONL metadata |
| 활동 3: 스키마 수정·검증 | `--schema`, `--validate-only` | 터미널의 오류 위치·이유 |
| 활동 4: 데이터 소스 판정 | 원문 출처와 문서 종류 보존 | 워크시트에 정형·비정형 판정 근거 작성 |

활동 4의 업무 판단과 온라인 워크시트 작성은 교육생이 수행함.  
본 프로그램의 결과는 청킹 전 자료이며 임베딩·벡터 DB 적재·검색은 후속 실습에서 수행함.

### 식별정보 정제 규칙

| 원문 항목 | 정제 결과 |
|---|---|
| 고객 이름 | 삭제 |
| 전화·이메일 | 삭제 |
| 카드번호·끝 4자리 | 전체·부분 번호 삭제 |
| `M-1042` 형식 회원번호 | `m_` 접두사가 있는 가명 ID로 변환 |
| 상담사 이름 | `a_` 접두사가 있는 직원 가명 ID로 변환 |
| 정확한 나이·생년월일 | 나이대 표현으로 모호화 |

가명 ID는 입력 문자열의 UTF-8 SHA-256 결과 중 앞 16자리 16진수에 접두사를 붙이는 실습 규칙임.  
변환 전에 입력 문자열 앞뒤 공백을 제거함.  
정형·문서·그래프를 연결할 때도 같은 입력과 함수를 사용해야 동일 고객으로 연결 가능함.  
교재의 짧은 `m_7f3a9c` 표기는 형태 예시이며 실제 변환 결과가 아님.  
식별정보를 정제한 상담도 공개 등급 `restricted`를 유지함.

### 결과 규모와 형식

현재 원문 기준 기대 규모는 D1 15쪽·52개 조문, D2 196쪽, D3 6파일·48건임.  
PDF 페이지마다 본문이 있는 경우 `documents.jsonl`은 211개 페이지와 48개 상담, 총 259개 문서임.  
`--segment`를 사용하면 상담이 8건으로 줄어들며 PDF 페이지 수는 동일함.  
원문 변경 시 보고서와 실제 결과로 기대 규모를 다시 확인함.

`documents.jsonl`의 한 줄은 아래 구조의 JSON 객체임.

```json
{"page_content": "추출·정제된 본문", "metadata": {"source": "원문 파일명", "page": 1}}
```

위 예시는 구조 설명용이며 실제 결과에는 문서 종류·버전·공개 등급 등의 메타데이터도 포함됨.  
PDF의 `created_at`은 내장 생성일 `2026-09-09`이며 시행일 `effective_date`의 `2027-01-15`와 구분함.  
D2의 테두리 없는 표는 같은 행의 셀을 `|`로 연결하며 여러 줄인 혜택 조건은 다음 줄에 보존함.  
PDF 합본 Markdown은 사람이 읽는 확인용이며 JSONL에 합본을 추가하여 페이지 문서와 중복 적재하지 않음.  
상담은 한 건 안에서만 후속 청킹하며 서로 다른 상담이나 고객 사이에 중첩을 만들지 않음.

## (6) 테스트와 한계

2026-09-10 제공 원문 8파일로 전체 실행하여 259개 문서·48개 상담 생성과 검증 오류 0건을 확인함.  
저장된 Markdown의 `--validate-only` 재검사도 257건·오류 0건이며 자동 테스트 15개 통과를 확인함.  
실행 전후 원문 8파일의 SHA-256이 동일하여 원문 보존을 확인함.

현재 위치 `s2.3`, 가상환경 활성화 상태에서 아래 명령으로 자동 테스트 실행 가능함.

```bash
python -m unittest discover -s tests -v
```

자동 검사 통과는 원문의 모든 의미가 보존되었다는 뜻이 아님.  
표의 행·열 대응, 연회비 브랜드, 혜택 제외 조건, 날짜, 상담 경계는 원문을 함께 열어 확인함.  
OCR을 수행하지 않으므로 스캔 이미지 PDF의 글자를 읽을 수 없으며 현재 제공된 문자 PDF를 대상으로 함.  
정제 규칙은 제공된 합성 상담 형식에 맞춘 실습 규칙이며 새로운 이름·번호 표현에는 규칙 보완이 필요함.  
허용 값 검사는 공개 등급·유효일을 업무적으로 결정하는 절차를 대신하지 않음.  
원문 PDF·TXT는 수정하지 않으며 안내 파일과 `_instructor/`는 입력에서 제외함.
