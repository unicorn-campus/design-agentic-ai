"""상담 분리와 가명화 완료 조건 시험."""

from __future__ import annotations

import json
import unittest

from app.domain.consultations import EMAIL, MEMBER, PAN, PHONE, parse_consultations


SAMPLE_CONSULTATION = """[상담ID] C-20260314-001 | 2026-03-14 | 채널: 앱 채팅 | 회원번호: M-1001
[기록정보] 문서종류: consult_log | 공개등급: restricted | 작성일: 2026-03-14 | 소관부서: customer_service | 버전: v2
[접수정보] 고객명: 가상고객0001 | 전화: 010-0000-0001 | 이메일: customer0001@example.invalid | 상담사명: 가상상담사02
[본인확인] 가상 카드번호: 0000-0000-0001-0017 | 끝 4자리: 0017 | 생년월일: 1991-01-02 | 나이: 만 35세
[상담주제] 가상고객0001의 앱 인증 불편
고객: 가상고객0001입니다. 전화 010-0000-0001로 알려 주세요.
상담사: 고객님 이메일 customer0001@example.invalid은 확인하지 않겠습니다.
"""


class ConsultationParserTests(unittest.TestCase):
    def test_parser_returns_a_pseudonymized_consultation(self) -> None:
        document = parse_consultations(SAMPLE_CONSULTATION, "D3_S01.txt")[0]
        serialized = json.dumps(
            {"page_content": document.page_content, "metadata": document.metadata},
            ensure_ascii=False,
        )

        self.assertTrue(document.metadata["pseudonymized"])
        self.assertNotIn("member_id", document.metadata)
        self.assertTrue(document.metadata["member_pseudo_id"].startswith("m_"))
        self.assertTrue(document.metadata["agent_pseudo_id"].startswith("a_"))
        self.assertFalse(any(pattern.search(serialized) for pattern in (PHONE, EMAIL, PAN, MEMBER)))


if __name__ == "__main__":
    unittest.main()
