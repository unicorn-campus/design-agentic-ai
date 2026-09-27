"""슬라이드 18~21 프롬프트·원문 위치·발췌 검증 테스트."""

from pathlib import Path
import json
import sys
import unittest

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))

from src.answering_ref import answer_with_sources, build_rag_prompt
from src.evidence import build_evidence_answer, parse_json_response, render_answer
from src.models import Hit
from src.sources import format_location, format_source, quote_is_in_text


REGULATION_TEXT = """제10조(연회비 면제)
① 직전 12개월 이용금액이 3,000,000원 이상이고 연체가 없으면 기본 연회비를 면제합니다.
② 승인 취소·환불 금액과 세금·공과금은 면제 실적에서 제외합니다."""


def regulation_hit() -> Hit:
    return Hit(REGULATION_TEXT, 0.8, {
        "chunk_id": "D1_0010",
        "source": "D1_개인회원표준약관_합성.pdf",
        "doc_type": "regulation",
        "clause_no": "제10조 제1항",
        "version": "1.2",
        "effective_date": "2027-01-15",
    })


class SourceTests(unittest.TestCase):
    def test_source_contains_file_and_revision(self):
        self.assertEqual(
            format_source(regulation_hit().metadata),
            "D1_개인회원표준약관_합성.pdf · v1.2 · 시행일 2027-01-15",
        )

    def test_regulation_location_comes_from_quote_paragraph(self):
        hit = regulation_hit()
        first, first_ok = format_location(hit.metadata, hit.text, "직전 12개월 이용금액이 3,000,000원 이상")
        second, second_ok = format_location(hit.metadata, hit.text, "승인 취소·환불 금액과 세금·공과금")
        self.assertEqual(first, "개인회원표준약관 제10조 제1항")
        self.assertEqual(second, "개인회원표준약관 제10조 제2항")
        self.assertTrue(first_ok and second_ok)

    def test_benefit_and_consult_locations(self):
        benefit = {
            "source": "D2_카드혜택안내_합성.pdf",
            "doc_type": "benefit_guide",
            "clause_no": "D2-C001 한빛 모아생활 · 연회비",
        }
        consult = {
            "source": "D3_S01_신규가입_상담이력_합성.txt",
            "doc_type": "consult_log",
            "record_id": "C-20260302-002",
            "turn_range": "1-4",
            "consult_date": "2026-03-02",
        }
        self.assertEqual(
            format_location(benefit, "총연회비는 22,000원입니다.", "총연회비는 22,000원입니다."),
            ("한빛 모아생활 > 연회비", True),
        )
        self.assertEqual(
            format_location(consult, "가입 전 이용월은 제외합니다.", "가입 전 이용월은 제외합니다."),
            ("상담 C-20260302-002 > 턴 1-4", True),
        )
        self.assertEqual(
            format_source(consult),
            "D3_S01_신규가입_상담이력_합성.txt · 상담일 2026-03-02",
        )

    def test_consult_location_finds_exact_turn_from_quote(self):
        metadata = {
            "source": "D3_S01_신규가입_상담이력_합성.txt",
            "doc_type": "consult_log",
            "record_id": "C-20260302-002",
            "turn_range": "4-8",
        }
        text = "고객: 첫 질문입니다.\n상담사: 첫 답변입니다.\n고객: 둘째 질문입니다.\n상담사: 둘째 답변입니다."
        self.assertEqual(
            format_location(metadata, text, "둘째 질문입니다."),
            ("상담 C-20260302-002 > 턴 5", True),
        )


class PromptTests(unittest.TestCase):
    def test_prompt_keeps_search_number_chunk_id_source_and_text(self):
        hit = regulation_hit()
        prompt = build_rag_prompt("연회비 면제 조건은?", [hit])
        self.assertIn("[검색결과 1]", prompt)
        self.assertIn("내부 chunk_id: D1_0010", prompt)
        self.assertIn("원본 문서: D1_개인회원표준약관_합성.pdf", prompt)
        self.assertIn(hit.text, prompt)
        self.assertTrue(prompt.endswith("[질문]\n연회비 면제 조건은?"))

    def test_empty_hits_and_empty_question(self):
        self.assertEqual(
            build_rag_prompt("질문", []),
            "[검색결과 목록]\n\n\n[질문]\n질문",
        )
        with self.assertRaises(ValueError):
            build_rag_prompt("  ", [regulation_hit()])


