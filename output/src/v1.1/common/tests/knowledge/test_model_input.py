"""반드시 넣을 시험 7 — 모델에 넘기는 입력 규격에 그 필드가 **없음**.

결정론 필터가 맡은 판정의 원문 필드는 주석으로 「안 씀」이라 적히지 않고 **칸 자체가 없음**임.
"""

from __future__ import annotations

import pytest

from common.knowledge import (
    MODEL_INPUT_KEYS,
    REMOVED_INPUT_FIELDS,
    RemovedFieldPresent,
    UnknownInputField,
    build_model_input,
)

# ④ 「입출력 형식」 `K-6` 10개. 규격이 바뀌면 이 시험이 먼저 깨지게 적어 둠.
EXPECTED_KEYS = (
    "context_tags",
    "region_label",
    "weekday",
    "time_slot",
    "weather_temp_c",
    "recent_menu_names",
    "preference_vector",
    "candidate_places",
    "excluded_ingredient_codes",
    "correlation_key",
)


def test_model_input_keys_match_the_contract() -> None:
    assert MODEL_INPUT_KEYS == EXPECTED_KEYS


@pytest.mark.parametrize("name", sorted(REMOVED_INPUT_FIELDS))
def test_removed_field_has_no_slot_in_the_spec(name: str) -> None:
    """시험 7 — 지운 필드 이름이 규격 칸 목록에 0건임."""
    assert name not in MODEL_INPUT_KEYS


@pytest.mark.parametrize("name", sorted(REMOVED_INPUT_FIELDS))
def test_removed_field_cannot_be_passed(name: str) -> None:
    with pytest.raises(RemovedFieldPresent):
        build_model_input(**{name: "아무 값"})


def test_allergen_label_slot_is_gone_and_code_slot_remains() -> None:
    """알레르겐 원문 라벨 칸은 없고 제외 식재료 코드 칸만 있음."""
    assert "allergyItems" not in MODEL_INPUT_KEYS
    assert "allergen_labels" not in MODEL_INPUT_KEYS
    assert "excluded_ingredient_codes" in MODEL_INPUT_KEYS


def test_unknown_name_is_refused() -> None:
    with pytest.raises(UnknownInputField):
        build_model_input(brand_new_key="아무 값")


def test_build_keeps_only_given_contract_keys() -> None:
    built = build_model_input(
        region_label="어느 동네",
        excluded_ingredient_codes=["CODE-A"],
        correlation_key="CK-1",
    )
    assert list(built) == ["region_label", "excluded_ingredient_codes", "correlation_key"]


def test_index_payload_also_refuses_removed_fields(embedding_ready, embedder) -> None:
    """색인에 넣는 값에도 지운 필드가 못 들어감."""
    from common.knowledge import build_index

    with pytest.raises(ValueError):
        build_index(
            "food_item",
            [
                {
                    "item_key": "F1",
                    "locator": "음식카드#1",
                    "text": "국물 있는 한식",
                    "metadata": {"category_code": "한식"},
                    "payload": {"nickname": "손님"},
                }
            ],
            embedder,
            settings=embedding_ready,
        )
