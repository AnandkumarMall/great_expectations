"""Integration tests for SingleStore (formerly MemSQL).

Validates GX functionality against a live SingleStore instance.
"""

import os

import pandas as pd
import pytest

import great_expectations.expectations as gxe
from great_expectations import get_context
from tests.integration.test_utils.data_source_config.generic_sql import (
    GenericSQLBatchTestSetup,
    GenericSQLDatasourceTestConfig,
)

pytestmark = pytest.mark.generic_sql

CONNECTION_STRING = os.environ.get("SINGLE_STORE_DB_CONNECTION_STRING", "")


@pytest.mark.skipif(
    not CONNECTION_STRING,
    reason="SINGLE_STORE_DB_CONNECTION_STRING not set; we can do this, but we'd need an always up "
    "instance of SingleStoreDB. Also, must have sqlalchemy-singlestoredb = '^1.2.1' installed.",
)
class TestSingleStore:
    """Smoke tests for SingleStore compatibility.

    Ticket: GX-3211 — SingleStore dialect compatibility issue reported by Windward.
    """

    DATA = pd.DataFrame(
        {
            "name": ["Alice", "Bob", "Charlie"],
            "age": [30, 25, 35],
        }
    )

    def _make_setup(self) -> GenericSQLBatchTestSetup:
        return GenericSQLBatchTestSetup(
            config=GenericSQLDatasourceTestConfig(
                connection_string=CONNECTION_STRING,
            ),
            data=self.DATA,
            extra_data={},
            context=get_context(mode="ephemeral"),
        )

    def test_can_connect_and_validate(self) -> None:
        batch_setup = self._make_setup()

        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                gxe.ExpectColumnValuesToBeInSet(
                    column="name",
                    value_set=["Alice", "Bob", "Charlie"],
                )
            )
        assert result.success

    def test_numeric_expectation(self) -> None:
        batch_setup = self._make_setup()

        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                gxe.ExpectColumnSumToBeBetween(
                    column="age",
                    min_value=89,
                    max_value=91,
                )
            )
        assert result.success

    def test_row_count(self) -> None:
        batch_setup = self._make_setup()

        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                gxe.ExpectTableRowCountToBeBetween(
                    min_value=3,
                    max_value=3,
                )
            )
        assert result.success

    def test_regex_expectation(self) -> None:
        batch_setup = self._make_setup()

        with batch_setup.batch_test_context() as batch:
            result = batch.validate(
                gxe.ExpectColumnValuesToMatchRegex(
                    column="name",
                    regex="^[A-Z].*",
                )
            )
        assert result.success
