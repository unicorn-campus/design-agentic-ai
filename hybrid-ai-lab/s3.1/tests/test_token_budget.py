"""실제 Tokenizers 엔진의 계수 동작 검사. 운영 모델의 정확도 검증은 아님."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

from token_budget import TokenBudget


@unittest.skipUnless(importlib.util.find_spec('tokenizers'), '선택 의존성 tokenizers 미설치')
class TokenBudgetTests(unittest.TestCase):
    def test_saved_truncation_and_padding_are_disabled(self):
        from tokenizers import Tokenizer, models, pre_tokenizers, processors
        tokenizer = Tokenizer(models.WordLevel({'[UNK]': 0, '가': 1, '[CLS]': 2, '[SEP]': 3},
                                                unk_token='[UNK]'))
        tokenizer.pre_tokenizer = pre_tokenizers.Whitespace()
        tokenizer.post_processor = processors.TemplateProcessing(
            single='[CLS] $A [SEP]', special_tokens=[('[CLS]', 2), ('[SEP]', 3)])
        tokenizer.enable_truncation(max_length=4)
        tokenizer.enable_padding(length=20)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'tokenizer.json'
            tokenizer.save(str(path))
            budget = TokenBudget(path, 10, prefix='가 ')
            self.assertEqual(budget.count('가 가 가 가 가'), 8)
            self.assertEqual(budget.count('가'), 4)
            self.assertEqual(len(budget.sha256), 64)


if __name__ == '__main__':
    unittest.main()
