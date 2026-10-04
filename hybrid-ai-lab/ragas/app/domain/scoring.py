"""RAGAS 채점 대상 고르기 · 반복 집계 · 사람과 LLM 판정 일치도 계산 규칙."""

from __future__ import annotations

from dataclasses import dataclass
import statistics
from typing import Any, Iterable

ANSWERED_STATUSES = frozenset({"answered", "retrieved"})  # 근거를 들고 끝난 응답 상태(리트리버 응답 상태 6종 중)

# 지표 이름 → RAGAS ascore가 읽는 칸. 핵심 4지표(위 · 정 · 출 · 관) — 검색 지표 2 + 생성 지표 2
# 보조 지표(ContextEntityRecall · FactualCorrectness)는 재지 않음(사용자 결정 2026-10-04)
METRIC_FIELDS: dict[str, tuple[str, ...]] = {
    "context_precision": ("user_input", "reference", "retrieved_contexts"),
    "context_recall": ("user_input", "retrieved_contexts", "reference"),
    "faithfulness": ("user_input", "response", "retrieved_contexts"),
    "answer_relevancy": ("user_input", "response"),
}
METRICS = tuple(METRIC_FIELDS)


def to_ragas_row(row: dict[str, Any]) -> dict[str, Any]:
    """리트리버 결과 행 하나를 RAGAS 4칸으로 옮김.

    근거는 개수가 아니라 본문 목록이어야 하고, 답변은 문장 목록을 공백으로 이어 붙임.
    """

    return {
        "user_input": row["question"],
        "retrieved_contexts": [item["text"] for item in row.get("evidence") or []],
        "response": " ".join(row.get("answer") or []),
        "reference": row.get("ground_truth", ""),
    }


def split_rows(rows: Iterable[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """RAGAS로 채점할 행과 뺄 행을 나눔.

    빼는 사유는 먼저 걸린 하나만 적음: 답 없음 문항 → 답을 안 냄 → 근거 없음 → 답변 없음 순.
    반환값: (채점 행 목록, {id, reason} 목록). 지표 평균의 분모는 채점 행 수임.
    """

    eligible: list[dict[str, Any]] = []
    excluded: list[dict[str, str]] = []
    for row in rows:
        if not row.get("answerable"):
            reason = "no_answer_question"
        elif row.get("status") not in ANSWERED_STATUSES:
            reason = "status_not_answered"
        elif not row.get("evidence"):
            reason = "empty_evidence"
        elif not row.get("answer"):
            reason = "empty_response"
        else:
            eligible.append(row)
            continue
        excluded.append({"id": row["id"], "reason": reason})
    return eligible, excluded


def describe(values: list[float]) -> dict[str, Any]:
    """평균 · 표본 표준편차 · 최소 · 최대 · 개수를 냄. 값이 1개면 표준편차는 None, 0개면 모두 None."""

    if not values:
        return {"mean": None, "std": None, "min": None, "max": None, "n": 0}
    return {
        "mean": round(statistics.mean(values), 4),
        "std": round(statistics.stdev(values), 4) if len(values) > 1 else None,
        "min": round(min(values), 4),
        "max": round(max(values), 4),
        "n": len(values),
    }


@dataclass(frozen=True)
class Agreement:
    """한 지표의 LLM 판정과 사람 종합 판정의 2×2 표와 일치도."""

    metric: str
    tp: int  # 둘 다 합격
    fp: int  # LLM만 합격 — 평가자가 너그러움
    fn: int  # LLM만 불합격 — 평가자가 엄격함
    tn: int  # 둘 다 불합격

    @property
    def n(self) -> int:
        """판정을 비교한 문항 수."""

        return self.tp + self.fp + self.fn + self.tn

    @property
    def agreement(self) -> float | None:
        """같은 판정을 낸 비율."""

        return round((self.tp + self.tn) / self.n, 4) if self.n else None

    @property
    def f1(self) -> float | None:
        """'합격' 판정의 정밀도와 재현율의 조화평균. 합격이 한 번도 없으면 None."""

        denominator = 2 * self.tp + self.fp + self.fn
        return round(2 * self.tp / denominator, 4) if denominator else None

    @property
    def kappa(self) -> float | None:
        """우연히 맞는 몫을 뺀 일치도(코헨 카파). 우연 일치가 1이면(한쪽이 전부 같은 판정) 정의할 수 없어 None."""

        if not self.n:
            return None
        llm_pass = (self.tp + self.fp) / self.n
        human_pass = (self.tp + self.fn) / self.n
        chance = llm_pass * human_pass + (1 - llm_pass) * (1 - human_pass)
        if chance >= 1:
            return None
        return round(((self.tp + self.tn) / self.n - chance) / (1 - chance), 4)


def agreement(metric: str, pairs: Iterable[tuple[float, bool]], threshold: float) -> Agreement:
    """(LLM 점수, 사람 합격 여부) 쌍으로 2×2 표를 만듦. LLM 합격 = 점수 ≥ threshold."""

    tp = fp = fn = tn = 0
    for score, human_pass in pairs:
        llm_pass = score >= threshold
        if llm_pass and human_pass:
            tp += 1
        elif llm_pass:
            fp += 1
        elif human_pass:
            fn += 1
        else:
            tn += 1
    return Agreement(metric, tp, fp, fn, tn)
