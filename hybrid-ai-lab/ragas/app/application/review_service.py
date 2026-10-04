"""사람 검토표 — 문항당 1행 검토표를 내보내고, 사람 종합 판정과 지표별 LLM 판정의 일치도를 계산함."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from app.domain.scoring import METRICS, agreement

from .models import QualityError
from .ports import ArtifactStorePort

EVIDENCE_LIMIT = 600  # 검토표 근거 칸 최대 글자 수 — 엑셀 한 칸에서 읽을 수 있는 길이(설계 가정)
MIN_TRUSTED = 60  # 채점관 검증에 필요한 판정 수 — 이보다 적으면 결과를 '참고값'으로 표시
HUMAN_COLUMNS = ["human_pass", "human_reason"]


def _header() -> list[str]:
    """검토표 열 순서 — 기계가 채우는 칸 다음에 사람 칸 2개."""

    return (["id", "version", "question", "ground_truth", "answer", "evidence", "status", "code_hit"]
            + [f"ragas_{m}" for m in METRICS] + [f"ragas_{m}_reason" for m in METRICS] + HUMAN_COLUMNS)


class ReviewService:
    """검토표 export · agree 서비스. 지표 고르기 · 기준값 조정 · 평가자 선택은 사람이 함(도구는 수치만 냄)."""

    def __init__(self, store: ArtifactStorePort, clock: Callable[[], datetime] | None = None):
        self.store = store
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    def export(self, retriever_log: Path, ragas_report: Path, out_path: Path, *, version: str | None = None,
               overwrite: bool = False) -> int:
        """문항당 1행 검토표를 씀.

        인자: overwrite=False면 사람 판정이 이미 들어 있는 검토표를 덮어쓰지 않음(사람이 적은 판정을 지키려는 것).
        반환값: 쓴 행 수(평가셋 문항 수와 같음 — 답 없음 문항도 '확인 필요'로 끝났는지 사람이 봄).
        예외: 판정이 들어 있는 검토표를 덮어쓰려 하면 QualityError("review_has_judgements").
        """

        if self.store.exists(out_path) and not overwrite:
            filled = [r for r in self.store.read_csv(out_path) if (r.get("human_pass") or "").strip()]
            if filled:
                raise QualityError("review_has_judgements",
                                   f"사람 판정 {len(filled)}건이 든 검토표가 있어 덮어쓰지 않음: {out_path}")
        log = self.store.read_json(retriever_log)
        ragas = {row["id"]: row["metrics"] for row in self.store.read_json(ragas_report).get("rows", [])}
        rows = []
        for row in log["rows"]:
            metrics = ragas.get(row["id"], {})
            evidence = " | ".join(f"[{i}] {item['text']}" for i, item in enumerate(row.get("evidence") or [], 1))
            record = {
                "id": row["id"], "version": version or log.get("version") or "",
                "question": row["question"], "ground_truth": row.get("ground_truth", ""),
                "answer": " ".join(row.get("answer") or []),
                "evidence": evidence[:EVIDENCE_LIMIT] + ("…" if len(evidence) > EVIDENCE_LIMIT else ""),
                "status": row.get("status", ""),
                "code_hit": "" if row["final"]["hit"] is None else row["final"]["hit"],
                "human_pass": "", "human_reason": "",
            }
            for metric in METRICS:
                item = metrics.get(metric) or {}
                record[f"ragas_{metric}"] = "" if item.get("mean") is None else item["mean"]
                reasons = [r for r in item.get("reasons") or [] if r]
                record[f"ragas_{metric}_reason"] = reasons[0] if reasons else ""
            rows.append(record)
        self.store.write_csv(out_path, _header(), rows)
        return len(rows)

    def agree(self, csv_paths: list[Path], *, threshold: float, out_path: Path | None = None) -> dict[str, Any]:
        """사람 종합 판정(pass · fail)을 기준으로 지표마다 2×2 표 · 일치율 · F1 · kappa를 냄.

        방법: human_pass가 pass · fail인 행만 셈. 지표 점수가 빈 행(채점에서 빠진 행)은 그 지표 비교에서만 뺌.
        반환값: 지표별 결과와 기입 오류 목록. 판정이 60건 미만이면 confidence가 '참고값'임.
        부수효과: out_path가 있으면 JSON으로 저장함.
        """

        judged: list[dict[str, str]] = []
        problems: list[dict[str, str]] = []
        for path in csv_paths:
            for row in self.store.read_csv(path):
                value = (row.get("human_pass") or "").strip().lower()
                if value in {"pass", "fail"}:
                    judged.append({**row, "human_pass": value})
                elif value:
                    problems.append({"file": str(path), "id": row.get("id", ""), "value": value})
        results = []
        for column in [f"ragas_{m}" for m in METRICS] + ["code_hit"]:
            pairs = [(float(r[column]), r["human_pass"] == "pass") for r in judged if (r.get(column) or "") != ""]
            item = agreement(column, pairs, threshold)
            results.append({"metric": column, "tp": item.tp, "fp": item.fp, "fn": item.fn, "tn": item.tn,
                            "n": item.n, "agreement": item.agreement, "f1": item.f1, "kappa": item.kappa,
                            "threshold": threshold,
                            "confidence": "검증 가능" if item.n >= MIN_TRUSTED else "참고값"})
        report = {"created_at": self.clock().isoformat(timespec="seconds"),
                  "files": [str(p) for p in csv_paths], "judged": len(judged),
                  "input_problems": problems, "metrics": results}
        if out_path is not None:
            self.store.write_json(out_path, report)
        return report
