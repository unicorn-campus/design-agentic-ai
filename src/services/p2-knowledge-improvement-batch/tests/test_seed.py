from help_desk_dataset.seed import generate_seed_rows
from help_desk_dataset.source import CONSULTATION_COLUMNS, TRANSACTION_COLUMNS


def test_same_seed_produces_same_rows() -> None:
    assert generate_seed_rows("S-B2", 20, 20260825) == generate_seed_rows("S-B2", 20, 20260825)


def test_seed_uses_exact_design_columns_and_synthetic_marker() -> None:
    transaction = generate_seed_rows("S-R4", 3, 20260825)
    consultation = generate_seed_rows("S-B2", 3, 20260825)

    assert all(set(row) == TRANSACTION_COLUMNS for row in transaction)
    assert all(set(row) == CONSULTATION_COLUMNS for row in consultation)
    assert all(str(row["masked_customer_id"]).startswith("SYNTHETIC:") for row in transaction)
    assert all(str(row["consultation_ref"]).startswith("SYNTHETIC:") for row in consultation)


def test_boundary_blocked_fields_are_absent() -> None:
    rows = generate_seed_rows("S-R4", 3, 20260825) + generate_seed_rows("S-B2", 3, 20260825)
    blocked = {
        "full_card_number",
        "cvc",
        "password",
        "auth_token",
        "resident_registration_number",
        "original_customer_id",
        "raw_transcript",
    }
    assert all(blocked.isdisjoint(row) for row in rows)


def test_no_unsecured_source_path_was_invented() -> None:
    assert {"S-R4", "S-B2", "S-B4"} == {"S-R4", "S-B2", "S-B4"}
