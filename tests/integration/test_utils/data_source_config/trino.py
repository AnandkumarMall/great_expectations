from typing import Mapping, Optional

import pandas as pd
import pytest

from great_expectations.compatibility.pydantic import BaseSettings
from great_expectations.compatibility.typing_extensions import override
from great_expectations.data_context import AbstractDataContext
from great_expectations.datasource.fluent.sql_datasource import TableAsset
from tests.integration.sql_session_manager import SessionSQLEngineManager
from tests.integration.test_utils.data_source_config.base import (
    BatchTestSetup,
    DataSourceTestConfig,
)
from tests.integration.test_utils.data_source_config.sql import (
    SQLBatchTestSetup,
)


class TrinoDatasourceTestConfig(DataSourceTestConfig):
    @property
    @override
    def label(self) -> str:
        return "trino"

    @property
    @override
    def pytest_mark(self) -> pytest.MarkDecorator:
        return pytest.mark.trino

    @override
    def create_batch_setup(
        self,
        request: pytest.FixtureRequest,
        data: pd.DataFrame,
        extra_data: Mapping[str, pd.DataFrame],
        context: AbstractDataContext,
        engine_manager: Optional[SessionSQLEngineManager] = None,
    ) -> BatchTestSetup:
        return TrinoBatchTestSetup(
            data=data,
            config=self,
            extra_data=extra_data,
            table_name=self.table_name,
            context=context,
            engine_manager=engine_manager,
        )


class TrinoConnectionConfig(BaseSettings):
    """This class retrieves these values from the environment.
    If you're testing locally, you can use your Trino creds
    and test against your own Snowflake account.
    """

    TRINO_USER: str
    TRINO_PW: str
    TRINO_HOST: str
    TRINO_PORT: str
    TRINO_CATALOG: str
    TRINO_SCHEMA: str

    @property
    def connection_string(self) -> str:
        # Note: we don't specify the schema here because it will be created dynamically, and we pass
        # it into the `data_sources.add_snowflake` call.
        return (
            f"trino://{self.TRINO_USER}:{self.TRINO_PW}"
            f"@{self.TRINO_HOST}:{self.TRINO_PORT}/{self.TRINO_CATALOG}/{self.TRINO_SCHEMA}"
        )


class TrinoBatchTestSetup(SQLBatchTestSetup[TrinoDatasourceTestConfig]):
    @property
    @override
    def connection_string(self) -> str:
        return self.trino_connection_config.connection_string

    @property
    @override
    def use_schema(self) -> bool:
        return True

    def __init__(
        self,
        config: TrinoDatasourceTestConfig,
        data: pd.DataFrame,
        extra_data: Mapping[str, pd.DataFrame],
        context: AbstractDataContext,
        table_name: Optional[str] = None,
        engine_manager: Optional[SessionSQLEngineManager] = None,
    ) -> None:
        self.trino_connection_config = TrinoConnectionConfig()  # type: ignore[call-arg]  # retrieves env vars
        super().__init__(
            config=config,
            data=data,
            extra_data=extra_data,
            table_name=table_name,
            engine_manager=engine_manager,
            context=context,
        )

    @override
    def make_asset(self) -> TableAsset:
        schema = self.schema
        assert schema
        return self.context.data_sources.add_sql(
            name=self._random_resource_name(),
            connection_string=self.connection_string,
        ).add_table_asset(
            name=self._random_resource_name(),
            table_name=self.table_name,
        )
