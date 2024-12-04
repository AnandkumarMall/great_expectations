from datetime import datetime, timezone

import pandas as pd
import pytest

from great_expectations.compatibility.sqlalchemy import sqltypes
from great_expectations.expectations import (
    ExpectColumnDistinctValuesToContainSet,
    ExpectColumnSumToBeBetween,
    ExpectColumnValuesToBeBetween,
    ExpectColumnValuesToBeOfType,
)
from tests.integration.test_utils.data_source_config import DatabricksDatasourceTestConfig
from tests.integration.test_utils.data_source_config.databricks import DatabricksBatchTestSetup

pytestmark = pytest.mark.databricks


class TestDatabricksDataTypes:
    """This set of tests ensures that we can run expectations against every data
    type supported by Databricks.

    https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html
    """

    BOOL_COL_NAME = "my_bool"
    DATE_COL_NAME = "my_date"
    NUMERIC_COL_NAME = "my_number"
    STRING_COL_NAME = "my_string"

    DATA_FRAME = pd.DataFrame(
        {
            BOOL_COL_NAME: [True, False, True, False],
            DATE_COL_NAME: [
                datetime(2021, 1, 1, tzinfo=timezone.utc).date(),
                datetime(2021, 1, 2, tzinfo=timezone.utc).date(),
                datetime(2021, 1, 3, tzinfo=timezone.utc).date(),
                datetime(2021, 1, 4, tzinfo=timezone.utc).date(),
            ],
            NUMERIC_COL_NAME: [1, 2, 3, 4],
            STRING_COL_NAME: ["a", "b", "c", "d"],
        }
    )

    @pytest.mark.parametrize(
        "column_type",
        [
            sqltypes.SMALLINT,
            sqltypes.INT,
            sqltypes.BIGINT,
            sqltypes.DECIMAL,
            sqltypes.FLOAT,
            sqltypes.REAL,
        ],
    )
    def test_number(self, column_type: sqltypes.TypeEngine):
        batch_setup = DatabricksBatchTestSetup(
            config=DatabricksDatasourceTestConfig(
                column_types={self.NUMERIC_COL_NAME: column_type}
            ),
            data=self.DATA_FRAME,
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnSumToBeBetween(
                    column=self.NUMERIC_COL_NAME,
                    min_value=9,
                    max_value=11,
                )
            )
        assert result.success

    def test_varchar(self):
        column_type = sqltypes.String
        batch_setup = DatabricksBatchTestSetup(
            config=DatabricksDatasourceTestConfig(column_types={self.STRING_COL_NAME: column_type}),
            data=self.DATA_FRAME,
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnDistinctValuesToContainSet(
                    column=self.STRING_COL_NAME,
                    value_set=[
                        "a",
                        "b",
                    ],
                )
            )
        assert result.success

    def test_boolean(self):
        column_type = sqltypes.BOOLEAN
        batch_setup = DatabricksBatchTestSetup(
            config=DatabricksDatasourceTestConfig(column_types={self.BOOL_COL_NAME: column_type}),
            data=self.DATA_FRAME,
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnValuesToBeOfType(column=self.BOOL_COL_NAME, type_="BOOLEAN")
            )
        assert result.success

    def test_date(self):
        column_type = sqltypes.DATE
        batch_setup = DatabricksBatchTestSetup(
            config=DatabricksDatasourceTestConfig(column_types={self.DATE_COL_NAME: column_type}),
            data=self.DATA_FRAME,
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnValuesToBeBetween(
                    column=self.DATE_COL_NAME,
                    min_value=datetime(year=2021, month=1, day=1, tzinfo=timezone.utc).date(),
                    max_value=datetime(year=2024, month=1, day=1, tzinfo=timezone.utc).date(),
                )
            )
        assert result.success

    def test_datetime(self):
        column_type = sqltypes.DATETIME
        batch_setup = DatabricksBatchTestSetup(
            config=DatabricksDatasourceTestConfig(column_types={self.DATE_COL_NAME: column_type}),
            data=self.DATA_FRAME,
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnValuesToBeBetween(
                    column=self.DATE_COL_NAME,
                    min_value=datetime(year=2021, month=1, day=1, tzinfo=timezone.utc),
                    max_value=datetime(year=2024, month=1, day=1, tzinfo=timezone.utc),
                )
            )
        assert result.success

    @pytest.mark.parametrize(
        "column_type",
        [
            sqltypes.TIMESTAMP(timezone=False),
            sqltypes.TIMESTAMP(timezone=True),
        ],
    )
    def test_timestamp(self, column_type: sqltypes.TIMESTAMP):
        batch_setup = DatabricksBatchTestSetup(
            config=DatabricksDatasourceTestConfig(column_types={self.DATE_COL_NAME: column_type}),
            data=self.DATA_FRAME,
            extra_data={},
        )
        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                expect=ExpectColumnValuesToBeBetween(
                    column=self.DATE_COL_NAME,
                    min_value=datetime(year=2021, month=1, day=1, tzinfo=timezone.utc),
                    max_value=datetime(year=2024, month=1, day=1, tzinfo=timezone.utc),
                )
            )
        assert result.success
