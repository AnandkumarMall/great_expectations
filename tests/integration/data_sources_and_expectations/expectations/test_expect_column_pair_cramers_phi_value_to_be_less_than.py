import pandas as pd
import pytest

import great_expectations.expectations as gxe
from great_expectations.core.result_format import ResultFormat
from great_expectations.datasource.fluent.interfaces import Batch
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.data_sources_and_expectations.test_canonical_expectations import (
    JUST_PANDAS_DATA_SOURCES,
)

# This Expectation builds a contingency table with pandas and computes Cramér's phi with scipy, so
# it is exercised against the Pandas data source only.

COL_A = "col_a"
COL_B = "col_b"

# Independent columns: every combination of (A/B) x (X/Y) appears equally often -> phi == 0.
INDEPENDENT_DATA = pd.DataFrame(
    {
        COL_A: ["A", "A", "B", "B"] * 25,
        COL_B: ["X", "Y", "X", "Y"] * 25,
    }
)

# Perfectly associated columns: col_b is fully determined by col_a -> phi near 1.
ASSOCIATED_DATA = pd.DataFrame(
    {
        COL_A: ["A"] * 50 + ["B"] * 50,
        COL_B: ["X"] * 50 + ["Y"] * 50,
    }
)


@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=INDEPENDENT_DATA
)
def test_success(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectColumnPairCramersPhiValueToBeLessThan(
        column_A=COL_A, column_B=COL_B, threshold=0.1
    )
    result = batch_for_datasource.validate(expectation, result_format=ResultFormat.COMPLETE)
    assert result.success
    assert result.to_json_dict()["result"] == {
        "observed_value": pytest.approx(0.0),
        "details": {
            "crosstab": {
                "row_variable": "col_a",
                "column_variable": "col_b",
                "rows": ["A", "B"],
                "columns": ["X", "Y"],
                "counts": [[25, 25], [25, 25]],
            }
        },
    }


@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ASSOCIATED_DATA
)
def test_failure(batch_for_datasource: Batch) -> None:
    expectation = gxe.ExpectColumnPairCramersPhiValueToBeLessThan(
        column_A=COL_A, column_B=COL_B, threshold=0.1
    )
    result = batch_for_datasource.validate(expectation, result_format=ResultFormat.COMPLETE)
    assert not result.success
    assert result.to_json_dict()["result"] == {
        "observed_value": pytest.approx(0.98),
        "details": {
            "crosstab": {
                "row_variable": "col_a",
                "column_variable": "col_b",
                "rows": ["A", "B"],
                "columns": ["X", "Y"],
                "counts": [[50, 0], [0, 50]],
            }
        },
    }


@pytest.mark.parametrize(
    "suite_param_value,expected_result",
    [
        pytest.param(0.999, True, id="success"),
        pytest.param(0.1, False, id="failure"),
    ],
)
@parameterize_batch_for_data_sources(
    data_source_configs=JUST_PANDAS_DATA_SOURCES, data=ASSOCIATED_DATA
)
def test_success_with_suite_param_threshold_(
    batch_for_datasource: Batch, suite_param_value: float, expected_result: bool
) -> None:
    suite_param_key = "expect_column_pair_cramers_phi_value_to_be_less_than"
    expectation = gxe.ExpectColumnPairCramersPhiValueToBeLessThan(
        column_A=COL_A,
        column_B=COL_B,
        threshold={"$PARAMETER": suite_param_key},
        result_format=ResultFormat.SUMMARY,
    )
    result = batch_for_datasource.validate(
        expectation, expectation_parameters={suite_param_key: suite_param_value}
    )
    assert result.success == expected_result
