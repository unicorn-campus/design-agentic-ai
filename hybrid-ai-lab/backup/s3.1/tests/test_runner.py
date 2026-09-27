import contextlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

from run_chunking import main


class RunnerTests(unittest.TestCase):
    def test_exception_kept_for_review_without_tokenizer(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / 'documents.jsonl'
            source.write_text(json.dumps({
                'page_content': '제1조(표)\n| 항목 | 설명 |\n| --- | --- |\n| 예시 | ' + '긴설명' * 230 + ' |',
                'metadata': {'source': 'D1_test.pdf', 'doc_type': 'regulation', 'page': 1,
                             'created_at': '2026-09-10', 'version': '1', 'owner_dept': 'test',
                             'access_level': 'public'}}, ensure_ascii=False), encoding='utf8')
            out = root / 'out'
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(['--input', str(source), '--output', str(out)])
            self.assertEqual(code, 2)
            exception = json.loads((out / 'exceptions.jsonl').read_text(encoding='utf8'))
            self.assertTrue(exception['metadata']['size_exception'])
            self.assertGreater(exception['metadata']['char_len'], 600)
            self.assertEqual((out / 'chunks.jsonl').read_text(encoding='utf8'), '')
            self.assertIn('긴설명', (out / 'review.jsonl').read_text(encoding='utf8'))
            if importlib.util.find_spec('tokenizers'):
                # 동작 검사 전용 인공 토크나이저임. 실제 임베딩 모델 결과로 보고하지 않음.
                from tokenizers import Tokenizer, models, pre_tokenizers
                tokenizer = Tokenizer(models.WordLevel({'[UNK]': 0}, unk_token='[UNK]'))
                tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
                path = root / 'test-tokenizer.json'
                tokenizer.save(str(path))
                with contextlib.redirect_stdout(io.StringIO()):
                    code = main(['--input', str(source), '--output', str(out),
                                 '--tokenizer-json', str(path), '--max-input-tokens', '100'])
                self.assertEqual(code, 0)
                chunk = json.loads((out / 'chunks.jsonl').read_text(encoding='utf8'))
                self.assertEqual(chunk['metadata']['token_check'], 'passed')
                self.assertLessEqual(chunk['metadata']['token_count'], 100)
                self.assertTrue(chunk['metadata']['size_exception'])


if __name__ == '__main__':
    unittest.main()
