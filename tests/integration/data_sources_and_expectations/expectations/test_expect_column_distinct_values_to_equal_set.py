from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Literal

import pandas as pd
import pytest

import great_expectations.expectations as gxe
from great_expectations.core.result_format import ResultFormat
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.data_sources_and_expectations.test_canonical_expectations import (
    ALL_DATA_SOURCES,
    DATA_SOURCES_THAT_SUPPORT_DATE_COMPARISONS,
    JUST_PANDAS_DATA_SOURCES,
)

if TYPE_CHECKING:
    from great_expectations.datasource.fluent.interfaces import Batch

COL_NAME = "my_col"

ONES_AND_TWOS = pd.DataFrame({COL_NAME: [1, 2, 2, 2]})


@parameterize_batch_for_data_sources(data_source_configs=ALL_DATA_SOURCES, data=ONES_AND_TWOS)
def test_success_complete_results(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=[1, 2])
    result = batch_for_datasource.validate(expectation, result_format=ResultFormat.COMPLETE)
    assert result.success
    # BREAKING CHANGE: observed_value now contains only differences (empty when success)
    assert result.to_json_dict()["result"] == {
        "observed_value": [],
    }


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_DATA_SOURCES,
    data=pd.DataFrame({COL_NAME: ["foo", "bar"]}),
)
def test_strings(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(
        column=COL_NAME, value_set=["foo", "bar"]
    )
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=DATA_SOURCES_THAT_SUPPORT_DATE_COMPARISONS,
    data=pd.DataFrame({COL_NAME: [datetime(2024, 11, 19).date(), datetime(2024, 11, 20).date()]}),  # noqa: DTZ001 # FIXME CoP
)
def test_dates(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(
        column=COL_NAME,
        value_set=[datetime(2024, 11, 19).date(), datetime(2024, 11, 20).date()],  # noqa: DTZ001 # FIXME CoP
    )
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=DATA_SOURCES_THAT_SUPPORT_DATE_COMPARISONS,
    data=pd.DataFrame({COL_NAME: [datetime(2024, 11, 19).date(), datetime(2024, 11, 20).date()]}),  # noqa: DTZ001 # FIXME CoP
)
def test_dates_with_str_value_set(batch_for_datasource: Batch) -> None:
    # BREAKING CHANGE: String values are no longer automatically coerced to match date columns.
    # Users should provide value_set with matching types.
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(
        column=COL_NAME,
        value_set=[str(datetime(2024, 11, 19).date()), str(datetime(2024, 11, 20).date())],  # noqa: DTZ001 # FIXME CoP
    )
    result = batch_for_datasource.validate(expectation)
    # Strings don't match date objects, so all dates appear as violations
    assert not result.success


@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=pd.DataFrame({COL_NAME: [1, 2, None]})
)
def test_ignores_nulls(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=[1, 2])
    result = batch_for_datasource.validate(expectation)
    assert result.success


@pytest.mark.parametrize("value_set", [[1], [1, 4], [1, 2, 3]])
@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ONES_AND_TWOS
)
def test_fails_if_data_is_not_equal(batch_for_datasource: Batch, value_set: list[int]) -> None:
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=value_set)
    result = batch_for_datasource.validate(expectation)
    assert not result.success


# Result format tests


@pytest.mark.parametrize(
    "result_format,expected_result_keys",
    [
        pytest.param("BOOLEAN_ONLY", set(), id="boolean_only"),
        pytest.param("BASIC", {"observed_value"}, id="basic"),
        pytest.param("SUMMARY", {"observed_value"}, id="summary"),
        pytest.param("COMPLETE", {"observed_value"}, id="complete"),
    ],
)
@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ONES_AND_TWOS
)
def test_result_format_success(
    batch_for_datasource: Batch,
    result_format: Literal["BOOLEAN_ONLY", "BASIC", "SUMMARY", "COMPLETE"],
    expected_result_keys: set[str],
) -> None:
    """Test that result format controls what's included in the result on success."""
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=[1, 2])
    result = batch_for_datasource.validate(expectation, result_format=result_format)

    assert result.success

    if result_format == "BOOLEAN_ONLY":
        assert result.result == {}
    else:
        assert set(result.result.keys()) == expected_result_keys
        # BREAKING CHANGE: observed_value now contains only differences (empty when success)
        assert result.result["observed_value"] == []


