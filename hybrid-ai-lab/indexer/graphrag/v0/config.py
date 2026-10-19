"""v0 설정을 한곳에 모음. 경로, 접속 주소, 모델 이름만 두고 비밀값은 환경변수나 secrets/.env에서만 읽음."""

from __future__ import annotations

import os
from pathlib import Path

V0 = Path(__file__).resolve().parent
LAB = V0.parents[2]  # hybrid-ai-lab
REPO = LAB.parent

# 실행 결과: 활성 세대 파일 하나와 세대별 폴더
DATA = V0 / "data"
GENERATIONS = DATA / "generations"
ACTIVE_FILE = DATA / "active_generation.json"

# 문서 유형별 그래프 스키마(graph_schema.json, approval.json, schema_spec.json)
SCHEMA_DIR = LAB / "indexer" / "graphrag" / "schema" / "doc"
DOC_TYPES = ("regulation", "benefit_guide", "consult_log")

# 1-a 인덱서. 청킹 결과 파일, 한국어 토크나이저, 임베더, 카드 별칭 규칙을 그대로 빌려 씀
VECTOR_BM25 = LAB / "indexer" / "vector-bm25"
DEFAULT_CHUNKS = VECTOR_BM25 / "data" / "artifacts" / "birthfix-20261018b" / "prepared-chunks.json"

# 비밀값 파일(GROQ_API_KEY)
SECRET_FILE = REPO / "secrets" / ".env"

# Neo4j: 비밀번호는 코드에 두지 않고 환경변수 NEO4J_PASSWORD로만 받음
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:17687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")

# 검색엔진(OpenSearch). 세대마다 인덱스 하나: card_chunks-{세대 ID}
OPENSEARCH_URL = os.environ.get("OPENSEARCH_URL", "http://localhost:19200")
INDEX_PREFIX = "card_chunks"

# LLM(K2 추출)
LLM_PROVIDER = "groq"
LLM_MODEL = os.environ.get("LLM_MODEL", "openai/gpt-oss-120b")
LLM_CONCURRENCY = 4  # 동시 호출 수
LLM_RETRIES = 2  # 형식 오류가 나면 같은 입력으로 다시 묻는 횟수

# 임베딩(S1 청크, K6 노드 설명): 1-a와 같은 KURE-v2
EMBED_MODEL = "nlpai-lab/KURE-v2"
EMBED_REVISION = "3431f86d399d666083890dbb882aced6708873bc"
EMBED_DIMENSION = 768

# BM25 조절값(1-a와 같음)
BM25_K1 = 1.5
BM25_B = 0.75
