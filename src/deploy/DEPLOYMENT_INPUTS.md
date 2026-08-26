# 미검증 설계: 배포 실행 입력값

실제 배포 미수행 상태임. 아래 필수 입력을 모두 확보하기 전 배포 시작 금지임.

| 이름 | 언제 정해지나 | 어디서 받아오나 | 필수 | 누가 가지고 있나 |
|---|---|---|:---:|---|
| `HELP_DESK_IMAGE_TAG` | 이미지 빌드 직전 | 커밋 식별자와 UTC 빌드 시각 | 예 | 배포 담당자 |
| 직전 정상 이미지 태그 | 배포 승인 전 | 이미지 저장소 배포 이력 | 예 | 배포 담당자 |
| `HELP_DESK_LLM_API_KEY` 비밀 객체 참조 | 운영 연결 승인 시 | 모델 벤더 비밀 보관소 | 예 | 모델 운영자 |
| `HELP_DESK_CHECKPOINT_URI` 비밀 객체 참조 | 저장소 준비 시 | 상태 저장소 비밀 보관소 | 예 | 데이터 운영자 |
| `HELP_DESK_CHECKPOINT_ENCRYPTION_KEY` 비밀 객체 참조 | 암호화 키 발급 시 | 키 관리 비밀 보관소 | 예 | 보안 담당자 |
| `HELP_DESK_MASKING_SALT` 비밀 객체 참조 | 비식별 키 발급 시 | 키 관리 비밀 보관소 | 예 | 보안 담당자 |
| `HELP_DESK_C_A1_CREDENTIAL` 비밀 객체 참조 | 실물 모델 연결 시 | 커넥터 비밀 보관소 | 조건부 | 연동 운영자 |
| `HELP_DESK_C_A2_CREDENTIAL` 비밀 객체 참조 | 실물 분석 뷰 연결 시 | 커넥터 비밀 보관소 | 조건부 | 연동 운영자 |
| `HELP_DESK_C_A3_CREDENTIAL` 비밀 객체 참조 | 실물 공식 검색 연결 시 | 커넥터 비밀 보관소 | 조건부 | 연동 운영자 |
| `HELP_DESK_C_A4_CREDENTIAL` 비밀 객체 참조 | 실물 CRM 연결 시 | 커넥터 비밀 보관소 | 조건부 | 연동 운영자 |
| `HELP_DESK_C_A5_CREDENTIAL` 비밀 객체 참조 | 실물 설문 연결 시 | 커넥터 비밀 보관소 | 조건부 | 연동 운영자 |
| `HELP_DESK_GLOSSARY_POSTGRES_DSN` 비밀 객체 참조 | 용어사전 적재 시 | PostgreSQL 비밀 보관소 | 조건부 | 데이터 운영자 |
| `HELP_DESK_KNOWLEDGE_RAG_DSN` 비밀 객체 참조 | RAG 연결 시 | PostgreSQL 비밀 보관소 | 조건부 | 데이터 운영자 |
| `HELP_DESK_KNOWLEDGE_GRAPH_PASSWORD` 비밀 객체 참조 | GraphRAG 연결 시 | Neo4j 비밀 보관소 | 조건부 | 데이터 운영자 |
| `HELP_DESK_KNOWLEDGE_GRAPH_ADMIN_USER` 비밀 객체 참조 | 그래프 role 준비 시 | Neo4j 운영 비밀 보관소 | 예 | 데이터 운영자 |
| `HELP_DESK_KNOWLEDGE_GRAPH_ADMIN_PASSWORD` 비밀 객체 참조 | 그래프 role 준비 시 | Neo4j 운영 비밀 보관소 | 예 | 데이터 운영자 |
| `HELP_DESK_RETENTION_APPROVAL_REF` | 실제 파기 승인 시 | 변경 승인 시스템 | 조건부 | 개인정보 보호 담당자 |

포트, 저장소 배치, 인스턴스 상한은 실행 정의에 이미 반영하는 확정값임.  
따라서 배포 실행 입력 목록에서 제외함.
