from datetime import datetime

import pandas as pd
import pytest

import great_expectations.expectations as gxe
from great_expectations.core.result_format import ResultFormat
from great_expectations.datasource.fluent.interfaces import Batch
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.data_sources_and_expectations.test_canonical_expectations import (
    ALL_DATA_SOURCES,
    DATA_SOURCES_THAT_SUPPORT_DATE_COMPARISONS,
    JUST_PANDAS_DATA_SOURCES,
)

COL_NAME = "my_col"

ONES_AND_TWOS = pd.DataFrame({COL_NAME: [1, 2, 2, 2]})


@parameterize_batch_for_data_sources(data_source_configs=ALL_DATA_SOURCES, data=ONES_AND_TWOS)
def test_success_complete_results(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(column=COL_NAME, value_set=[1, 2])
    result = batch_for_datasource.validate(expectation, result_format=ResultFormat.COMPLETE)
    assert result.success
    assert result.to_json_dict()["result"] == {
        "details": {
            "value_counts": [
                {"value": 1, "count": 1},
                {"value": 2, "count": 3},
            ]
        },
        "observed_value": [1, 2],
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
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(
        column=COL_NAME,
        value_set=[str(datetime(2024, 11, 19).date()), str(datetime(2024, 11, 20).date())],  # noqa: DTZ001 # FIXME CoP
    )
    result = batch_for_datasource.validate(expectation)
    assert result.success


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


@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ONES_AND_TWOS
)
def test_include_unexpected_rows(batch_for_datasource: Batch) -> None:
    """Test include_unexpected_rows for ExpectColumnDistinctValuesToEqualSet."""
    expectation = gxe.ExpectColumnDistinctValuesToEqualSet(
        column=COL_NAME, value_set=["a", "b", "d"]
    )
    result = batch_for_datasource.validate(
        expectation, result_format={"result_format": "BASIC", "include_unexpected_rows": True}
    )

    result_dict = result.to_json_dict()["result"]

    # Verify that unexpected_rows is present (may be empty list for successful expectations)
    assert "unexpected_rows" in result_dict
    assert result_dict["unexpected_rows"] is not None

    # Convert to DataFrame for easier comparison
    unexpected_rows_data = result_dict["unexpected_rows"]
    assert isinstance(unexpected_rows_data, list)

    # If there are unexpected rows, validate the structure
    if unexpected_rows_data:
        unexpected_rows_df = pd.DataFrame(unexpected_rows_data)
        # Check that the unexpected rows contain some columns
        assert len(unexpected_rows_df.columns) > 0
