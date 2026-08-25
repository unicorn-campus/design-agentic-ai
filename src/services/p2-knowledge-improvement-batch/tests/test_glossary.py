import logging
from pathlib import Path

from help_desk_dataset.glossary import load_glossary


GLOSSARY_FILE = Path(__file__).resolve().parents[1] / "config" / "glossaries" / "카드업무용어.toml"


def test_glossary_returns_original_and_canonical_term() -> None:
    glossary = load_glossary(GLOSSARY_FILE)
    result = glossary.normalize("결제거절")

    assert result.original == "결제거절"
    assert result.canonical_terms == ("이용거절",)


def test_one_to_many_alias_is_exposed_as_conflict() -> None:
    result = load_glossary(GLOSSARY_FILE).normalize("승인")

    assert result.canonical_terms == ("거래승인", "검토승인")
    assert result.status == "보류·경고"


def test_unknown_term_leaves_one_log(caplog) -> None:
    glossary = load_glossary(GLOSSARY_FILE)
    with caplog.at_level(logging.WARNING):
        result = glossary.normalize("새로운낱말")

    assert result.original == "새로운낱말"
    assert result.canonical_terms == ()
    assert result.status == "보류큐 적재"
    assert [record.message for record in caplog.records].count("glossary_unknown_term") == 1
