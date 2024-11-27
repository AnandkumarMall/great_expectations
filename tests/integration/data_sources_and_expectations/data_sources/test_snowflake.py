import pandas as pd
import pytest

from great_expectations.compatibility import snowflake
from great_expectations.compatibility.sqlalchemy import sqltypes
from great_expectations.expectations import (
    ExpectColumnDistinctValuesToContainSet,
    ExpectColumnSumToBeBetween,
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
            snowflake.NUMBER,  # equivalent to DECIMAL, NUMERIC
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
    @pytest.mark.xfail(strict=True, reason="Raises exception 'unhashable type: `bytearray`'")
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

    def test_boolean(self): ...

    def test_date(self): ...

    def test_semi_structured(self): ...

    def test_geospatial(self): ...

    def test_vector(self): ...
