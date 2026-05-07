"""Unit tests for the EXPECTATION_CASES table.

Verifies:
  (a) every ``id`` in the table is unique
  (b) every expectation_type covered by ``family_for`` returns 'map' or 'aggregate'
  (c) the case count equals the number of expect_*.py files under core/
"""
from __future__ import annotations

from pathlib import Path

import pytest

from great_expectations.core.validation_result_schemas.dispatcher import (
    family_for,
)
from tests.integration.data_sources_and_expectations.expectations._validation_result_schemas_cases import (  # noqa: E501
    EXPECTATION_CASES,
)


@pytest.mark.unit
def test_case_ids_are_unique() -> None:
    ids = [c.id for c in EXPECTATION_CASES]
    assert len(ids) == len(set(ids)), (
        f"Duplicate ids: {sorted(i for i in ids if ids.count(i) > 1)}"
    )


@pytest.mark.unit
def test_all_expectation_types_in_family_table() -> None:
    for case in EXPECTATION_CASES:
        exp_type = case.expectation.expectation_type
        family = family_for(exp_type)
        assert family in ("map", "aggregate"), (
            f"{exp_type!r} returned unexpected family {family!r}"
        )


@pytest.mark.unit
def test_case_count_matches_core_expectations() -> None:
    core_dir = (
        Path(__file__).parent / ".." / ".." / ".." / ".."
        / "great_expectations" / "expectations" / "core"
    )
    core_files = list(core_dir.glob("expect_*.py"))
    expected_count = len(
        [f for f in core_files if not f.name.startswith("__")]
    )
    assert len(EXPECTATION_CASES) == expected_count, (
        f"Expected {expected_count} cases, got {len(EXPECTATION_CASES)}"
    )
