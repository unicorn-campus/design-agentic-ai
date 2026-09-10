"""교재 경계 규칙과 원문 보존에 대한 외부 서비스 없는 회귀 검사."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.chunking import Chunk, ITEM_RE, chunk_by_clause, chunk_by_turn, enforce_token_limit, make_chunk


class ClauseTests(unittest.TestCase):
    def test_boundaries_and_branched_article(self):
        text = "표지\n# 제1조(목적)\n(1) 목적 본문.\n제3조의2(예외)\n(10) 예외 본문."
        chunks = chunk_by_clause(text, {"source": "D1_test.md"})
        self.assertEqual([c.chunk_id for c in chunks], ["D1_0000", "D1_0001"])
        self.assertEqual([c.metadata["clause_no"] for c in chunks], ["제1조", "제3조의2"])
        self.assertNotIn("표지", "".join(c.text for c in chunks))
        self.assertIn("(10) 예외 본문.", chunks[1].text)

    def test_item_pattern_is_not_character_class(self):
        self.assertEqual([m.group("no") for m in ITEM_RE.finditer("(1) 가\n(10) 나\n1. 호\n(20) 다")],
                         ["1", "10", "20"])

    def test_short_article_keeps_items_together(self):
        text = "제1조(목적)\n(1) 가.\n(2) 나."
        self.assertEqual([c.text for c in chunk_by_clause(text, {"doc_key": "D1"})], [text])

    def test_length_title_overlap_and_no_cross_article_overlap(self):
        body = "\n".join(f"({i}) 조건{i:02d} " + "가나다라마바사 " * 6 for i in range(1, 8))
        chunks = chunk_by_clause("제1조(환불)\n" + body + "\n제2조(변경)\n새 조문.",
                                 {"doc_key": "D1"}, 120, 15)
        self.assertTrue(all(len(c.text) <= 120 for c in chunks))
        self.assertTrue(all(c.text.startswith("제1조(환불)") for c in chunks[:-1]))
        self.assertIn(chunks[0].text[-15:], chunks[1].text)
        self.assertEqual(chunks[-1].text, "제2조(변경)\n새 조문.")
        for i in range(1, 8):
            self.assertIn(f"조건{i:02d}", "\n".join(c.text for c in chunks))

    def test_huge_item_character_fallback_preserves_every_character(self):
        body = "(1) " + "".join(chr(0xAC00 + i) for i in range(400))
        chunks = chunk_by_clause("제1조\n" + body, {"doc_key": "D1"}, 90, 0)
        restored = "".join(c.text.partition("\n")[2] for c in chunks)
        self.assertEqual(restored, body)
        self.assertTrue(all(c.metadata["clause_no"] == "제1조 제1항" for c in chunks))

    def test_circled_source_items_preserved(self):
        text = "제1조\n① " + "가" * 40 + "\n② " + "나" * 40
        chunks = chunk_by_clause(text, {"doc_key": "D1"}, 60, 0)
        self.assertEqual([c.metadata["clause_no"] for c in chunks], ["제1조 제1항", "제1조 제2항"])
        self.assertIn("①", chunks[0].text)
        self.assertIn("②", chunks[1].text)

    def test_table_repeats_header_and_conditions_without_losing_rows(self):
        rows = [f"| 항목{i} | {i}000원 |" for i in range(10)]
        text = "## 샘플카드 혜택\n전월 30만원 이상 조건.\n| 항목 | 한도 |\n| --- | --- |\n" + "\n".join(rows)
        chunks = chunk_by_clause(text, {"source": "D2_benefits.md"}, 120, 0)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk.text), 120)
            self.assertIn("## 샘플카드 혜택", chunk.text)
            self.assertIn("전월 30만원 이상 조건.", chunk.text)
            self.assertIn("| 항목 | 한도 |\n| --- | --- |", chunk.text)
        for row in rows:
            self.assertEqual(sum(row in c.text.splitlines() for c in chunks), 1)

    def test_table_oversized_row_creates_exception_candidate(self):
        text = "## 카드\n| 항목 | 조건 |\n| --- | --- |\n| 할인 | " + "긴내용" * 100 + " |"
        chunks = chunk_by_clause(text, {"doc_key": "D2"}, 100, 0)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, text)
        self.assertTrue(chunks[0].metadata["size_exception"])
        self.assertEqual(chunks[0].metadata["token_check"], "required")
        self.assertIn("단일 행과 필수 문맥", chunks[0].metadata["exception_reason"])

    def test_attribute_table_repeats_all_conditions_and_deduplicates(self):
        rows = ["| 혜택 | " + "내용" * 25 + " |", "| 실적 조건 | 전월 30만원 이상 |",
                "| 한도 | 월 1만원 |", "| 취소·제외 | 취소하면 지급액 회수 |"]
        text = "## 카드 혜택\n| 항목 | 합성 조건 |\n| --- | --- |\n" + "\n".join(rows)
        chunks = chunk_by_clause(text, {"doc_key": "D2"}, 120, 0)
        self.assertEqual(len(chunks), 1)
        self.assertTrue(chunks[0].metadata["size_exception"])
        for row in rows:
            self.assertIn(row, chunks[0].text)

    def test_short_table_is_unchanged(self):
        text = "## 카드\n| 항목 | 합성 조건 |\n| --- | --- |\n| 혜택 | 포인트 |\n각주 내용."
        chunks = chunk_by_clause(text, {"doc_key": "D2"}, 600, 0)
        self.assertEqual(chunks[0].text, text)
        self.assertNotIn("size_exception", chunks[0].metadata)

    def test_long_independent_table_has_only_single_row_exceptions(self):
        rows = ["| 짧은행 | 가 |", "| 긴행 | " + "나" * 120 + " |", "| 마지막 | 다 |"]
        text = "## 카드\n조건 반복.\n| 항목 | 설명 |\n| --- | --- |\n" + "\n".join(rows)
        chunks = chunk_by_clause(text, {"doc_key": "D2"}, 100, 0)
        self.assertEqual(len(chunks), 3)
        self.assertEqual([bool(c.metadata.get("size_exception")) for c in chunks], [False, True, False])
        self.assertIn(rows[1], chunks[1].text)
        self.assertNotIn(rows[0], chunks[1].text)
        self.assertNotIn(rows[2], chunks[1].text)

    def test_metadata_is_copied_and_lengths_are_computed(self):
        meta = {"doc_key": "D1_custom", "page": 2, "tags": ["합성"], "char_len": 999}
        chunks = chunk_by_clause("제1조\n내용.\n제2조\n다른 내용.", meta)
        chunks[0].metadata["tags"].append("변경")
        self.assertEqual(meta["tags"], ["합성"])
        self.assertEqual(chunks[1].metadata["tags"], ["합성"])
        self.assertEqual(meta["char_len"], 999)
        self.assertEqual(chunks[0].metadata["char_len"], len(chunks[0].text))
        self.assertEqual(chunks[0].chunk_id, "D1_custom_0000")

    def test_unknown_source_and_too_long_title_are_errors(self):
        with self.assertRaisesRegex(ValueError, "doc_key"):
            chunk_by_clause("내용", {})
        with self.assertRaises(ValueError):
            chunk_by_clause("제1조(" + "가" * 100 + ")", {"doc_key": "D1"}, 80, 0)


class TurnTests(unittest.TestCase):
    @staticmethod
    def dialogue(count):
        return "\n".join(f"고객: 질문{i}\n상담사: 답변{i}" for i in range(1, count + 1))

    def test_twelve_turns_tail_and_overlap(self):
        chunks = chunk_by_turn(self.dialogue(12), {"record_id": "C-2026-0117", "access_level": "restricted"})
        self.assertEqual([c.metadata["turn_range"] for c in chunks], ["1-4", "4-7", "7-12"])
        self.assertEqual(chunks[0].chunk_id, "D3_C-2026-0117_0000")
        self.assertIn("고객: 질문4\n상담사: 답변4", chunks[0].text)
        self.assertTrue(chunks[1].text.startswith("고객: 질문4\n상담사: 답변4"))
        self.assertTrue(chunks[-1].text.endswith("상담사: 답변12"))
        self.assertTrue(all(c.metadata["access_level"] == "restricted" for c in chunks))

    def test_three_new_turns_create_new_chunk(self):
        chunks = chunk_by_turn(self.dialogue(7), {"record_id": "A"})
        self.assertEqual([c.metadata["turn_range"] for c in chunks], ["1-4", "4-7"])

    def test_consecutive_speaker_multiline_and_odd_tail_preserved(self):
        text = "고객: 질문\n고객: 추가 질문\n설명 계속\n상담사: 답변\n고객: 마지막"
        chunks = chunk_by_turn(text, {"record_id": "A"})
        self.assertEqual(chunks[0].metadata["turn_range"], "1-2")
        self.assertEqual(chunks[0].text, "고객: 질문\n추가 질문\n설명 계속\n상담사: 답변\n고객: 마지막")

    def test_records_have_distinct_ids(self):
        first = chunk_by_turn(self.dialogue(1), {"record_id": "A"})
        second = chunk_by_turn(self.dialogue(1), {"record_id": "B"})
        self.assertNotEqual(first[0].chunk_id, second[0].chunk_id)

    def test_unrecognized_body_and_missing_record_id_are_errors(self):
        with self.assertRaisesRegex(ValueError, "시작"):
            chunk_by_turn("앞부분\n고객: 내용", {"record_id": "A"})
        with self.assertRaisesRegex(ValueError, "record_id"):
            chunk_by_turn("고객: 내용", {})


class ContractTests(unittest.TestCase):
    def test_empty(self):
        self.assertEqual(chunk_by_clause(" \n", {}), [])
        self.assertEqual(chunk_by_turn(" \n", {}), [])

    def test_invalid_parameters(self):
        for size, overlap in [(0, 0), (10, 10), (10, -1), (True, 0), (2.5, 0)]:
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                chunk_by_clause("", {}, size, overlap)
        for size, overlap in [(0, 0), (4, 4), (4, -1), (True, 0)]:
            with self.subTest(size=size, overlap=overlap), self.assertRaises(ValueError):
                chunk_by_turn("", {}, size, overlap)

    def test_make_chunk(self):
        chunk = make_chunk("가나다", {"source": "합성"}, "D1", 12, clause_no="제1조")
        self.assertIsInstance(chunk, Chunk)
        self.assertEqual(chunk.chunk_id, "D1_0012")
        self.assertEqual(chunk.metadata["char_len"], 3)


class TokenLimitTests(unittest.TestCase):
    # 아래 테스트 전용 tokenizer는 글자 하나를 토큰 하나로 정의함.
    # 실제 임베딩 모델의 토큰 수를 추정하거나 대신하는 용도가 아님.
    @staticmethod
    def tokenizer(text):
        return list(text)

    def count(self, text):
        return len(self.tokenizer(text))

    def test_actual_counter_is_used_and_original_metadata_unchanged(self):
        chunk = make_chunk("가나다", {"token_check": "required", "size_exception": True}, "D1", 0)
        output = enforce_token_limit(chunk, lambda text: 7, 7)
        self.assertEqual(output[0].metadata["token_count"], 7)
        self.assertEqual(output[0].metadata["token_check"], "passed")
        self.assertEqual(chunk.metadata["token_check"], "required")

    def test_long_cell_splits_sentences_repeats_context_and_rechecks(self):
        sentences = [f"설명{i} " + "가" * 20 + "." for i in range(5)]
        text = "## 샘플카드\n전월 30만원 조건.\n| 항목 | 설명 |\n| --- | --- |\n| 할인 | " + " ".join(sentences) + " |"
        candidate = chunk_by_clause(text, {"doc_key": "D2"}, 100, 0)[0]
        output = enforce_token_limit(candidate, self.count, 125)
        self.assertGreater(len(output), 1)
        self.assertEqual(len({c.chunk_id for c in output}), len(output))
        for chunk in output:
            self.assertLessEqual(self.count(chunk.text), 125)
            self.assertIn("## 샘플카드", chunk.text)
            self.assertIn("전월 30만원 조건.", chunk.text)
            self.assertIn("| 할인 |", chunk.text)
            self.assertEqual(chunk.metadata["token_check"], "passed")
            self.assertEqual(chunk.metadata["char_len"], len(chunk.text))
        for sentence in sentences:
            self.assertEqual(sum(sentence in c.text for c in output), 1)

    def test_attribute_long_description_repeats_other_conditions(self):
        text = ("## 카드\n| 항목 | 합성 조건 |\n| --- | --- |\n| 혜택 설명 | " +
                " ".join(f"설명{i} " + "가" * 20 + "." for i in range(6)) + " |\n" +
                "| 실적 조건 | 30만원 이상 |\n| 제외 조건 | 세금 제외 |")
        chunk = chunk_by_clause(text, {"doc_key": "D2"}, 100, 0)[0]
        output = enforce_token_limit(chunk, self.count, 150)
        self.assertGreater(len(output), 1)
        for part in output:
            self.assertIn("| 실적 조건 | 30만원 이상 |", part.text)
            self.assertIn("| 제외 조건 | 세금 제외 |", part.text)
            self.assertLessEqual(part.metadata["token_count"], 150)

    def test_long_unsplittable_sentence_requires_review(self):
        text = "## 카드\n| 항목 | 설명 |\n| --- | --- |\n| 할인 | " + "가" * 150 + " |"
        chunk = chunk_by_clause(text, {"doc_key": "D2"}, 100, 0)[0]
        with self.assertRaisesRegex(ValueError, "문장 경계"):
            enforce_token_limit(chunk, self.count, 100)

    def test_mandatory_conditions_exceed_limit_requires_review(self):
        text = "## 카드\n| 항목 | 합성 조건 |\n| --- | --- |\n| 실적 조건 | " + "조건. " * 50 + " |"
        chunk = chunk_by_clause(text, {"doc_key": "D2"}, 100, 0)[0]
        with self.assertRaisesRegex(ValueError, "필수 조건"):
            enforce_token_limit(chunk, self.count, 100)

    def test_bad_counter_and_limit_rejected(self):
        chunk = make_chunk("내용", {}, "D1", 0)
        for counter, limit in [(None, 1), (lambda _: -1, 10), (lambda _: 1.5, 10), (self.count, 0)]:
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                enforce_token_limit(chunk, counter, limit)


if __name__ == "__main__":
    unittest.main()
