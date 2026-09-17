# Vector Indexer

PDF 약관·혜택 문서와 상담 텍스트를 추출·가명화·청킹한 뒤  
ChromaDB에 적재하는 로컬 앱임.
LangGraph 8개 노드와 SQLite 체크포인트를 사용함.

## 처리 흐름

```text
원문 선택 → 추출(상담 분리·가명화) → 프로필 적용 → 메타데이터 검증
          → 청킹 → 임베딩 → ChromaDB 적재 → 건수 검증
```

상담 문서는 추출 중 항상 가명화·검증됨. 가명화 전 본문은 그래프 상태·출력 파일·로그에 저장하지 않음.

## 실행 전제

- Python 3.12 권장
- 원문 8건을 `hybrid-ai-lab/docs/`에 배치
- 기본 임베딩 모델 `nlpai-lab/KURE-v2`
- 기본 컬렉션 `card_docs`, 거리 함수 `cosine`
- 실모델 최초 실행 시 KURE-v2 다운로드와 충분한 디스크 공간 필요
- 현재 구현의 임베딩 장치가 CPU로 고정되어 있으므로 GPU 자동 사용 없음

기본 원문 구성은 PDF 2건과 상담 텍스트 6건임.

```text
hybrid-ai-lab/docs/
├── D1_개인회원표준약관_합성.pdf
├── D2_카드혜택안내_합성.pdf
└── D3_S01_...txt ~ D3_S06_...txt
```

## 설치

프로젝트 루트에서 다음 명령 실행을 권장함.

```bash
cd hybrid-ai-lab/vector/indexer
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Linux CPU 환경에서 PyTorch 설치본을 찾지 못하면  
PyTorch CPU 인덱스를 먼저 지정해야 할 수 있음.

```bash
python -m pip install torch==2.14.0 \
  --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

설정 파일이 필요한 경우 예시 파일을 복사함. 값이 비어 있으면 코드 기본값 사용됨.

```bash
cp .env.example .env
```

상대 경로 설정값은 현재 셸 위치가 아니라 `vector/indexer/` 기준으로 해석됨.

## 빠른 확인

### Dry-run

추출·가명화·검증·청킹까지만 실행함. 임베딩 호출과 벡터 적재는 수행하지 않음.

```bash
python run_indexer.py \
  --in ../../docs \
  --out data \
  --doc all \
  --dry-run
```

정상 결과의 `status`는 `dry_run`, `exit_code`는 `0`임.

### Smoke 적재

모델 다운로드 없이 384차원 해시 임베딩과 `data/chroma_smoke/`를 사용함.

```bash
python run_indexer.py \
  --in ../../docs \
  --out data \
  --doc all \
  --embedding-backend smoke \
  --full-reindex
```

Smoke 컬렉션은 시험 전용임.  
KURE-v2 서명이 필요한 Retriever의 실제 검색 인덱스로 사용할 수 없음.

## 실모델 적재

현재 컬렉션을 비우고 KURE-v2로 전체 청크를 다시 적재하는 명령임.

```bash
python run_indexer.py \
  --in ../../docs \
  --out data \
  --doc all \
  --embedding-backend sentence-transformers \
  --full-reindex
```

`--full-reindex`는 컬렉션을 먼저 초기화함.  
처리 도중 실패하면 이전 컬렉션을 자동 복구하지 않으므로  
운영 데이터에 적용하기 전 별도 백업 필요함.

2026-09-13 실측은 원천 8건, 문서 259건, 청크 485건, KURE-v1 1,024차원임.
전체 적재 시간은 254,793ms였으며 하드웨어·캐시 상태에 따라 달라질 수 있음.

## 증분 적재

`index_manifest.json`의 본문·메타데이터 SHA-256과 현재 청크를 비교함.
같은 청크는 건너뛰고 변경된 청크만 임베딩·upsert함.

```bash
python run_indexer.py \
  --in ../../docs \
  --out data \
  --doc all \
  --embedding-backend sentence-transformers
```

변경이 없었던 실측 결과는 신규 임베딩 0건, 해시 건너뜀 485건, 컬렉션 485건임.
해당 실행 시간은 17,902ms임.

임베딩 서명이나 청킹 파라미터가 달라지면 증분 계획이 자동으로 전량 적재로 승격됨.

## 중단 후 재개

체크포인트 파일은 `data/checkpoints/indexer.sqlite`임.
중단된 실행과 같은 `--thread-id`를 넘기면 저장된 상태에서 재개함.

```bash
python run_indexer.py \
  --in ../../docs \
  --out data \
  --doc all \
  --thread-id idx-training-001
```

새 작업은 `--thread-id`를 생략해 자동 ID를 만들거나 새 값을 사용해야 함.
완료된 작업의 ID를 재사용하면 새 입력이 아니라 저장된 완료 상태를 읽을 수 있음.

