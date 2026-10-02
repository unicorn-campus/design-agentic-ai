"""색인 실행 유스케이스: 요청 한 건을 파이프라인으로 실행하고 CLI 결과로 바꿈."""

from __future__ import annotations

# monotonic()은 시스템 시간이 바뀌어도 뒤로 가지 않아 실행 시간 측정에 사용함.
from time import monotonic

from .ports import IndexConfigPort, IndexingPipelineFactoryPort
from .state import IndexerState, IndexRequest, IndexResult, build_index_result


def build_initial_state(request: IndexRequest, profiles: dict, schema: dict) -> IndexerState:
    """요청·프로필·규칙을 묶어 그래프가 사용할 첫 상태를 만듦."""

    return {
        "input_path": str(request.input_path),
        "output_path": str(request.output_path),
        "doc": request.doc,
        "segment": request.segment,
        "embedding_backend": request.embedding_backend,
        "dry_run": request.dry_run,
        "full_reindex": request.full_reindex,
        "thread_id": request.thread_id,
        "profiles": profiles,
        "schema": schema,
        "force_fail_node": None,
        "llm_calls": 0,
        "status": "ok",
        "exit_code": 0,
    }


class IndexingService:
    """presentation이 부르는 색인 실행 진입점.

    필요한 기능은 생성자로 포트를 주입받음. 실제 구현체 조립은 app/bootstrap.py가 담당함.
    """

    def __init__(self, pipelines: IndexingPipelineFactoryPort, config: IndexConfigPort) -> None:
        self._pipelines = pipelines  # 요청 조건에 맞는 실행 자원·파이프라인 준비
        self._config = config  # 문서 프로필·메타데이터 규칙 읽기

    def run(self, request: IndexRequest) -> IndexResult:
        """인덱싱 유스케이스 한 건을 동기 그래프로 실행함."""

        # 아래에서 실행 자원·설정·체크포인트를 준비하고, 인덱싱 그래프를 실행한 결과를 만듦.
        # monotonic()은 계속 증가하는 초 단위 값임. 예: 시작 100.250, 종료 102.875면 경과 시간은 2.625초임.
        started = monotonic()

        # 요청 설정에 맞는 실제 자원을 준비함.
        # 실제 자원은 Settings(설정), PdfReader(PDF 읽기), FileStore(파일 처리),
        # Embedder(텍스트를 숫자 벡터로 변환), VectorStore(벡터 저장·조회) 묶음임.
        pipeline = self._pipelines.create(request)

        # 원문 파일별 담당 부서·공개 등급 등의 프로필을 읽음.
        profiles = self._config.load_profiles()

        # 메타데이터에 허용되는 값과 필수 항목 규칙을 읽음.
        schema = self._config.load_schema()

        # 요청·프로필·규칙을 묶어 그래프가 사용할 첫 상태를 만듦.
        initial = build_initial_state(request, profiles, schema)

        # 체크포인트를 연결한 그래프를 실행함. 같은 thread_id의 이전 상태가 있으면 이어서 실행함.
        final_state = pipeline.run(initial, request.thread_id)

        # 모든 노드 시간에 전체 실행 시간을 더해 최종 결과에 기록함.
        final_state["timings"] = {
            **final_state.get("timings", {}),
            "total_ms": max(0, round((monotonic() - started) * 1000)),
        }

        # 그래프 상태를 CLI가 돌려줄 간결한 결과 객체로 바꿈.
        return build_index_result(final_state)
