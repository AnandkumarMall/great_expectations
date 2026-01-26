from datetime import date

import pandas as pd

from great_expectations.datasource.fluent.interfaces import Batch
from great_expectations.metrics.column.distinct_values_not_equal_set import (
    ColumnDistinctValuesNotEqualSet,
    ColumnDistinctValuesNotEqualSetResult,
)
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.data_sources_and_expectations.test_canonical_expectations import (
    DATA_SOURCES_THAT_SUPPORT_DATE_COMPARISONS,
)
from tests.metrics.conftest import ALL_DATA_SOURCES

COLUMN_NAME = "my_col"
DATA_FRAME = pd.DataFrame(
    {
        COLUMN_NAME: ["a", "b", "c", "c", "c", None],
    },
)
DATE_DATA_FRAME = pd.DataFrame(
    {
        COLUMN_NAME: [date(2024, 11, 19), date(2024, 11, 20)],
    },
)


class TestColumnDistinctValuesNotEqualSet:
    @parameterize_batch_for_data_sources(
        data_source_configs=ALL_DATA_SOURCES,
        data=DATA_FRAME,
    )
    def test_sets_equal(self, batch_for_datasource: Batch) -> None:
        """When column values exactly match the set, both lists should be empty."""
        metric = ColumnDistinctValuesNotEqualSet(column=COLUMN_NAME, value_set=["a", "b", "c"])
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnDistinctValuesNotEqualSetResult)
        assert metric_result.value["in_column_not_in_set"] == []
        assert metric_result.value["in_set_not_in_column"] == []

    @parameterize_batch_for_data_sources(
        data_source_configs=ALL_DATA_SOURCES,
        data=DATA_FRAME,
    )
    def test_column_has_extra_values(self, batch_for_datasource: Batch) -> None:
        """When column has values not in set, in_column_not_in_set should contain them."""
        metric = ColumnDistinctValuesNotEqualSet(
            column=COLUMN_NAME,
            value_set=["a", "b"],  # missing "c"
        )
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnDistinctValuesNotEqualSetResult)
        assert metric_result.value["in_column_not_in_set"] == ["c"]
        assert metric_result.value["in_set_not_in_column"] == []

    @parameterize_batch_for_data_sources(
        data_source_configs=ALL_DATA_SOURCES,
        data=DATA_FRAME,
    )
    def test_set_has_extra_values(self, batch_for_datasource: Batch) -> None:
        """When set has values not in column, in_set_not_in_column should contain them."""
        metric = ColumnDistinctValuesNotEqualSet(
            column=COLUMN_NAME, value_set=["a", "b", "c", "d", "e"]
        )
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnDistinctValuesNotEqualSetResult)
        assert metric_result.value["in_column_not_in_set"] == []
        assert set(metric_result.value["in_set_not_in_column"]) == {"d", "e"}

    @parameterize_batch_for_data_sources(
        data_source_configs=ALL_DATA_SOURCES,
        data=DATA_FRAME,
    )
    def test_both_have_extra_values(self, batch_for_datasource: Batch) -> None:
        """When both have unique values, both lists should contain them."""
        metric = ColumnDistinctValuesNotEqualSet(
            column=COLUMN_NAME,
            value_set=["a", "b", "d"],  # missing c, has extra d
        )
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnDistinctValuesNotEqualSetResult)
        assert metric_result.value["in_column_not_in_set"] == ["c"]
        assert metric_result.value["in_set_not_in_column"] == ["d"]

    @parameterize_batch_for_data_sources(
        data_source_configs=ALL_DATA_SOURCES,
        data=DATA_FRAME,
    )
    def test_completely_different_sets(self, batch_for_datasource: Batch) -> None:
        """When sets are completely different, both lists should be fully populated."""
        metric = ColumnDistinctValuesNotEqualSet(column=COLUMN_NAME, value_set=["x", "y", "z"])
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnDistinctValuesNotEqualSetResult)
        assert set(metric_result.value["in_column_not_in_set"]) == {"a", "b", "c"}
        assert set(metric_result.value["in_set_not_in_column"]) == {"x", "y", "z"}

    @parameterize_batch_for_data_sources(
        data_source_configs=ALL_DATA_SOURCES,
        data=DATA_FRAME,
    )
    def test_limit_parameter(self, batch_for_datasource: Batch) -> None:
        """The limit parameter should restrict the number of returned values in each list."""
        metric = ColumnDistinctValuesNotEqualSet(
            column=COLUMN_NAME, value_set=["w", "x", "y", "z"], limit=2
        )
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnDistinctValuesNotEqualSetResult)
        # Both lists should be limited
        assert len(metric_result.value["in_column_not_in_set"]) <= 2
        assert len(metric_result.value["in_set_not_in_column"]) <= 2

    @parameterize_batch_for_data_sources(
        data_source_configs=DATA_SOURCES_THAT_SUPPORT_DATE_COMPARISONS,
        data=DATE_DATA_FRAME,
    )
    def test_dates_equal(self, batch_for_datasource: Batch) -> None:
        """When date column values exactly match the set, both lists should be empty."""
        metric = ColumnDistinctValuesNotEqualSet(
            column=COLUMN_NAME,
            value_set=[date(2024, 11, 19), date(2024, 11, 20)],
        )
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnDistinctValuesNotEqualSetResult)
        assert metric_result.value["in_column_not_in_set"] == []
        assert metric_result.value["in_set_not_in_column"] == []

    @parameterize_batch_for_data_sources(
        data_source_configs=DATA_SOURCES_THAT_SUPPORT_DATE_COMPARISONS,
        data=DATE_DATA_FRAME,
    )
    def test_dates_with_str_value_set(self, batch_for_datasource: Batch) -> None:
        """When date column is compared with string value_set, should handle type coercion."""
        metric = ColumnDistinctValuesNotEqualSet(
            column=COLUMN_NAME,
            value_set=["2024-11-19", "2024-11-20"],  # strings instead of date objects
        )
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnDistinctValuesNotEqualSetResult)
        # After type coercion, the sets should be equal
        assert metric_result.value["in_column_not_in_set"] == []
        assert metric_result.value["in_set_not_in_column"] == []
