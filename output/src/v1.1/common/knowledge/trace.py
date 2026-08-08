"""기록을 남길 **자리**만 둠. 무엇을 어떻게 남길지는 검사·기록 묶음이 정함.

질의 변환 전후와 재정렬 전후를 여기로 흘려 보냄. 이 파일은 값을 판단하지 않고
`common.guardrail_hooks`의 기록 자리에 그대로 넘김.
"""

from __future__ import annotations

from typing import Any

from common.guardrail_hooks import HookSet

from .result import RetrievalResult

__all__ = ["record_retrieval", "retrieval_fields"]


def retrieval_fields(result: RetrievalResult) -> dict[str, Any]:
    """기록에 넘길 값. 후보 내용은 넣지 않고 **자리와 개수 · 사유**만 넘김."""
    return {
        "route_id": result.route_id,
        "kind": result.kind.value,
        "candidate_count": result.candidate_count,
        "empty_reason": result.empty_reason,
        "notes": list(result.notes),
        "traces": [
            {
                "stage": trace.stage,
                "before": list(trace.before),
                "after": list(trace.after),
                "detail": dict(trace.detail),
            }
            for trace in result.traces
        ],
        "sources": [source.describe() for source in result.sources()],
    }


def record_retrieval(hooks: HookSet, step_id: str, result: RetrievalResult) -> None:
    """검색 1회를 기록 자리에 넘김. 여기서 무엇을 가릴지 정하지 않음."""
    hooks.recorder.record(step_id, retrieval_fields(result))
