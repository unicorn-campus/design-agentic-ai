"""응용 계층의 색인 단계를 LangGraph 체크포인트 실행기로 연결함."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from time import monotonic
from typing import Any, Callable, cast

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.application.indexing_service import WORKFLOW_VERSION, IndexingWorkflow
from app.application.models import ThreadReuseError, TransientOperationError
from app.application.ports import PipelineRunnerPort, ProgressReporterPort
from app.application.state import IndexerState


def open_sqlite_checkpointer(path: str | Path) -> SqliteSaver:
    """프로세스 재시작 뒤에도 진행 상태를 복구할 SQLite 체크포인터를 엶.

    인자: path는 체크포인트 SQLite 파일 경로임. 부모 디렉터리는 없어도 됨.
    반환값: 호출자가 연결 수명과 닫기를 관리해야 하는 SqliteSaver임.
    예외: 디렉터리 생성, SQLite 연결, WAL 설정 실패 예외를 호출자에게 전달함.
    부수효과: 부모 디렉터리와 SQLite 파일을 만들고 저널 모드를 WAL로 설정함.
    ※ 저널모드 WAL(Write-Ahead Logging, 선기록 방식): 변경 내용을 DB 파일에 바로 덮어쓰지 않고
      옆의 `-wal` 파일에 먼저 이어 적은 뒤 나중에 DB 파일로 옮기는 방식임.
      읽기와 쓰기가 서로를 막지 않아, 노드마다 체크포인트를 기록하는 중에도 다른 스레드가 읽을 수 있음.
      프로세스가 강제 종료되어도 기록이 끝난 체크포인트는 남으므로 중단 지점부터 재개 가능함.
      실행 중 생기는 `-wal`·`-shm` 파일은 정상 부산물이므로 실행 중에 지우지 않아야 함.
    """

    checkpoint_path = Path(path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    connection.execute("PRAGMA journal_mode=WAL")
    return SqliteSaver(connection)


def execution_config(thread_id: str, recursion_limit: int) -> RunnableConfig:
    """체크포인트 실행 식별자와 그래프 순환 상한을 LangGraph 설정으로 만듦.

    인자: thread_id는 저장된 실행을 구분하는 값이며, recursion_limit은 한 invoke의 최대 단계 수임.
    반환값: LangGraph invoke와 체크포인터가 함께 사용하는 RunnableConfig임.
    부수효과: 없음.
    """

    return {"configurable": {"thread_id": thread_id}, "recursion_limit": recursion_limit}


NodeCompleted = Callable[[str, float], None]


def _timed(
    name: str,
    action: Callable[[IndexerState], dict[str, Any]],
    on_completed: NodeCompleted | None = None,
) -> Callable[[IndexerState], dict[str, Any]]:
    """성공한 노드 호출의 단계별 실행 시간을 상태 갱신값에 누적하는 래퍼를 만듦.

    실패한 시도와 재시도 대기 시간은 상태가 갱신되지 않으므로 포함하지 않음.
    on_completed가 있으면 성공한 호출마다 노드 이름과 소요 초를 전달함.
    """

    def wrapper(state: IndexerState) -> dict[str, Any]:
        """단계 함수를 실행하고 현재 호출에 걸린 밀리초를 누적함."""

        started = monotonic()
        update = dict(action(state) or {})
        elapsed = monotonic() - started
        timings = dict(state.get("timings", {}))
        timings[name] = timings.get(name, 0) + max(0, round(elapsed * 1000))
        update["timings"] = timings
        if on_completed is not None:
            on_completed(name, elapsed)
        return update

    return wrapper


def _after_discover_docs(state: IndexerState) -> str:
    """원천과 계약이 같으면 후속 비용 없이 실행을 끝내도록 분기함."""

    return "done" if state.get("no_op") else "load_split_clean"


def _after_load_split_clean(state: IndexerState) -> str:
    """건식 실행은 색인 변경 없이 끝내고 일반 실행만 계획 단계로 보냄."""

    return "done" if state.get("status") == "dry_run" else "prepare_embed"


def _after_prepare_embed(state: IndexerState) -> str:
    """새 임베딩 대상 유무에 따라 임베딩 또는 적재 단계로 분기함."""

    ids = state.get("plan", {}).get("embed_ids", [])
    return "embed" if int(state.get("embed_cursor", 0)) < len(ids) else "upsert"


def _after_embed(state: IndexerState) -> str:
    """임베딩 커서가 대상 끝에 도달할 때까지 배치 노드를 반복함."""

    ids = state.get("plan", {}).get("embed_ids", [])
    return "again" if int(state.get("embed_cursor", 0)) < len(ids) else "upsert"


def _after_upsert(state: IndexerState) -> str:
    """모든 최종 청크가 대상 세대에 적재될 때까지 배치 노드를 반복함."""

    expected = int(state.get("expected_count", 0))
    return "again" if int(state.get("upsert_cursor", 0)) < expected else "build_text_index"


def create_graph_builder(workflow: IndexingWorkflow, on_completed: NodeCompleted | None = None) -> StateGraph:
    """업무 로직 없이 그래프 연결·분기·재시도 정책만 정의함.

    목적: Workflow Graph 구성
    방법: 각 노드는 업무 함수를 그대로 등록하지 않고 `cast(Any, _timed(이름, 업무 함수, on_completed))`로 등록함.
      - `_timed`(데코레이터 함수): 업무 함수를 받아 시간 측정·완료 알림을 덧붙인 새 함수를 만들어 반환함.
        자신은 업무 함수를 실행하지 않으며, 노드 7개에 대해 한 번씩 호출되어 노드별 래퍼를 하나씩 만듦.
      - `_timed` 안의 `wrapper`(래퍼이자 클로저): LangGraph가 노드 차례마다 `wrapper(state)`로 자동 호출함.
        몸체에서 업무 함수를 직접 호출하고(`action(state)`) 앞뒤로 시각 기록·timings 누적·on_completed 호출을 수행함.
        LangGraph 노드는 state 하나만 받아야 하므로, 추가로 필요한 이름·업무 함수·콜백은 `_timed`가 받은 값을
        `wrapper`가 기억하는 클로저 방식으로 전달함.
      - `cast(Any, ...)`: 실행 시에는 값을 바꾸지 않고 그대로 반환하며 타입 검사기(mypy)에만 Any로 보이게 함.
        `_timed`의 반환 타입 `Callable[[IndexerState], dict[str, Any]]`가 `add_node`의 타입 정의(overload)
        어느 것과도 맞지 않아 타입검사 오류가 나므로, 동작은 같게 두고 이 인자의 타입 검사만 건너뜀.
        대신 이 자리에 모양이 틀린 함수를 넣어도 mypy가 잡지 못하므로 add_node 인자에만 최소로 적용함.
    인자: workflow는 외부 포트가 이미 주입된 응용 계층 단계 모음임.
    인자: on_completed는 노드가 성공할 때마다 이름과 소요 초를 받는 선택 콜백임.
    반환값: 호출자가 체크포인터와 함께 컴파일할 StateGraph임.
    예외: 노드·간선 등록이 유효하지 않으면 LangGraph 예외를 호출자에게 전달함.
    부수효과: 없음. 그래프를 실행하거나 체크포인트를 기록하지 않음.
    """

    builder = StateGraph(IndexerState)
    # 종료가 확인된 일시 오류만 재시도해 이전 호출과 새 호출이 동시에 외부 상태를 바꾸는 상황을 피함.
    retry = RetryPolicy(
        max_attempts=3,
        retry_on=lambda error: isinstance(error, TransientOperationError),
    )
    builder.add_node(
        "discover_docs",
        cast(Any, _timed("discover_docs", workflow.discover_docs, on_completed)),
        retry_policy=retry,
    )
    builder.add_node(
        "load_split_clean",
        cast(Any, _timed("load_split_clean", workflow.load_split_clean, on_completed)),
        retry_policy=retry,
    )
    builder.add_node(
        "prepare_embed",
        cast(Any, _timed("prepare_embed", workflow.prepare_embed, on_completed)),
        retry_policy=retry,
    )
    builder.add_node(
        "embed", cast(Any, _timed("embed", workflow.embed, on_completed)), retry_policy=retry
    )
    builder.add_node(
        "upsert", cast(Any, _timed("upsert", workflow.upsert, on_completed)), retry_policy=retry
    )
    builder.add_node(
        "build_text_index",
        cast(Any, _timed("build_text_index", workflow.build_text_index, on_completed)),
        retry_policy=retry,
    )
    builder.add_node(
        "publish", cast(Any, _timed("publish", workflow.publish, on_completed)), retry_policy=retry
    )

    builder.add_edge(START, "discover_docs")
    builder.add_conditional_edges(
        "discover_docs",
        _after_discover_docs,
        {"done": END, "load_split_clean": "load_split_clean"},
    )
    builder.add_conditional_edges(
        "load_split_clean",
        _after_load_split_clean,
        {"done": END, "prepare_embed": "prepare_embed"},
    )
    # 배치 하나가 끝날 때마다 노드를 종료해 커서가 체크포인트에 저장되고 중단 지점부터 재개 가능함.
    builder.add_conditional_edges(
        "prepare_embed",
        _after_prepare_embed,
        {"embed": "embed", "upsert": "upsert"},
    )
    builder.add_conditional_edges(
        "embed",
        _after_embed,
        {"again": "embed", "upsert": "upsert"},
    )
    builder.add_conditional_edges(
        "upsert",
        _after_upsert,
        {"again": "upsert", "build_text_index": "build_text_index"},
    )
    builder.add_edge("build_text_index", "publish")
    builder.add_edge("publish", END)
    return builder


def build_graph(
    workflow: IndexingWorkflow,
    checkpointer: SqliteSaver | None = None,
    on_completed: NodeCompleted | None = None,
) -> Any:
    """색인 그래프를 주어진 체크포인터와 결합해 실행 가능한 형태로 컴파일함.

    인자: workflow는 포트가 주입된 단계 모음이며, checkpointer가 None이면 실행 상태를 영속화하지 않음.
    인자: on_completed는 create_graph_builder에 그대로 전달하는 노드 완료 콜백임.
    반환값: invoke를 제공하는 컴파일된 LangGraph 실행기임.
    예외: 그래프 검증이나 컴파일 실패 예외를 호출자에게 전달함.
    부수효과: 컴파일 자체는 색인 업무를 실행하지 않음.
    """

    return create_graph_builder(workflow, on_completed).compile(checkpointer=checkpointer)


def _checkpoint_state(checkpoint: Any) -> dict[str, Any]:
    """LangGraph 체크포인트에서 업무 상태 채널만 안전하게 꺼냄."""

    if checkpoint is None:
        return {}
    value = getattr(checkpoint, "checkpoint", None)
    if not isinstance(value, dict):
        return {}
    channels = value.get("channel_values", {})
    return dict(channels) if isinstance(channels, dict) else {}


class LangGraphPipeline(PipelineRunnerPort):
    """SQLite 체크포인트와 저장된 산출물로 새 프로세스에서도 실행을 이어 가는 실행기임.

    IndexingWorkflow와 체크포인트 경로, 선택적 진행 알림 포트를 주입받으며, 색인 단계의 업무 규칙은 구현하지 않음.
    """

    def __init__(
        self,
        workflow: IndexingWorkflow,
        checkpoint_path: str | Path,
        *,
        recursion_limit: int = 10_000,
        progress: ProgressReporterPort | None = None,
    ) -> None:
        """워크플로와 체크포인트 위치, 한 번의 실행 단계 상한을 주입받음.

        인자: recursion_limit은 배치 반복을 포함한 한 invoke의 최대 LangGraph 단계 수임.
        인자: progress가 None이면 노드 완료를 알리지 않음.
        부수효과: 없음. SQLite 연결은 run 호출마다 열고 닫음.
        """

        self.workflow = workflow
        self.checkpoint_path = Path(checkpoint_path)
        self.recursion_limit = recursion_limit
        self.progress = progress

    def run(self, initial_state: dict[str, Any], thread_id: str) -> dict[str, Any]:
        """새 실행을 시작하거나 같은 요청 지문을 가진 체크포인트에서 재개함.

        인자: initial_state에는 request_fingerprint가 있어야 하며, thread_id는 체크포인트 키로 사용됨.
        반환값: 그래프가 정상 종료한 뒤의 전체 상태임.
        예외: 저장된 요청 지문이 다르면 ThreadReuseError를, 단계 실패 시 해당 예외를 전달함.
        부수효과: SQLite 체크포인트와 워크플로가 사용하는 중간 산출물·색인 저장소를 변경함.
        """

        # 누적 시간은 이번 프로세스의 run 시작부터 셈. 재개 실행이면 이전 프로세스에서 쓴 시간은 포함하지 않음.
        run_started = monotonic()
        progress = self.progress


        def on_completed(node: str, node_seconds: float) -> None:
            """노드 소요 초에 이번 실행의 누적 경과 초를 더해 진행 알림 포트로 넘김."""
            if progress is not None:
                progress.node_completed(node, node_seconds, monotonic() - run_started)

        saver = open_sqlite_checkpointer(self.checkpoint_path)  # checkpointer 객체 생성 
        
        # 노드 이름이 바뀐 구버전의 진행 위치를 새 그래프가 잘못 해석하지 않도록 thread 저장 공간을 분리함.
        checkpoint_thread_id = f"{WORKFLOW_VERSION}:{thread_id}"
        config = execution_config(checkpoint_thread_id, self.recursion_limit)
        try:
            # ==== 같은 스레드ID인데 지난번 저장된 실행과 이번 실행의 요청이나 설정이 변경되었는지 체크 ===

            # 같은 thread에 저장된 진행 기록이 있는지 먼저 확인해 새 실행과 재개 실행을 구분함.
            existing = saver.get_tuple(config)  # thread의 최신 체크포인트(상태·메타데이터 묶음), 없으면 None
            previous = _checkpoint_state(existing)
            
            expected = str(initial_state.get("request_fingerprint", ""))
            actual = str(previous.get("request_fingerprint", ""))   # 새 thread에서 수행이면 빈 값
            # 다른 요청을 같은 스레드에서 재개하면 이전 커서와 산출물이 새 요청에 섞일 수 있음.
            if existing is not None and actual != expected:
                raise ThreadReuseError(
                    "같은 thread_id에 저장된 요청 또는 처리 설정이 현재 실행과 다릅니다. "
                    "새 thread_id를 사용해야 합니다."
                )
            # ====================
            
            # workflow graph 빌드 
            graph = build_graph(self.workflow, saver, on_completed if progress is not None else None)
            
            # workflow 실행 
            return dict(graph.invoke(None if existing is not None else initial_state, config))
        finally:
            saver.conn.close()
