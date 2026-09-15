"""권한·융합·질문 변환·리랭킹·근거 대조 시험."""

from __future__ import annotations

from dataclasses import dataclass
import unittest

from app.application.state import AnswerDraft, EvidenceDraft, Hit, RouteDecision
from app.domain.access import build_where, filter_candidates
from app.domain.query_transform import (
    ensure_decomposition_coverage,
    merge_query_groups,
    route_query,
    rerank_each_query_and_merge,
    validate_route_decision,
    weighted_rrf,
)
from app.domain.scoring import build_answer, fuse, gate_score, passes_gate


def hit(chunk_id: str, score: float, *, vector_score=None, access="public", text="근거 원문") -> Hit:
    return Hit(
        chunk_id=chunk_id,
        score=score,
        vector_score=vector_score,
        access_level=access,
        source="source.pdf",
        location="제10조 제1항",
        text=text,
        metadata={"chunk_id": chunk_id, "access_level": access, "source": "source.pdf", "clause_no": "제10조 제1항"},
    )


class AccessAndScoringTests(unittest.TestCase):
    def test_agent_cannot_read_restricted(self):
        rows = [hit("P", 1.0), hit("R", 0.9, access="restricted")]
        self.assertEqual([item.chunk_id for item in filter_candidates(rows, "agent")], ["P"])
        self.assertIn("$in", build_where("agent")["access_level"])

    def test_auditor_reads_restricted(self):
        rows = [hit("R", 1.0, access="restricted")]
        self.assertEqual(len(filter_candidates(rows, "auditor")), 1)

    def test_unknown_role_fails_closed(self):
        with self.assertRaises(ValueError):
            build_where("admin")

    def test_fusion_preserves_vector_score_and_bm25_only_none(self):
        vector = [hit("V", 0.8, vector_score=0.8)]
        chunks = {"B": hit("B", 0.0)}
        output = fuse(vector, {"B": 3.0}, chunks, weight_bm25=0.4, weight_vector=0.6)
        by_id = {item.chunk_id: item for item in output}
        self.assertEqual(by_id["V"].vector_score, 0.8)
        self.assertIsNone(by_id["B"].vector_score)

    def test_fusion_uses_only_bm25_top_candidates_matching_vector_count(self):
        vector = [hit("V1", 0.8, vector_score=0.8), hit("V2", 0.7, vector_score=0.7)]
        chunks = {chunk_id: hit(chunk_id, 0.0) for chunk_id in ("B1", "B2", "B3")}
        output = fuse(
            vector,
            {"B1": 3.0, "B2": 2.0, "B3": 1.0},
            chunks,
            weight_bm25=0.4,
            weight_vector=0.6,
        )
        self.assertEqual({item.chunk_id for item in output}, {"V1", "V2", "B1", "B2"})

    def test_gate_uses_final_first_hit_only(self):
        rows = [hit("A", 1.0, vector_score=0.61), hit("B", 0.9, vector_score=0.90)]
        self.assertEqual(gate_score(rows), 0.61)
        self.assertFalse(passes_gate(rows, 0.62))


