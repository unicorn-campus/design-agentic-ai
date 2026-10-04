"""RAGAS 채점 — 리트리버 결과 로그를 핵심 4지표 × 반복 수만큼 채점하고 평균 · 흔들림을 모음."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.domain.scoring import METRIC_FIELDS, METRICS, describe, split_rows, to_ragas_row

from .ports import ArtifactStorePort, JudgePort


class RagasService:
    """RAGAS 채점 서비스.

    평가자는 JudgePort로 주입받음(평가자 만들기는 bootstrap). 동시 호출 수는 concurrency로 제한함 —
    로컬 평가자는 GPU 하나를 나눠 쓰므로 많이 열어도 빨라지지 않음.
    """

    def __init__(self, store: ArtifactStorePort, judge_factory: Callable[[str], JudgePort], *, concurrency: int = 4,
                 clock: Callable[[], datetime] | None = None):
        self.store, self.judge_factory, self.concurrency = store, judge_factory, max(1, concurrency)
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    async def score_rows(self, log: dict[str, Any], *, provider: str, repeat: int,
                         metrics: tuple[str, ...] = METRICS) -> dict[str, Any]:
        """결과 로그 하나를 채점해 보고서 dict를 만듦.

        방법: split_rows로 채점할 행을 고르고, (행 · 지표 · 회차)를 동시에 채점한 뒤 지표별로 모음.
        반환값: summary(지표별 평균 · 반복 평균들의 표준편차 · 최소 · 최대 · n · repeat_means) · rows · excluded ·
                failed_scores를 담은 dict. 실패한 칸은 평균에서 빠지고 failed_scores에 남음.
        부수효과: 평가자 LLM 호출(행 수 × 지표 수 × repeat 회).
        """

        judge = self.judge_factory(provider)
        eligible, excluded = split_rows(log["rows"])
        semaphore = asyncio.Semaphore(self.concurrency)
        failed: list[dict[str, Any]] = []
        results: dict[tuple[str, str, int], tuple[float, str | None]] = {}

        async def one(row: dict[str, Any], metric: str, index: int) -> None:
            ragas_row = to_ragas_row(row)
            fields = {name: ragas_row[name] for name in METRIC_FIELDS[metric]}
            async with semaphore:
                try:
                    results[(row["id"], metric, index)] = await judge.score(metric, fields)
                except Exception as error:  # 칸 하나의 실패로 전체 채점을 멈추지 않음(긴 근거의 개체 추출 미완료 등)
                    failed.append({"id": row["id"], "metric": metric, "repeat_index": index,
                                   "error": f"{type(error).__name__}: {str(error)[:300]}"})

        await asyncio.gather(*(one(row, metric, i) for row in eligible for metric in metrics for i in range(repeat)))

        rows_out = []
        for row in eligible:
            metric_out = {}
            for metric in metrics:
                scored = [results[(row["id"], metric, i)] for i in range(repeat) if (row["id"], metric, i) in results]
                metric_out[metric] = {**describe([value for value, _ in scored]),
                                      "values": [value for value, _ in scored],
                                      "reasons": [reason for _, reason in scored]}
            rows_out.append({"id": row["id"], "question": row["question"], "metrics": metric_out})

        summary = {}
        for metric in metrics:
            row_means = [r["metrics"][metric]["mean"] for r in rows_out if r["metrics"][metric]["mean"] is not None]
            # 반복 간 흔들림: 회차마다 문항 평균을 내고 그 평균들이 얼마나 흔들리는지 봄(개선 판정의 재료)
            repeat_means = []
            for i in range(repeat):
                values = [results[(r["id"], metric, i)][0] for r in eligible if (r["id"], metric, i) in results]
                if values:
                    repeat_means.append(round(sum(values) / len(values), 4))
            spread = describe(repeat_means)
            summary[metric] = {
                "mean": describe(row_means)["mean"], "std": spread["std"], "min": spread["min"],
                "max": spread["max"], "n": len(row_means), "repeat_means": repeat_means,
            }
        info = judge.describe()
        snapshot = log.get("config_snapshot") or {}
        return {
            "created_at": self.clock().isoformat(timespec="seconds"),
            "version": log.get("version"),
            "eval_set_hash": snapshot.get("eval_set_hash"),
            "provider": info.get("provider"), "model": info.get("model"),
            "embedding_model": info.get("embedding_model"), "repeat": repeat,
            "scored": len(eligible), "excluded": excluded,
            "summary": summary, "rows": rows_out, "failed_scores": failed,
        }

    def score_file(self, log_path: Path, out_path: Path, *, provider: str, repeat: int) -> dict[str, Any]:
        """리트리버 결과 파일을 읽어 채점하고 out_path에 저장함. 반환값: 저장한 보고서."""

        report = asyncio.run(self.score_rows(self.store.read_json(log_path), provider=provider, repeat=repeat))
        report["log_file"] = str(log_path)
        self.store.write_json(out_path, report)
        return report
