from typing import Sequence, TypedDict

import pandas as pd
import pytest

from great_expectations.datasource.fluent.interfaces import Batch
from great_expectations.metrics.column.aggregate_nonnull_count import (
    ColumnAggregateNonNullCount,
    ColumnAggregateNonNullCountResult,
)
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.test_utils.data_source_config import (
    BigQueryDatasourceTestConfig,
    DataSourceTestConfig,
    SnowflakeDatasourceTestConfig,
)
from tests.metrics.conftest import (
    PANDAS_DATA_SOURCES,
    SPARK_DATA_SOURCES,
    SQL_DATA_SOURCES,
)

STRING_COLUMN_NAME = "whatevs"
DATA_FRAME = pd.DataFrame(
    {
        STRING_COLUMN_NAME: ["a", None, "c", "d", None],
    },
    dtype="object",
)

ALL_NULL_DATA_FRAME = pd.DataFrame(
    {
        STRING_COLUMN_NAME: [None, None, None],
    },
    dtype="object",
)

NO_NULL_DATA_FRAME = pd.DataFrame(
    {
        STRING_COLUMN_NAME: ["a", "b", "c", "d"],
    },
    dtype="object",
)

# Empty dataframe with explicit schema for Spark compatibility
EMPTY_DATA_FRAME = pd.DataFrame(
    {
        STRING_COLUMN_NAME: pd.Series([], dtype="object"),
    }
)


# Type definitions for the compatibility dictionary
class IncompatibleDataSources(TypedDict):
    bigquery: Sequence[DataSourceTestConfig]
    snowflake: Sequence[DataSourceTestConfig]
    spark: Sequence[DataSourceTestConfig]


class EmptyDatasetCompatibility(TypedDict):
    compatible: Sequence[DataSourceTestConfig]
    incompatible: IncompatibleDataSources


# Create datasource groups based on compatibility with empty datasets
EMPTY_DATASET_COMPATIBILITY: EmptyDatasetCompatibility = {
    # Sources that work with empty datasets
    "compatible": [
        config
        for config in SQL_DATA_SOURCES
        if not isinstance(config, (BigQueryDatasourceTestConfig, SnowflakeDatasourceTestConfig))
    ]
    + PANDAS_DATA_SOURCES,
    # Sources that fail with specific errors
    "incompatible": {
        "bigquery": [
            config
            for config in SQL_DATA_SOURCES
            if isinstance(config, BigQueryDatasourceTestConfig)
        ],
        "snowflake": [
            config
            for config in SQL_DATA_SOURCES
            if isinstance(config, SnowflakeDatasourceTestConfig)
        ],
        "spark": SPARK_DATA_SOURCES,
    },
}


class TestColumnAggregateNonNullCount:
    @parameterize_batch_for_data_sources(
        data_source_configs=SQL_DATA_SOURCES + PANDAS_DATA_SOURCES + SPARK_DATA_SOURCES,
        data=DATA_FRAME,
    )
    def test_success(self, batch_for_datasource: Batch) -> None:
        metric = ColumnAggregateNonNullCount(column=STRING_COLUMN_NAME)
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnAggregateNonNullCountResult)
        assert metric_result.value == 3

    @parameterize_batch_for_data_sources(
        data_source_configs=SQL_DATA_SOURCES + PANDAS_DATA_SOURCES,
        data=ALL_NULL_DATA_FRAME,
    )
    def test_all_null(self, batch_for_datasource: Batch) -> None:
        metric = ColumnAggregateNonNullCount(column=STRING_COLUMN_NAME)
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnAggregateNonNullCountResult)
        assert metric_result.value == 0

    @parameterize_batch_for_data_sources(
        data_source_configs=SPARK_DATA_SOURCES,
        data=ALL_NULL_DATA_FRAME,
    )
    @pytest.mark.xfail(reason="Spark cannot determine types from all-null dataset", strict=True)
    def test_all_null_spark(self, batch_for_datasource: Batch) -> None:
        metric = ColumnAggregateNonNullCount(column=STRING_COLUMN_NAME)
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnAggregateNonNullCountResult)
        assert metric_result.value == 0

    @parameterize_batch_for_data_sources(
        data_source_configs=SQL_DATA_SOURCES + PANDAS_DATA_SOURCES + SPARK_DATA_SOURCES,
        data=NO_NULL_DATA_FRAME,
    )
    def test_no_null(self, batch_for_datasource: Batch) -> None:
        metric = ColumnAggregateNonNullCount(column=STRING_COLUMN_NAME)
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnAggregateNonNullCountResult)
        assert metric_result.value == 4

    # Empty dataset tests consolidated into a single test method with appropriate markers
    @parameterize_batch_for_data_sources(
        data_source_configs=EMPTY_DATASET_COMPATIBILITY["compatible"],
        data=EMPTY_DATA_FRAME,
    )
    def test_empty_dataset(self, batch_for_datasource: Batch) -> None:
        """Test the metric with an empty dataset for compatible data sources."""
        metric = ColumnAggregateNonNullCount(column=STRING_COLUMN_NAME)
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnAggregateNonNullCountResult)
        assert metric_result.value == 0

    @parameterize_batch_for_data_sources(
        data_source_configs=EMPTY_DATASET_COMPATIBILITY["incompatible"]["bigquery"],
        data=EMPTY_DATA_FRAME,
    )
    @pytest.mark.xfail(reason="BigQuery cannot handle empty datasets", strict=True)
    def test_empty_dataset_bigquery(self, batch_for_datasource: Batch) -> None:
        """Test BigQuery with empty datasets (expected to fail)."""
        self._run_empty_dataset_test(batch_for_datasource)

    @parameterize_batch_for_data_sources(
        data_source_configs=EMPTY_DATASET_COMPATIBILITY["incompatible"]["snowflake"],
        data=EMPTY_DATA_FRAME,
    )
    @pytest.mark.xfail(reason="Snowflake syntax error when inserting empty dataset", strict=True)
    def test_empty_dataset_snowflake(self, batch_for_datasource: Batch) -> None:
        """Test Snowflake with empty datasets (expected to fail)."""
        self._run_empty_dataset_test(batch_for_datasource)

    @parameterize_batch_for_data_sources(
        data_source_configs=EMPTY_DATASET_COMPATIBILITY["incompatible"]["spark"],
        data=EMPTY_DATA_FRAME,
    )
    @pytest.mark.xfail(reason="Spark cannot infer schema from empty dataset", strict=True)
    def test_empty_dataset_spark(self, batch_for_datasource: Batch) -> None:
        """Test Spark with empty datasets (expected to fail)."""
        self._run_empty_dataset_test(batch_for_datasource)

    def _run_empty_dataset_test(self, batch_for_datasource: Batch) -> None:
        """Helper method to avoid code duplication in empty dataset tests."""
        metric = ColumnAggregateNonNullCount(column=STRING_COLUMN_NAME)
        metric_result = batch_for_datasource.compute_metrics(metric)

        assert isinstance(metric_result, ColumnAggregateNonNullCountResult)
        assert metric_result.value == 0