@pytest.mark.parametrize(
    "result_format,expected_result_keys",
    [
        pytest.param("BOOLEAN_ONLY", set(), id="boolean_only"),
        pytest.param("BASIC", {"observed_value", "unexpected_count", "details"}, id="basic"),
        pytest.param("SUMMARY", {"observed_value", "unexpected_count", "details"}, id="summary"),
        pytest.param("COMPLETE", {"observed_value", "unexpected_count", "details"}, id="complete"),
    ],
)
@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ONES_AND_TWOS
)
def test_result_format_failure(
    batch_for_datasource: Batch,
    result_format: Literal["BOOLEAN_ONLY", "BASIC", "SUMMARY", "COMPLETE"],
    expected_result_keys: set[str],
) -> None:
    """Test that result format controls what's included in the result on failure."""
    # value_set [1] doesn't include 2 which is in column
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=[1])
    result = batch_for_datasource.validate(expectation, result_format=result_format)

    assert not result.success

    if result_format == "BOOLEAN_ONLY":
        assert result.result == {}
    else:
        assert set(result.result.keys()) == expected_result_keys
        # BREAKING CHANGE: observed_value now contains only differences (2 is in column not in set)
        assert result.result["observed_value"] == [2]
        # Verify unexpected_count reflects the number of violations (2 is extra in column)
        assert result.result["unexpected_count"] == 1


@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ONES_AND_TWOS
)
def test_failure_complete_results(batch_for_datasource: Batch) -> None:
    """Test COMPLETE result format on failure."""
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=[1])
    result = batch_for_datasource.validate(expectation, result_format=ResultFormat.COMPLETE)

    assert not result.success

    # BREAKING CHANGE: observed_value now contains only differences
    # Details now show in_column_not_in_set and in_set_not_in_column
    assert result.to_json_dict()["result"] == {
        "observed_value": [2],
        "unexpected_count": 1,
        "details": {
            "in_column_not_in_set": [2],
            "in_set_not_in_column": [],
        },
    }


@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ONES_AND_TWOS
)
def test_failure_missing_from_set(batch_for_datasource: Batch) -> None:
    """Test failure when column is missing values from the expected set."""
    # value_set requires [1, 2, 3] but column only has [1, 2]
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=[1, 2, 3])
    result = batch_for_datasource.validate(expectation, result_format=ResultFormat.COMPLETE)

    assert not result.success

    # BREAKING CHANGE: observed_value now contains only differences (3 is missing)
    assert result.result["observed_value"] == [3]
    # Check unexpected_count: 3 is missing from column
    assert result.result["unexpected_count"] == 1
    # Check details
    assert result.result["details"] == {
        "in_column_not_in_set": [],
        "in_set_not_in_column": [3],
    }


@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ONES_AND_TWOS
)
def test_failure_both_extra_and_missing(batch_for_datasource: Batch) -> None:
    """Test failure when column has extra values AND set has extra values."""
    # value_set [1, 3] - column has 2 (extra) and is missing 3
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=[1, 3])
    result = batch_for_datasource.validate(expectation, result_format=ResultFormat.COMPLETE)

    assert not result.success

    # BREAKING CHANGE: observed_value now contains all differences
    assert sorted(result.result["observed_value"]) == [2, 3]
    # Check unexpected_count: 2 (extra in column) + 3 (missing from column)
    assert result.result["unexpected_count"] == 2
    # Check details
    assert result.result["details"] == {
        "in_column_not_in_set": [2],
        "in_set_not_in_column": [3],
    }
