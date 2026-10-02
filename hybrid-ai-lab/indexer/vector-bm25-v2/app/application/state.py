"""LangGraph 체크포인트에 저장할 직렬화 가능 상태를 정의함."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class IndexerState(TypedDict, total=False):
    """재시작 뒤에도 프로세스 메모리에 의존하지 않고 실행을 이어 가는 상태임."""

    request: dict[str, Any]  # 직렬화한 IndexRequest 값: input_path, output_path, doc(색인대상문서key), full_reindex, thread_id
    request_fingerprint: str  # 같은 thread_id의 다른 요청·설정 재사용을 막는 지문
    workflow_version: str  # 노드 구성 변경 뒤 진행 중인 구버전 체크포인트 재개를 막는 버전
    run_id: str  # 실행 중간 산출물을 묶는 식별자
    thread_id: str  # LangGraph 체크포인트 실행을 식별하는 값
    target_generation: str  # 활성 세대와 분리해 작성할 색인 세대
    policy_signature: str  # 청킹 정책 변경을 감지하는 서명
    profile_signature: str  # 문서 기본 메타데이터 프로필 변경을 감지하는 서명
    embedding_signature: str  # 검색기와 임베딩 모델의 호환성을 확인하는 서명
    sources: list[dict[str, Any]]  # 이번 실행에서 선택한 원천 문서 목록
    inputs_sha256: dict[str, str]  # 전체 결과에 포함할 원천별 내용 지문
    source_doc_keys: dict[str, str]  # 원천별 D1·D2·D3 문서 유형
    prepared_chunks_ref: str  # 개인정보 처리 후 청크를 보관한 외부 산출물 참조
    prepared_count: int  # 정제까지 끝난 청크 수
    plan: dict[str, Any]  # 임베딩·재사용·삭제 대상과 해시를 담은 실행 계획
    expected_count: int  # 새 세대에 게시되어야 하는 최종 청크 수
    vector_refs: list[str]  # 재사용하거나 새로 만든 벡터 산출물 참조 목록
    embed_cursor: int  # 임베딩이 끝난 신규 청크 수
    upsert_cursor: int  # 대상 세대에 적재가 끝난 청크 수
    completed_ids: list[str]  # 적재 완료를 검증할 청크 ID 목록
    text_index_stage: dict[str, Any]  # 키워드 검색용 BM25 색인의 검증 완료 증거
    publication: dict[str, Any] | None  # 게시된 세대 정보, 게시 전에는 None
    no_op: bool  # 원천과 처리 계약이 같아 실행을 생략했는지 여부
    failed: list[dict[str, Any]]  # 호출자에게 전달할 실패 항목 목록
    timings: dict[str, int]  # 단계별 누적 실행 시간(밀리초)
    status: Literal["ok", "dry_run", "error"]  # 호출자에게 전달할 실행 상태
    exit_code: int  # CLI 프로세스 종료 코드
