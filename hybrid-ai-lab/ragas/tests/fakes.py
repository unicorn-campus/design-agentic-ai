"""포트 모양의 가짜 구현(상속 없이 모양만 맞춤) — 호출 기록(calls)으로 행위까지 검증함."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.application.models import QualityError, StepError

QUESTIONS = [
    {"id": "Q01", "question": "연회비 면제 기준?", "answerable": True, "ground_truth": "300만 원 이상",
     "filters": [], "relevance": [{"source": "D1.pdf", "location": "제10조", "any_of": ["300만 원"]}]},
    {"id": "Q02", "question": "포인트로 연회비?", "answerable": False, "ground_truth": "확인 필요",
     "filters": [], "relevance": [], "no_answer_terms": [["연회비", "포인트"]]},
]


def retriever_log(version: str, recall: float, *, status: str = "answered", top_k: int = 5) -> dict[str, Any]:
    """evaluate_retriever.py 결과 모양의 가짜 로그."""

    metrics = {"hit": 1, "recall": recall, "mrr": 1.0, "precision": recall / 5, "ndcg": recall}
    rows = [
        {"id": "Q01", "version": version, "question": "연회비 면제 기준?", "answerable": True, "status": status,
         "evidence": [{"source": "D1.pdf", "text": "300만 원 이상이면 면제", "card_id": None}],
         "answer": ["300만 원 이상이면 면제됩니다."], "ground_truth": "300만 원 이상",
         "search": metrics, "search_fixed": metrics, "final": metrics},
        {"id": "Q02", "version": version, "question": "포인트로 연회비?", "answerable": False,
         "status": "needs_confirmation", "evidence": [], "answer": [], "ground_truth": "확인 필요",
         "search": {k: None for k in metrics}, "search_fixed": {k: None for k in metrics},
         "final": {k: None for k in metrics}},
    ]
    block = {"answerable": 1, "search_top5": metrics, "search_fixed": metrics, "final_evidence": metrics,
             "answerable_returned": 1, "answerable_returned_with_relevant": 1, "no_answer_refused": 1,
             "seconds_median": 1.0, "llm_calls_mean": 2.0}
    return {"version": version, "top_k": top_k, "metric_k": top_k, "fixed_k": 5,
            "config_snapshot": None, "summary": {"all": block}, "rows": rows}


class FakeJudge:
    """지표마다 정해 둔 점수를 돌려주는 평가자. fail_metric은 항상 실패함."""

    def __init__(self, scores: dict[str, float] | None = None, fail_metric: str | None = None):
        self.scores = scores or {}
        self.fail_metric = fail_metric
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def describe(self) -> dict[str, str]:
        return {"provider": "fake", "model": "fake-judge", "embedding_model": "fake-emb"}

    async def score(self, metric: str, fields: dict[str, Any]) -> tuple[float, str | None]:
        self.calls.append((metric, tuple(sorted(fields))))
        if metric == self.fail_metric:
            raise RuntimeError("IncompleteOutputException")
        return self.scores.get(metric, 0.8), f"{metric} 이유"


class FakePointer:
    """메모리 속 포인터. writes에 바꾼 내용을 남김."""

    def __init__(self, generation: str = "gen-base"):
        self.content = {"generation": generation, "chroma_path": f"generations/{generation}/chroma"}
        self.writes: list[str] = []

    def read(self) -> dict[str, Any]:
        return dict(self.content)

    def sha256(self) -> str:
        return "sha-" + self.content["generation"]

    def write(self, content: dict[str, Any]) -> str:
        self.content = dict(content)
        self.writes.append(content["generation"])
        return self.sha256()


class FakeLock:
    def __init__(self, busy: bool = False):
        self.busy, self.held, self.events = busy, False, []

    def acquire(self) -> None:
        if self.busy:
            raise QualityError("lock_unavailable", "busy", 2)
        self.held = True
        self.events.append("acquire")

    def release(self) -> None:
        self.held = False
        self.events.append("release")


class FakeIndexer:
    """재색인하면 포인터를 새 세대로 바꾸는 가짜 인덱서(게시를 흉내 냄)."""

    def __init__(self, pointer: FakePointer, fail: bool = False):
        self.pointer, self.fail = pointer, fail
        self.calls: list[tuple[str, dict[str, str]]] = []
        self.base_seen: list[str] = []

    def reindex(self, thread_id: str, env: dict[str, str], log_dir: Path) -> str:
        self.calls.append((thread_id, dict(env)))
        # 게시 조건: 시작할 때 포인터가 기준 세대여야 함(버전마다 되돌리기 확인용)
        self.base_seen.append(self.pointer.content["generation"])
        if self.fail:
            raise StepError("E-EXIT", "indexer 종료 코드 1")
        generation = f"gen-{thread_id}"
        self.pointer.write({"generation": generation, "chroma_path": f"generations/{generation}/chroma"})
        return generation


class FakeRetriever:
    """--out 위치에 가짜 결과 로그를 쓰는 리트리버. fail_versions의 버전은 실패함."""

    def __init__(self, pointer: FakePointer, supported: tuple[str, ...] = ("--top-k",),
                 fail_versions: tuple[str, ...] = (), interrupt_versions: tuple[str, ...] = ()):
        self.pointer, self.supported = pointer, supported
        self.fail_versions, self.interrupt_versions = fail_versions, interrupt_versions
        self.calls: list[dict[str, Any]] = []

    def supports(self, argument: str) -> bool:
        return argument in self.supported

    def run(self, args: list[str], env: dict[str, str], log_dir: Path) -> None:
        options = dict(zip(args[::2], args[1::2]))
        version = args[args.index("--version-label") + 1]
        self.calls.append({"args": args, "env": dict(env), "generation": self.pointer.content["generation"],
                           "version": version})
        if version in self.interrupt_versions:
            raise KeyboardInterrupt
        if version in self.fail_versions:
            raise StepError("E-EXIT", "retriever 종료 코드 1")
        recall = {"800": 0.8, "600": 0.9, "5": 0.8, "3": 0.7}.get(version, 0.5)
        out = Path(args[args.index("--out") + 1])
        out.parent.mkdir(parents=True, exist_ok=True)
        log = retriever_log(version, recall, top_k=int(options.get("--top-k", 5)))
        log["config_snapshot"] = json.loads(Path(args[args.index("--config-snapshot") + 1]).read_text(encoding="utf-8"))
        out.write_text(json.dumps(log, ensure_ascii=False), encoding="utf-8")


class FakeProbe:
    def __init__(self, running: list[str] | None = None):
        self.running = running or []

    def running_servers(self) -> list[str]:
        return list(self.running)


class FakeEnvironment:
    def snapshot(self) -> dict[str, Any]:
        return {"git_commit": "abc", "secrets": {"GROQ_API_KEY": "(설정됨)"}}
