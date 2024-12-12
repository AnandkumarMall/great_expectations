from datetime import datetime, timezone
from typing import Sequence

import pandas as pd

import great_expectations.expectations as gxe
from great_expectations.core.expectation_suite import ExpectationSuite
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.test_utils.data_source_config import (
    BigQueryDatasourceTestConfig,
    DatabricksDatasourceTestConfig,
    DataSourceTestConfig,
    MSSQLDatasourceTestConfig,
    MySQLDatasourceTestConfig,
    PandasDataFrameDatasourceTestConfig,
    PandasFilesystemCsvDatasourceTestConfig,
    PostgreSQLDatasourceTestConfig,
    SnowflakeDatasourceTestConfig,
    SparkFilesystemCsvDatasourceTestConfig,
    SqliteDatasourceTestConfig,
)

ALL_DATA_SOURCES: Sequence[DataSourceTestConfig] = [
    BigQueryDatasourceTestConfig(),
    DatabricksDatasourceTestConfig(),
    MSSQLDatasourceTestConfig(),
    MySQLDatasourceTestConfig(),
    PandasDataFrameDatasourceTestConfig(),
    PandasFilesystemCsvDatasourceTestConfig(),
    PostgreSQLDatasourceTestConfig(),
    SnowflakeDatasourceTestConfig(),
    SparkFilesystemCsvDatasourceTestConfig(),
    SqliteDatasourceTestConfig(),
]

NON_SQL_DATA_SOURCES: Sequence[DataSourceTestConfig] = [
    PandasDataFrameDatasourceTestConfig(),
    PandasFilesystemCsvDatasourceTestConfig(),
    SparkFilesystemCsvDatasourceTestConfig(),
]

SQL_DATA_SOURCES: Sequence[DataSourceTestConfig] = [
    BigQueryDatasourceTestConfig(),
    DatabricksDatasourceTestConfig(),
    MSSQLDatasourceTestConfig(),
    MySQLDatasourceTestConfig(),
    PostgreSQLDatasourceTestConfig(),
    SnowflakeDatasourceTestConfig(),
    SqliteDatasourceTestConfig(),
]

DATA_SOURCES_THAT_SUPPORT_DATE_COMPARISONS: Sequence[DataSourceTestConfig] = [
    BigQueryDatasourceTestConfig(),
    DatabricksDatasourceTestConfig(),
    MSSQLDatasourceTestConfig(),
    MySQLDatasourceTestConfig(),
    PandasDataFrameDatasourceTestConfig(),
    PostgreSQLDatasourceTestConfig(),
    SnowflakeDatasourceTestConfig(),
    SparkFilesystemCsvDatasourceTestConfig(),
]

JUST_PANDAS_DATA_SOURCES: Sequence[DataSourceTestConfig] = [PandasDataFrameDatasourceTestConfig()]


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_DATA_SOURCES,
    data=pd.DataFrame({"a": [1, 2]}),
)
def test_expect_column_min_to_be_between(batch_for_datasource) -> None:
    expectation = gxe.ExpectColumnMinToBeBetween(column="a", min_value=1, max_value=1)
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_DATA_SOURCES,
    data=pd.DataFrame(
        {
            "date": [
                datetime(year=2021, month=1, day=31, tzinfo=timezone.utc).date(),
                datetime(year=2022, month=1, day=31, tzinfo=timezone.utc).date(),
                datetime(year=2023, month=1, day=31, tzinfo=timezone.utc).date(),
            ]
        }
    ),
)
def test_expect_column_min_to_be_between__date(batch_for_datasource) -> None:
    expectation = gxe.ExpectColumnMinToBeBetween(
        column="date",
        min_value=datetime(year=2021, month=1, day=1, tzinfo=timezone.utc).date(),
        max_value=datetime(year=2022, month=1, day=1, tzinfo=timezone.utc).date(),
    )
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_DATA_SOURCES,
    data=pd.DataFrame(
        {
            "date": [
                datetime(year=2021, month=1, day=31, tzinfo=timezone.utc).date(),
                datetime(year=2022, month=1, day=31, tzinfo=timezone.utc).date(),
                datetime(year=2023, month=1, day=31, tzinfo=timezone.utc).date(),
            ]
        }
    ),
)
def test_expect_column_max_to_be_between__date(batch_for_datasource) -> None:
    expectation = gxe.ExpectColumnMaxToBeBetween(
        column="date",
        min_value=datetime(year=2023, month=1, day=1, tzinfo=timezone.utc).date(),
        max_value=datetime(year=2024, month=1, day=1, tzinfo=timezone.utc).date(),
    )
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_DATA_SOURCES,
    data=pd.DataFrame({"a": [1, 2]}),
)
def test_expect_column_max_to_be_between(batch_for_datasource) -> None:
    expectation = gxe.ExpectColumnMaxToBeBetween(column="a", min_value=2, max_value=2)
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_DATA_SOURCES,
    data=pd.DataFrame({"a": [1, 2]}),
)
def test_expect_column_to_exist(batch_for_datasource):
    expectation = gxe.ExpectColumnToExist(column="a")
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_DATA_SOURCES,
    data=pd.DataFrame({"a": [1, 2]}),
)
def test_expect_column_values_to_not_be_null(batch_for_datasource):
    expectation = gxe.ExpectColumnValuesToNotBeNull(column="a")
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_DATA_SOURCES,
    data=pd.DataFrame({"a": [1, 2, 3, 4]}),
)
def test_expect_column_mean_to_be_between(batch_for_datasource):
    expectation = gxe.ExpectColumnMeanToBeBetween(column="a", min_value=2, max_value=3)
    result = batch_for_datasource.validate(expectation)
    assert result.success


@parameterize_batch_for_data_sources(
    data_source_configs=[SparkFilesystemCsvDatasourceTestConfig()],
    data=pd.DataFrame(
        {
            "col1": [1, 2, 3, 4, 5],
            "col2": ["A", "B", "C", "D", None],
            "col3": [1.1, None, 3.3, 4.4, 5.5],
        }
    ),
)
def test_missing_condition_parser_causes_entire_suite_to_fail(batch_for_datasource):
    suite = ExpectationSuite(
        name="faulty",
        expectations=[
            gxe.ExpectColumnValuesToNotBeNull(column="col1", result_format="COMPLETE"),
            gxe.ExpectColumnValuesToBeInSet(
                column="col2",
                value_set=["A", "B", "C"],
                row_condition="col3 IS NOT NULL",
                mostly=0.665,
                # condition_parser='spark',
                result_format="COMPLETE",
            ),
        ],
    )

    result = batch_for_datasource.validate(suite)
    assert not result.success
    assert all(res.success is False and res.exception_info for res in result.results)
