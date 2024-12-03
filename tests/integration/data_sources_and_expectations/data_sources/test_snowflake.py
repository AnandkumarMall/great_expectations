from datetime import datetime, timezone

import pandas as pd
import pytest

from great_expectations.compatibility.snowflake import NUMBER, TIMESTAMP_NTZ, TIMESTAMP_TZ
from great_expectations.compatibility.sqlalchemy import sqltypes
from great_expectations.expectations import (
    ExpectColumnDistinctValuesToContainSet,
    ExpectColumnSumToBeBetween,
    ExpectColumnValuesToBeBetween,
    ExpectColumnValuesToBeOfType,
)
from tests.integration.test_utils.data_source_config import SnowflakeDatasourceTestConfig
from tests.integration.test_utils.data_source_config.snowflake import SnowflakeBatchTestSetup


class TestDataTypes:
    """This set of tests ensures that we can run expectations against every data
    type supported by Snowflake.

    https://docs.snowflake.com/en/sql-reference/intro-summary-data-types
    """

    COLUMN = "col_a"

    @pytest.mark.snowflake
    @pytest.mark.parametrize(
        "column_type",
        [
            NUMBER,  # snowflake specific type equivalent to DECIMAL, NUMERIC
            sqltypes.INT,  # equivalent to INTEGER, BIGINT, SMALLINT, TINYINT, BYTEINT
            sqltypes.FLOAT,  # equivalent to FLOAT4, FLOAT8, DOUBLE, DOUBLE PRECISION, REAL
        ],
    )
    def test_numeric(self, column_type):
        batch_setup = SnowflakeBatchTestSetup(
            config=SnowflakeDatasourceTestConfig(column_types={self.COLUMN: column_type}),
            data=pd.DataFrame({self.COLUMN: [1, 2, 3, 4]}),
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnSumToBeBetween(
                    column=self.COLUMN,
                    min_value=9,
                    max_value=11,
                )
            )
        assert result.success

    @pytest.mark.snowflake
    @pytest.mark.parametrize(
        "column_type",
        [
            sqltypes.VARCHAR,  # equivalent to STRING, TEXT
            sqltypes.CHAR,  # length of 1, equivalent to CHARACTER
            sqltypes.BINARY,  # equivalent to VARBINARY
        ],
    )
    def test_string(self, column_type):
        batch_setup = SnowflakeBatchTestSetup(
            config=SnowflakeDatasourceTestConfig(column_types={self.COLUMN: column_type}),
            data=pd.DataFrame({self.COLUMN: ["a", "b", "c", "d"]}),
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnDistinctValuesToContainSet(
                    column=self.COLUMN,
                    value_set=[
                        "a",
                        "b",
                    ],
                )
            )
        assert result.success

    @pytest.mark.snowflake
    @pytest.mark.xfail(
        strict=True, reason="Raises exception 'unhashable type: `bytearray`' (CORE-684)"
    )
    def test_binary(self):
        column_type = sqltypes.BINARY  # equivalent to VARBINARY
        batch_setup = SnowflakeBatchTestSetup(
            config=SnowflakeDatasourceTestConfig(column_types={self.COLUMN: column_type}),
            data=pd.DataFrame({self.COLUMN: [b"a", b"b", b"c", b"d"]}),
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnDistinctValuesToContainSet(
                    column=self.COLUMN,
                    value_set=[
                        b"a",
                        b"b",
                    ],
                )
            )
        assert result.success

    @pytest.mark.snowflake
    def test_boolean(self):
        column_type = sqltypes.BOOLEAN
        batch_setup = SnowflakeBatchTestSetup(
            config=SnowflakeDatasourceTestConfig(column_types={self.COLUMN: column_type}),
            data=pd.DataFrame({self.COLUMN: [True, False, True, True]}),
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnValuesToBeOfType(column=self.COLUMN, type_="BOOLEAN")
            )
        assert result.success

    @pytest.mark.snowflake
    def test_date(self):
        column_type = sqltypes.DATE
        batch_setup = SnowflakeBatchTestSetup(
            config=SnowflakeDatasourceTestConfig(column_types={self.COLUMN: column_type}),
            data=pd.DataFrame(
                {
                    self.COLUMN: [
                        datetime(year=2021, month=1, day=31, tzinfo=timezone.utc).date(),
                        datetime(year=2022, month=1, day=31, tzinfo=timezone.utc).date(),
                        datetime(year=2023, month=1, day=31, tzinfo=timezone.utc).date(),
                    ]
                }
            ),
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnValuesToBeBetween(
                    column=self.COLUMN,
                    min_value=datetime(year=2021, month=1, day=1, tzinfo=timezone.utc).date(),
                    max_value=datetime(year=2024, month=1, day=1, tzinfo=timezone.utc).date(),
                )
            )
        assert result.success

    @pytest.mark.snowflake
    @pytest.mark.parametrize(
        "column_type",
        [
            sqltypes.DATETIME,
            TIMESTAMP_TZ,
            TIMESTAMP_NTZ,
        ],
    )
    def test_datetime(self, column_type):
        batch_setup = SnowflakeBatchTestSetup(
            config=SnowflakeDatasourceTestConfig(column_types={self.COLUMN: column_type}),
            data=pd.DataFrame(
                {
                    self.COLUMN: [
                        str(datetime(year=2021, month=1, day=31, tzinfo=timezone.utc)),
                        str(datetime(year=2022, month=1, day=31, tzinfo=timezone.utc)),
                        str(datetime(year=2023, month=1, day=31, tzinfo=timezone.utc)),
                    ]
                }
            ),
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnValuesToBeBetween(
                    column=self.COLUMN,
                    min_value=datetime(year=2021, month=1, day=1, tzinfo=timezone.utc),
                    max_value=datetime(year=2024, month=1, day=1, tzinfo=timezone.utc),
                )
            )
        assert result.success

    @pytest.mark.snowflake
    @pytest.mark.xfail(
        strict=True,
        reason="time is not an accepted min/max value parameter, and other date types "
        "(datetime, timestamp, etc) fail in the query.",
    )
    def test_time(self):
        column_type = sqltypes.TIME
        batch_setup = SnowflakeBatchTestSetup(
            config=SnowflakeDatasourceTestConfig(column_types={self.COLUMN: column_type}),
            data=pd.DataFrame(
                {
                    self.COLUMN: [
                        datetime(year=2021, month=1, day=31, tzinfo=timezone.utc).time(),
                        datetime(year=2022, month=1, day=31, tzinfo=timezone.utc).time(),
                        datetime(year=2023, month=1, day=31, tzinfo=timezone.utc).time(),
                    ]
                }
            ),
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnValuesToBeBetween(
                    column=self.COLUMN,
                    min_value=datetime(year=2021, month=1, day=1, tzinfo=timezone.utc).time(),
                    max_value=datetime(year=2024, month=1, day=1, tzinfo=timezone.utc).time(),
                )
            )
        assert result.success
