from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Mapping

import pytest

from great_expectations.compatibility.pydantic import BaseSettings
from great_expectations.compatibility.typing_extensions import override
from great_expectations.datasource.fluent.sql_datasource import TableAsset
from tests.integration.test_utils.data_source_config.base import (
    BatchTestSetup,
    DataSourceTestConfig,
)
from tests.integration.test_utils.data_source_config.sql import SQLBatchTestSetup

if TYPE_CHECKING:
    import pandas as pd


class AthenaDatasourceTestConfig(DataSourceTestConfig):
    @property
    @override
    def label(self) -> str:
        return "athena"

    @property
    @override
    def pytest_mark(self) -> pytest.MarkDecorator:
        return pytest.mark.athena

    @override
    def create_batch_setup(
        self,
        request: pytest.FixtureRequest,
        data: pd.DataFrame,
        extra_data: Mapping[str, pd.DataFrame],
    ) -> BatchTestSetup:
        return AthenaBatchTestSetup(
            data=data,
            config=self,
            extra_data=extra_data,
            table_name=self.table_name,
        )


class AthenaBatchTestSetup(SQLBatchTestSetup[AthenaDatasourceTestConfig]):
    @property
    @override
    def connection_string(self) -> str:
        return self.athena_connection_config.connection_string

    @property
    @override
    def use_schema(self) -> bool:
        return False

    @cached_property
    @override
    def asset(self) -> TableAsset:
        return self.context.data_sources.add_sql(
            name=self._random_resource_name(), connection_string=self.connection_string
        ).add_table_asset(
            name=self._random_resource_name(),
            table_name=self.table_name,
        )

    @cached_property
    def athena_connection_config(self) -> AthenaConnectionConfig:
        return AthenaConnectionConfig()  # type: ignore[call-arg]  # retrieves env vars


class AthenaConnectionConfig(BaseSettings):
    """Environment variables for Athena connection. Injected via CI."""

    ATHENA_DB_NAME: str
    ATHENA_STAGING_S3: str

    @property
    def connection_string(self) -> str:
        return f"awsathena+rest://@athena.us-east-1.amazonaws.com/{self.ATHENA_DB_NAME}?s3_staging_dir={self.ATHENA_STAGING_S3}"