class QueryTransformTests(unittest.TestCase):
    def test_route_query_off_skips_router(self):
        result = route_query("질문", transform_mode="off", gate_score=0.1, gate_threshold=0.7)
        self.assertEqual((result["route_action"], result["llm_calls"]), ("off", 0))

    def test_route_query_gate_pass_skips_router(self):
        result = route_query("질문", transform_mode="auto", gate_score=0.71, gate_threshold=0.7)
        self.assertEqual((result["route_action"], result["llm_calls"]), ("gate_pass", 0))

    def test_route_query_calls_router_below_gate(self):
        @dataclass
        class Result:
            parsed: RouteDecision
            attempts: int
        class Router:
            def complete_structured(self, *args, **kwargs):
                return Result(
                    RouteDecision(action="keep", technique=None, queries=[], reason="유지", clarification=""),
                    attempts=3,
                )
        result = route_query("질문", transform_mode="auto", gate_score=0.69, gate_threshold=0.7, router=Router())
        self.assertEqual(result["llm_calls"], 3)

    def test_route_query_cache_hit_skips_router(self):
        class Cache:
            def get(self, query):
                return RouteDecision(action="keep", technique=None, queries=[], reason="캐시", clarification="")
            def put(self, query, decision):
                raise AssertionError("캐시 적중 때 쓰면 안 됨")
        result = route_query("질문", transform_mode="auto", gate_score=0.69, gate_threshold=0.7, cache=Cache())
        self.assertTrue(result["transform_cache_hit"])
        self.assertEqual(result["llm_calls"], 0)

    def test_route_query_multi_requires_exact_three(self):
        class Router:
            def complete_structured(self, *args, **kwargs):
                return RouteDecision(action="transform", technique="multi", queries=["a", "b"], reason="", clarification="")
        result = route_query("원본", transform_mode="auto", gate_score=0.1, gate_threshold=0.7, router=Router())
        self.assertEqual(result["route_action"], "keep")
        self.assertIn("정확히 3개", result["route_error"])

    def test_route_query_decomposition_range_two_to_four(self):
        class Router:
            def __init__(self, queries): self.queries = queries
            def complete_structured(self, *args, **kwargs):
                return RouteDecision(action="transform", technique="decomposition", queries=self.queries, reason="", clarification="")
        invalid = route_query("원본", transform_mode="auto", gate_score=0.1, gate_threshold=0.7, router=Router(list("abcde")))
        valid = route_query("원본", transform_mode="auto", gate_score=0.1, gate_threshold=0.7, router=Router(["a", "b", "c"]))
        self.assertEqual(invalid["route_action"], "keep")
        self.assertEqual(valid["transformed_queries"], ["a", "b", "c"])

    def test_merge_rewrite_uses_original_weight_point_five(self):
        rows, weights, coverage = merge_query_groups(
            [hit("A", 1.0)], [[hit("B", 1.0)]], technique="rewrite", rrf_k=60,
            original_weight=0.5, decomposition_original_weight=0.1,
            decomposition_per_query_top_k=3, top_k=5,
        )
        self.assertEqual(weights, {"original": 0.5, "transformed_each": 0.5})
        self.assertFalse(coverage)
        self.assertEqual(len(rows), 2)

    def test_merge_decomposition_uses_point_one_and_coverage(self):
        groups = [[hit(f"Q{group}-{index}", 1 - index / 10) for index in range(3)] for group in range(3)]
        rows, weights, coverage = merge_query_groups(
            [hit("O", 1.0)], groups, technique="decomposition", rrf_k=60,
            original_weight=0.5, decomposition_original_weight=0.1,
            decomposition_per_query_top_k=3, top_k=10,
        )
        self.assertEqual(weights, {"original": 0.1, "transformed_each": 0.3})
        self.assertTrue(coverage)
        self.assertTrue({item.chunk_id for item in rows}.issuperset({item.chunk_id for group in groups for item in group}))

    def test_weighted_rrf_is_deterministic(self):
        ranked = weighted_rrf([("q", [hit("B", 1), hit("A", .9)], 1.0)], rrf_k=60)
        self.assertEqual([item["hit"].chunk_id for item in ranked], ["B", "A"])

    def test_decomposition_coverage_reserves_each_top(self):
        a, b = hit("A", 1), hit("B", 1)
        ranked = weighted_rrf([("q1", [a], .5), ("q2", [b], .5)], rrf_k=60)
        covered = ensure_decomposition_coverage(ranked, [[b], [a]], per_query_top_k=1)
        self.assertEqual([item["hit"].chunk_id for item in covered[:2]], ["B", "A"])


class RerankAndEvidenceTests(unittest.TestCase):
    def test_rerank_scores_each_group_with_own_query(self):
        class Recorder:
            def __init__(self): self.queries = []
            def score(self, query, texts):
                self.queries.append(query)
                return [float(index) for index, _ in enumerate(texts, 1)]
        recorder = Recorder()
        groups = [("original", "원 질문", [hit("A", 1)], .5), ("transformed_1", "변환 질문", [hit("B", 1)], .5)]
        rerank_each_query_and_merge(groups, recorder, technique="rewrite", top_n=2, rrf_k=60, decomposition_original_weight=.1, decomposition_per_query_top_k=3)
        self.assertEqual(recorder.queries, ["원 질문", "변환 질문"])

    def test_decomposition_rerank_uses_max_transformed_score_and_original_weight(self):
        class ByText:
            def score(self, query, texts):
                table = {
                    "원 질문": {"공통": 0.8, "원문 전용": 0.9},
                    "하위 1": {"공통": 0.6, "하위 1 전용": 0.7},
                    "하위 2": {"공통": 0.95, "하위 2 전용": 0.5},
                }
                return [table[query][text] for text in texts]

        common = hit("C", 1.0, text="공통")
        groups = [
            ("original", "원 질문", [common, hit("O", .9, text="원문 전용")], .1),
            ("transformed_1", "하위 1", [common, hit("T1", .9, text="하위 1 전용")], .45),
            ("transformed_2", "하위 2", [common, hit("T2", .9, text="하위 2 전용")], .45),
        ]
        rows = rerank_each_query_and_merge(
            groups,
            ByText(),
            technique="decomposition",
            top_n=4,
            rrf_k=60,
            decomposition_original_weight=.1,
            decomposition_per_query_top_k=3,
        )
        self.assertEqual(rows[0].chunk_id, "C")
        self.assertAlmostEqual(rows[0].rerank_score, .9 * .95 + .1 * .8)

    def test_evidence_exact_quote_passes(self):
        answer = build_answer(
            AnswerDraft(conclusion="결론", caution="주의", evidence=[EvidenceDraft(ref=1, quote="근거 원문")]),
            [hit("A", 1.0)],
        )
        self.assertTrue(answer.verification.automatic_valid)
        self.assertTrue(answer.evidence[0].quote_verified)

    def test_evidence_mismatch_fails(self):
        answer = build_answer(
            AnswerDraft(conclusion="결론", caution="주의", evidence=[EvidenceDraft(ref=1, quote="없는 문장")]),
            [hit("A", 1.0)],
        )
        self.assertFalse(answer.verification.automatic_valid)


if __name__ == "__main__":
    unittest.main()
