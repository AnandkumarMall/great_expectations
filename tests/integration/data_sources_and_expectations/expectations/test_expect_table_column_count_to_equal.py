from typing import Any, Dict, cast

import pandas as pd

import great_expectations.expectations as gxe
from great_expectations.datasource.fluent.interfaces import Batch
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.data_sources_and_expectations.test_canonical_expectations import (
    ALL_DATA_SOURCES,
    JUST_PANDAS_DATA_SOURCES,
)

INT_COL_A = "INT_COL_A"
INT_COL_B = "INT_COL_B"
INT_COL_C = "INT_COL_C"
STRING_COL_A = "STRING_COL_A"
STRING_COL_B = "STRING_COL_B"


DATA = pd.DataFrame(
    {
        INT_COL_A: [1, 1, 2, 3],
        INT_COL_B: [2, 2, 3, 4],
        INT_COL_C: [3, 3, 4, 4],
        STRING_COL_A: ["a", "b", "c", "d"],
        STRING_COL_B: ["x", "y", "z", "a"],
    }
)


@parameterize_batch_for_data_sources(data_source_configs=ALL_DATA_SOURCES, data=DATA)
def test_golden_path(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectTableColumnCountToEqual(value=5)
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_failure(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectTableColumnCountToEqual(value=4)
    result = batch_for_datasource.validate(expectation)
    assert not result.success


@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_include_unexpected_rows(batch_for_datasource: Batch) -> None:
    """Test that include_unexpected_rows works correctly for ExpectTableColumnCountToEqual."""
    expectation = gxe.ExpectTableColumnCountToEqual(value=1)
    result = batch_for_datasource.validate(
        expectation, result_format={"result_format": "BASIC", "include_unexpected_rows": True}
    )

    # Table expectations may succeed or fail, so we check for unexpected_rows regardless
    result_dict = cast("Dict[str, Any]", result.to_json_dict()["result"])

    # Verify that unexpected_rows is present (may be empty for table-level expectations)
    assert "unexpected_rows" in result_dict

    # Table expectations typically don't populate unexpected_rows the same way,
    # but we verify the key exists for consistency
    # unexpected_rows may be None or an empty list for table-level expectations
    unexpected_rows_data = result_dict.get("unexpected_rows")
    if unexpected_rows_data is not None:
        assert isinstance(unexpected_rows_data, list)
