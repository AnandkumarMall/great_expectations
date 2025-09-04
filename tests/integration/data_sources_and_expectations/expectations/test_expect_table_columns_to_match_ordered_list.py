from typing import Any, Dict, cast

import pandas as pd
import pytest

import great_expectations.expectations as gxe
from great_expectations.datasource.fluent.interfaces import Batch
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.data_sources_and_expectations.test_canonical_expectations import (
    ALL_DATA_SOURCES,
    JUST_PANDAS_DATA_SOURCES,
)

COL_A = "col_a"
COL_B = "col_b"
COL_C = "col_c"


DATA = pd.DataFrame(
    {
        COL_A: [1],
        COL_B: [2],
        COL_C: [3],
    }
)


@parameterize_batch_for_data_sources(data_source_configs=ALL_DATA_SOURCES, data=DATA)
def test_golden_path(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectTableColumnsToMatchOrderedList(column_list=[COL_A, COL_B, COL_C])
    result = batch_for_datasource.validate(expectation)
    assert result.success


@pytest.mark.parametrize(
    "expectation",
    [
        pytest.param(
            gxe.ExpectTableColumnsToMatchOrderedList(column_list=[COL_A, COL_B]),
            id="missing_cols",
        ),
        pytest.param(
            gxe.ExpectTableColumnsToMatchOrderedList(column_list=[COL_A, COL_B, COL_C, "col_d"]),
            id="extra_cols",
        ),
        pytest.param(
            gxe.ExpectTableColumnsToMatchOrderedList(column_list=[COL_A, COL_B, COL_C.upper()]),
            id="wrong_value",
        ),
        pytest.param(
            gxe.ExpectTableColumnsToMatchOrderedList(column_list=[COL_C, COL_B, COL_A]),
            id="wrong_order",
        ),
    ],
)
@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_failure(
    batch_for_datasource: Batch, expectation: gxe.ExpectTableColumnsToMatchOrderedList
) -> None:
    result = batch_for_datasource.validate(expectation)
    assert not result.success


@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_include_unexpected_rows(batch_for_datasource: Batch) -> None:
    """Test include_unexpected_rows for ExpectTableColumnsToMatchOrderedList."""
    expectation = gxe.ExpectTableColumnsToMatchOrderedList(column_list=["wrong_column"])
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