## 문서 선택 옵션

| 옵션 | 값 | 의미 |
|---|---|---|
| `--doc` | `D1`, `D2`, `D3`, `all` | 처리할 문서 그룹 선택 |
| `--segment` | `1` ~ `6` | D3 상담 파일 번호 선택 |
| `--embedding-backend` | `sentence-transformers`, `smoke` | 임베딩 구현 선택 |
| `--dry-run` | 플래그 | 청킹 후 종료 |
| `--full-reindex` | 플래그 | 컬렉션 초기화 후 전량 적재 |
| `--thread-id` | 문자열 | 체크포인트 세션 키 |

전체 옵션 확인 명령은 다음과 같음.

```bash
python run_indexer.py --help
```

## 출력 파일

`--out data` 기준 주요 출력임.

| 경로 | 내용 |
|---|---|
| `data/documents.jsonl` | 가명화·검증을 마친 문서 |
| `data/manifest.json` | 원문 SHA-256과 문서 수 |
| `data/report.json` | PDF 추출 상세 보고 |
| `data/validation.json` | 문서별 메타데이터 검증 결과 |
| `data/chunks.jsonl` | 검색 적재용 청크 |
| `data/review.jsonl` | 사람이 검토해야 하는 청크 |
| `data/exceptions.jsonl` | 글자 상한 예외지만 토큰 한도 안인 청크 |
| `data/chunk_report.json` | 입력 단위·청크·검토·예외 건수 |
| `data/embeddings/<thread-id>.npy` | 이번 실행에서 만든 벡터 |
| `data/index_manifest.json` | 증분 판정용 해시·모델 서명·건수 |
| `data/chroma/` | KURE-v2 ChromaDB |
| `data/chroma_smoke/` | Smoke ChromaDB |
| `data/checkpoints/indexer.sqlite` | LangGraph 체크포인트 |
| `data/logs/<thread-id>.jsonl` | 본문·비밀값을 제외한 노드 감사 로그 |
| `data/index_run<N>.json` | 자동 번호가 붙은 실행 결과 |

결과 JSON은 stdout에도 출력됨. 저장 경로 안내는 stderr에 출력됨.

실측의 `exceptions.jsonl` 56건은 적재 실패가 아님.
필수 문맥을 보존하느라 600자 상한을 넘었지만 KURE-v2 토큰 한도 안에 들어온 청크임.

## 종료 코드

| 코드 | 의미 | 결과 확인 위치 |
|---:|---|---|
| `0` | 정상 완료 또는 dry-run | `status=ok` 또는 `dry_run` |
| `1` | 입력·설정·검증 오류 | `status=error`와 stderr |
| `2` | 검토 보류 청크 존재 | `chunk.review_count` |
| `3` | 일부 적재 실패 | `index.failed` |

코드 `2`와 `3`이 함께 해당하면 `3`이 우선임.
`status=ok`라도 종료 코드 `2` 또는 `3`일 수 있으므로 두 값을 함께 확인해야 함.

## 시간 제한과 감사 로그

| 작업 단위 | 기본 제한 |
|---|---:|
| PDF 파일 1건 추출 | 60초 |
| 청킹 입력 단위 1건 | 30초 |
| 임베딩 배치 1건 | 120초 |
| Chroma upsert 배치 1건 | 120초 |

모델 최초 적재는 작업 시간 제한에서 제외됨.
시간 제한 작업은 프로세스 공용 작업자 최대 4개로 실행되어 무제한 스레드 누적을 막음.

제한을 넘으면 호출자는 `TimeoutError`로 복귀함.
이미 실행 중인 Python 스레드는 강제 종료할 수 없음.  
따라서 실제 하부 작업은 끝날 때까지 계속될 수 있음.
외부 I/O의 자체 타임아웃과 함께 사용하는 운영 전제임.

노드마다 완료·실패, 경과 시간, 예외 종류만 `data/logs/<thread-id>.jsonl`에 기록함.
원문 본문·메타데이터·비밀값은 감사 로그에 기록하지 않음.

## 주의사항

- 출력 폴더를 원문 폴더와 같게 두거나 그 하위에 두면 종료 코드 1로 중단됨.
- `_instructor` 경로와 심볼릭 링크 입력은 선택 대상에서 제외됨.
- 상담 분리 건수와 `[상담ID]` 머리글 수가 다르면 중단됨.
- 프로필이 출처·식별 키를 덮어쓰려 하면 중단됨.
- `--full-reindex`와 일부 문서 선택을 함께 쓰면 컬렉션도 해당 선택 결과만 남게 됨.
- 실제 검증 범위와 미검증 항목은 `../verify-report.md`에서 확인 가능함.