class EvidenceTests(unittest.TestCase):
    def test_valid_quotes_get_human_locations_and_internal_chunk_id(self):
        raw = json.dumps({
            "conclusion": "300만 원 이상 이용하고 연체가 없으면 면제됩니다.",
            "evidence": [
                {"ref": 1, "quote": "직전 12개월 이용금액이 3,000,000원 이상이고 연체가 없으면 기본 연회비를 면제합니다."},
                {"ref": 1, "quote": "승인 취소·환불 금액과 세금·공과금은 면제 실적에서 제외합니다."},
            ],
            "caution": "상품별 세부 조건은 확인 필요합니다.",
        }, ensure_ascii=False)
        answer = build_evidence_answer(raw, [regulation_hit()])
        self.assertTrue(answer["verification"]["automatic_valid"])
        self.assertEqual(
            [item["location"] for item in answer["evidence"]],
            ["개인회원표준약관 제10조 제1항", "개인회원표준약관 제10조 제2항"],
        )
        self.assertEqual(answer["evidence"][0]["chunk_id"], "D1_0010")
        rendered = render_answer(answer)
        self.assertIn("원문 위치: 개인회원표준약관 제10조 제1항", rendered)
        self.assertNotIn("prediction", answer)
        self.assertNotIn("예측값", rendered)

    def test_paraphrased_quote_and_bad_ref_fail(self):
        raw = json.dumps({
            "conclusion": "면제됩니다.",
            "evidence": [
                {"ref": 1, "quote": "300만 원을 쓰면 무조건 면제됩니다."},
                {"ref": 3, "quote": "없는 검색 결과"},
            ],
            "caution": "없음",
        }, ensure_ascii=False)
        answer = build_evidence_answer(raw, [regulation_hit()])
        self.assertFalse(answer["verification"]["automatic_valid"])
        self.assertEqual(answer["verification"]["invalid_refs"], [3])
        self.assertEqual(answer["verification"]["quote_failures"][0]["ref"], 1)

    def test_whitespace_and_code_fence_are_accepted(self):
        self.assertTrue(quote_is_in_text("기본 연회비", "기본\n연회비"))
        self.assertEqual(parse_json_response("```json\n{\"a\": 1}\n```"), {"a": 1})

    def test_answer_gate_skips_llm_or_returns_verified_answer(self):
        calls = []

        def fake_ask(system, user):
            calls.append((system, user))
            return {"content": json.dumps({
                "conclusion": "300만 원 이상 이용하고 연체가 없으면 면제됩니다.",
                "evidence": [{
                    "ref": 1,
                    "quote": "직전 12개월 이용금액이 3,000,000원 이상이고 연체가 없으면 기본 연회비를 면제합니다.",
                }],
                "caution": "없음",
            }, ensure_ascii=False)}

        low = Hit("관련 없음", 0.2, {"chunk_id": "LOW"})
        self.assertEqual(
            answer_with_sources("질문", [low], ask_fn=fake_ask)["conclusion"],
            "확인 필요",
        )
        self.assertEqual(calls, [])
        answer = answer_with_sources("질문", [regulation_hit()], ask_fn=fake_ask)
        self.assertTrue(answer["verification"]["automatic_valid"])
        self.assertEqual(len(calls), 1)

    def test_answer_gate_converts_non_json_response_to_needs_check(self):
        answer = answer_with_sources(
            "질문",
            [regulation_hit()],
            ask_fn=lambda system, user: {"content": "JSON이 아닌 응답"},
        )
        self.assertEqual(answer["conclusion"], "확인 필요")
        self.assertIn("LLM JSON 해석 실패", answer["caution"])


if __name__ == "__main__":
    unittest.main()
