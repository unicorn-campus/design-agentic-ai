import unittest

from lab_io import normalize_table, prepare_units, validate_documents


def document(text, page, kind='regulation', **extra):
    return {'page_content': text, 'metadata': {
        'source': 'D1_test.pdf' if kind == 'regulation' else 'D2_test.pdf',
        'doc_type': kind, 'page': page, 'created_at': '2026-09-09', 'version': '1',
        'owner_dept': 'product_planning', 'access_level': 'public', **extra}}


class InputTests(unittest.TestCase):
    def test_clause_continues_across_pages(self):
        rows = [document('제1조(목적)\n(1) 시작', 1), document('계속되는 조건\n제2조(정의)\n다음', 2)]
        units, _ = prepare_units(rows)
        self.assertEqual(len(units), 2)
        self.assertIn('계속되는 조건', units[0]['text'])
        self.assertEqual(units[0]['meta']['page_end'], 2)
        self.assertEqual(units[0]['meta']['page'], 1)

    def test_contents_excluded(self):
        units, skipped = prepare_units([document('제1조(목적)', 1, section_kind='contents'),
                                        document('제1조(목적)\n본문', 2)])
        self.assertEqual(len(units), 1)
        self.assertEqual(len(skipped), 1)

    def test_card_context_survives_page_change(self):
        rows = [document('D2-C001\n한빛 예시\n시행일 2027-01-15\n연회비\n브랜드 | 금액\n국내 | 100',
                         1, 'benefit_guide'),
                document('D2-C001-B01 | 할인\n항목 | 조건\n실적 | 세금은\n제외함.\n모든 명칭은 합성',
                         2, 'benefit_guide')]
        units, _ = prepare_units(rows)
        self.assertIn('한빛 예시', units[1]['text'])
        self.assertIn('| 실적 | 세금은 제외함. |', units[1]['text'])
        self.assertEqual(units[1]['meta']['page'], 2)

    def test_duplicate_page_rejected(self):
        row = document('본문', 1)
        with self.assertRaises(ValueError):
            validate_documents([row, row])

    def test_benefit_footer_continues_on_next_page(self):
        rows = [document('D2-C001\n한빛 예시\n시행일 2027\n연회비\n브랜드 | 금액\n국내 | 100\n'
                         'D2-C001-B01 | 할인\n항목 | 조건\n혜택 | 1%', 1, 'benefit_guide'),
                document('일반 혜택은 중복 불가\nD2-C001-B02 | 적립\n항목 | 조건\n혜택 | 2%',
                         2, 'benefit_guide')]
        units, skipped = prepare_units(rows)
        self.assertIn('일반 혜택은 중복 불가', units[1]['text'])
        self.assertEqual(units[1]['meta']['page_end'], 2)
        self.assertEqual(skipped, [])

    def test_matching_footnotes_are_attached(self):
        rows = [document('제1조(환산)\n가상 환율임.**\n제2조(기타)\n본문', 1),
                document('각주와 출처\n* 다른 각주\n** 환산 조건 각주', 2)]
        units, _ = prepare_units(rows)
        self.assertIn('** 환산 조건 각주', units[0]['text'])
        self.assertNotIn('* 다른 각주', units[0]['text'])
        self.assertEqual(units[0]['meta']['footnote_page'], 2)

    def test_unpseudonymized_consultation_rejected(self):
        row = document('고객: 질문', 1, 'consult_log', record_id='test')
        with self.assertRaises(ValueError):
            validate_documents([row])


if __name__ == '__main__':
    unittest.main()
