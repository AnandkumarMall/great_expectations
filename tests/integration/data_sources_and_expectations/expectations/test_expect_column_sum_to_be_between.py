from typing import Any, Dict, cast

import pandas as pd
import pytest

import great_expectations.expectations as gxe
from great_expectations.core.result_format import ResultFormat
from great_expectations.datasource.fluent.interfaces import Batch
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.data_sources_and_expectations.test_canonical_expectations import (
    ALL_DATA_SOURCES,
    JUST_PANDAS_DATA_SOURCES,
)

COL_NAME = "my_col"

DATA = pd.DataFrame({COL_NAME: [0, -1, 1, 2, 100, 9000, -1, -40, -60, None, None]}, dtype="object")


@parameterize_batch_for_data_sources(data_source_configs=ALL_DATA_SOURCES, data=DATA)
def test_its_over_9000(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectColumnSumToBeBetween(column=COL_NAME, min_value=9001, max_value=9001)
    result = batch_for_datasource.validate(expectation, result_format=ResultFormat.COMPLETE)
    assert result.success
    assert result.to_json_dict()["result"] == {"observed_value": 9001}


@pytest.mark.parametrize(
    "expectation",
    [
        pytest.param(
            gxe.ExpectColumnSumToBeBetween(column=COL_NAME),
            id="vacuous_truth",
        ),
        pytest.param(
            gxe.ExpectColumnSumToBeBetween(column=COL_NAME, min_value=9000),
            id="no_max",
        ),
        pytest.param(
            gxe.ExpectColumnSumToBeBetween(column=COL_NAME, max_value=9002),
            id="no_min",
        ),
        pytest.param(
            gxe.ExpectColumnSumToBeBetween(
                column=COL_NAME, min_value=9000, max_value=9002, strict_min=True, strict_max=True
            ),
            id="stict_bounds",
        ),
    ],
)
@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_success(batch_for_datasource: Batch, expectation: gxe.ExpectColumnSumToBeBetween) -> None:
    result = batch_for_datasource.validate(expectation)
    assert result.success


@pytest.mark.parametrize(
    "expectation",
    [
        pytest.param(
            gxe.ExpectColumnSumToBeBetween(column=COL_NAME, min_value=9002, max_value=9002),
            id="bad_range",
        ),
        pytest.param(
            gxe.ExpectColumnSumToBeBetween(column=COL_NAME, min_value=9001, strict_min=True),
            id="strict_min",
        ),
        pytest.param(
            gxe.ExpectColumnSumToBeBetween(column=COL_NAME, max_value=9001, strict_max=True),
            id="strict_max",
        ),
    ],
)
@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_failure(batch_for_datasource: Batch, expectation: gxe.ExpectColumnSumToBeBetween) -> None:
    result = batch_for_datasource.validate(expectation)
    assert not result.success


@pytest.mark.parametrize(
    "suite_param_value,expected_result",
    [
        pytest.param(True, True, id="success"),
    ],
)
@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_success_with_suite_param_strict_min_(
    batch_for_datasource: Batch, suite_param_value: bool, expected_result: bool
) -> None:
    suite_param_key = "test_expect_column_sum_to_be_between"
    expectation = gxe.ExpectColumnSumToBeBetween(
        column=COL_NAME,
        min_value=9000,
        max_value=9002,
        strict_min={"$PARAMETER": suite_param_key},
        result_format=ResultFormat.SUMMARY,
    )
    result = batch_for_datasource.validate(
        expectation, expectation_parameters={suite_param_key: suite_param_value}
    )
    assert result.success == expected_result


@pytest.mark.parametrize(
    "suite_param_value,expected_result",
    [
        pytest.param(True, True, id="success"),
    ],
)
@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_success_with_suite_param_strict_max_(
    batch_for_datasource: Batch, suite_param_value: bool, expected_result: bool
) -> None:
    suite_param_key = "test_expect_column_sum_to_be_between"
    expectation = gxe.ExpectColumnSumToBeBetween(
        column=COL_NAME,
        min_value=9000,
        max_value=9002,
        strict_max={"$PARAMETER": suite_param_key},
        result_format=ResultFormat.SUMMARY,
    )
    result = batch_for_datasource.validate(
        expectation, expectation_parameters={suite_param_key: suite_param_value}
    )
    assert result.success == expected_result


@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_include_unexpected_rows(batch_for_datasource: Batch) -> None:
    """Test that include_unexpected_rows works correctly for ExpectColumnSumToBeBetween."""
    expectation = gxe.ExpectColumnSumToBeBetween(column=COL_NAME, min_value=10, max_value=20)
    result = batch_for_datasource.validate(
        expectation, result_format={"result_format": "BASIC", "include_unexpected_rows": True}
    )

    assert not result.success
    result_dict = cast("Dict[str, Any]", result.to_json_dict()["result"])

    # Verify that unexpected_rows is present and contains the expected data
    assert "unexpected_rows" in result_dict
    assert result_dict["unexpected_rows"] is not None

    # Convert to DataFrame for easier comparison
    unexpected_rows_data = result_dict["unexpected_rows"]
    assert isinstance(unexpected_rows_data, list)
    unexpected_rows_df = pd.DataFrame(unexpected_rows_data)

    # Should contain rows that don't meet the expectation
    assert len(unexpected_rows_df) > 0

    # Check that the unexpected rows contain the expected columns
    assert COL_NAME in unexpected_rows_df.columns
