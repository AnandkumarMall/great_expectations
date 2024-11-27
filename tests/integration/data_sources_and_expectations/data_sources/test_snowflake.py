import pandas as pd
import pytest

from great_expectations.compatibility import snowflake
from great_expectations.compatibility.sqlalchemy import sqltypes
from great_expectations.expectations import ExpectColumnSumToBeBetween
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
            snowflake.NUMBER,
            sqltypes.NUMERIC,
            sqltypes.INT,
            sqltypes.BIGINT,
            sqltypes.SMALLINT,
            sqltypes.FLOAT,
            sqltypes.DOUBLE,
            sqltypes.DOUBLE_PRECISION,
            sqltypes.REAL,
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

    def test_string(self): ...

    def test_boolean(self): ...

    def test_date(self): ...

    def test_semi_structured(self): ...

    def test_geospatial(self): ...

    def test_vector(self): ...
