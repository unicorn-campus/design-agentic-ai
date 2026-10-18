"""문서 탐색과 상담 기록 로딩의 개인정보 경계를 검증함."""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

from app.infrastructure.loaders import ConfiguredDocumentLoader, FileSystemSourceCatalog


def _configs(tmp_path: Path) -> tuple[Path, Path]:
    """상담 문서만 읽는 최소 정책·프로필 설정을 임시 경로에 생성함."""
    policies = tmp_path / "policies.json"
    profiles = tmp_path / "profiles.json"
    policies.write_text(
        json.dumps(
            {
                "documents": {
                    "D3": {
                        "file_regex": "^D3_S\\d{2}_.*\\.txt$",
                        "doc_type": "consult_log",
                        "access_level": "restricted",
                        "separators": ["\\n", " ", ""],
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    profiles.write_text(
        json.dumps({"documents": {"D3": {"owner_dept": "customer_service"}}}),
        encoding="utf-8",
    )
    return policies, profiles


def test_consultation_loader_returns_pseudonymized_text_before_chunking(tmp_path: Path) -> None:
    """상담 로더가 청킹 전에 구조 필드 줄을 지우고 개인정보를 치환한 본문만 돌려줌을 보증함."""
    policies, profiles = _configs(tmp_path)
    source_file = tmp_path / "D3_S02_test.txt"
    source_file.write_text(
        """========================================
[상담ID] C-20260302-001 | 2026-03-02 | 채널: 콜센터 | 회원번호: M-1042
[기록정보] 문서종류: consult_log | 공개등급: restricted
[접수정보] 고객명: 가상고객0042 | 전화: 010-0000-0042 | 이메일: customer0042@example.invalid | 상담사명: 가상상담사19
[본인확인] 가상 카드번호: 0000-0000-0042-0714 | 끝 4자리: 0714 | 생년월일: 1971-01-15 | 나이: 만 55세
[상담주제] 연회비 대비 가치
고객: 제 이름은 가상고객0042입니다.
상담사: 요청을 확인했습니다.
""",
        encoding="utf-8",
    )

    sources = FileSystemSourceCatalog(policies).discover(str(tmp_path), "D3", 2)
    assert len(sources) == 1
    assert sources[0].sha256 == sha256(source_file.read_bytes()).hexdigest()

    documents = ConfiguredDocumentLoader(policies, profiles).load(sources[0])
    assert len(documents) == 1
    document = documents[0]
    for private in ("가상고객0042", "010-0000-0042", "customer0042@example.invalid", "M-1042", "가상상담사19", "1971-01-15"):
        assert private not in document.text
    assert "[상담ID]" not in document.text and "[접수정보]" not in document.text
    assert document.text.startswith("고객: 제 이름은 [삭제]입니다.")
    assert document.pseudonymized is True
    assert document.context_spans[0].end == len(document.text)
    assert document.metadata["member_pseudo_id"] == "m_59853c3d8e1e3c25"
    assert document.metadata["record_id"] == "C-20260302-001"


def test_consultation_loader_removes_spoken_birth_date_but_keeps_business_dates(tmp_path: Path) -> None:
    """발화 속 한글 표기 생년월일은 연령대로 바꾸고 상담일과 거래월 같은 업무 날짜는 남김을 보증함.

    실제 D3 원문 12건에서 "기록 대조용 생일은 1971년 1월 15일이고"처럼 말한 생일이 정제 뒤에도 남았던 회귀 사례임.
    """
    policies, profiles = _configs(tmp_path)
    source_file = tmp_path / "D3_S02_test.txt"
    source_file.write_text(
        """========================================
[상담ID] C-20260302-001 | 2026-03-02 | 채널: 콜센터 | 회원번호: M-1042
[기록정보] 문서종류: consult_log | 공개등급: restricted
[접수정보] 고객명: 가상고객0042 | 전화: 010-0000-0042 | 이메일: customer0042@example.invalid | 상담사명: 가상상담사19
[본인확인] 가상 카드번호: 0000-0000-0042-0714 | 끝 4자리: 0714 | 생년월일: 1971-01-15 | 나이: 만 55세
[상담주제] 연회비 대비 가치
고객: 기록 대조용 생일은 1971년 1월 15일이고 이메일은 customer0042@example.invalid입니다.
상담사: 2026-02 승인 거래는 3건입니다. 2026-01-31 상담과 이어서 보겠습니다.
고객: 다른 기록에는 생년월일: 1971.01.15로 남아 있을 수도 있어요.
""",
        encoding="utf-8",
    )

    source = FileSystemSourceCatalog(policies).discover(str(tmp_path), "D3", 2)[0]
    document = ConfiguredDocumentLoader(policies, profiles).load(source)[0]
    for private in ("1971년 1월 15일", "1971.01.15", "1971-01-15", "customer0042@example.invalid"):
        assert private not in document.text
    assert "생일은 50대이고" in document.text
    assert "2026-02 승인 거래" in document.text and "2026-01-31 상담" in document.text
