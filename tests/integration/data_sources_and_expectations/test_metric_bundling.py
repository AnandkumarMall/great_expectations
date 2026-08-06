"""Tests for validating suites whose expectations share an underlying metric.

The SQL execution engine bundles the metrics required by a suite into as few
queries as possible. Two expectations on different columns can resolve to the
same metric name, so the bundled query needs to give each one a distinct
column alias; backends that reject duplicate output column names fail to
compile the query otherwise.
"""

import pandas as pd

import great_expectations.expectations as gxe
from great_expectations.core.expectation_suite import ExpectationSuite
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.test_utils.data_source_config import (
    BigQueryDatasourceTestConfig,
)


@parameterize_batch_for_data_sources(
    data_source_configs=[BigQueryDatasourceTestConfig()],
    data=pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]}),
)
def test_expectations_sharing_a_metric_are_bundled_into_one_query(batch_for_datasource) -> None:
    """Expectations that resolve to the same metric must not collide when bundled.

    Each of these expectations resolves to column_values.nonnull.unexpected_count,
    so all three land in a single bundled query against the same domain.
    """
    suite = ExpectationSuite(
        name="expectations_sharing_a_metric",
        expectations=[
            gxe.ExpectColumnValuesToNotBeNull(column="a"),
            gxe.ExpectColumnValuesToNotBeNull(column="b"),
            gxe.ExpectColumnValuesToNotBeNull(column="c"),
        ],
    )

    result = batch_for_datasource.validate(suite)

    assert result.success, [r.exception_info for r in result.results]
    assert len(result.results) == 3
