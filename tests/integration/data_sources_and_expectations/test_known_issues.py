"""
Responsible for highlighting known bugs we're working to resolve.
"""

import pandas as pd

import great_expectations.expectations as gxe
from great_expectations.core.expectation_suite import ExpectationSuite
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.test_utils.data_source_config.pandas_data_frame import (
    PandasDataFrameDatasourceTestConfig,
)
from tests.integration.test_utils.data_source_config.postgres import PostgreSQLDatasourceTestConfig


@parameterize_batch_for_data_sources(
    data_source_configs=[PostgreSQLDatasourceTestConfig()],
    data=pd.DataFrame(
        {
            "col1": [1, 2, 3, 4, 5],
            "col2": ["A", "B", "C", "D", None],
            "col3": [1.1, None, 3.3, 4.4, 5.5],
        }
    ),
)
def test_shared_metric_dependencies_cause_entire_suite_to_fail(batch_for_datasource):
    """
    This test demonstrates the bug where a missing condition_parser causes the entire suite to fail.

    The bug is that the error message from the third expectation is propagated to all subsequent
    expectations.

    This highlights a larger issue where shared metric dependencies can cause issues to propagate
    across expectations. A missing condition parser is simply one example of this issue.

    All expectations here share a dependency on the 'table.row_count' metric.
    """
    suite = ExpectationSuite(
        name="faulty",
        expectations=[
            gxe.ExpectColumnValuesToNotBeNull(column="col1"),
            gxe.ExpectColumnValuesToNotBeNull(column="col2"),
            gxe.ExpectColumnValuesToBeInSet(
                column="col2",
                value_set=["A", "B", "C"],
                row_condition="col3 IS NOT NULL",
                mostly=0.665,
                condition_parser=None,  # Should be specified as 'great_expectations'
            ),
        ],
    )

    result = batch_for_datasource.validate(suite)

    assert result.success is False
    assert all(
        res.success is False
        and "SqlAlchemyExecutionEngine only supports the great_expectations condition_parser."
        in str(res.exception_info)
        for res in result.results
    )


@parameterize_batch_for_data_sources(
    data_source_configs=[PandasDataFrameDatasourceTestConfig()],
    data=pd.DataFrame(
        {
            "col1": [1, 2, 3, 4, 5],
        }
    ),
)
def test_catch_exceptions_is_not_respected(batch_for_datasource):
    """
    This test demonstrates the bug where catch_exceptions is not respected.

    We do not currently have any logic that respects user configuration
    and disables the default value of True.
    """
    expectation = gxe.ExpectColumnValuesToMatchStrftimeFormat(
        column="col1", strftime_format="%Y-%m-%d", catch_exceptions=False
    )
    result = batch_for_datasource.validate(expectation)

    assert result.success is False
    assert "please call the expectation before converting from string format" in str(
        result.exception_info
    )
