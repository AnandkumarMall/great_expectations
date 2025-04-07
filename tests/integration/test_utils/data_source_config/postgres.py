from typing import Mapping

import pandas as pd
import pytest

from great_expectations.compatibility.typing_extensions import override
from great_expectations.datasource.fluent.sql_datasource import TableAsset
from tests.integration.test_utils.data_source_config.base import (
    BatchTestSetup,
    DataSourceTestConfig,
)
from tests.integration.test_utils.data_source_config.sql import SQLBatchTestSetup


class PostgreSQLDatasourceTestConfig(DataSourceTestConfig):
    @property
    @override
    def label(self) -> str:
        return "postgresql"

    @property
    @override
    def pytest_mark(self) -> pytest.MarkDecorator:
        return pytest.mark.postgresql

    @override
    def create_batch_setup(
        self,
        request: pytest.FixtureRequest,
        data: pd.DataFrame,
        extra_data: Mapping[str, pd.DataFrame],
    ) -> BatchTestSetup:
        return PostgresBatchTestSetup(
            data=data,
            config=self,
            extra_data=extra_data,
            table_name=self.table_name,
        )


class PostgresBatchTestSetup(SQLBatchTestSetup[PostgreSQLDatasourceTestConfig]):
    @property
    @override
    def connection_string(self) -> str:
        return "postgresql+psycopg2://postgres@localhost:5432/test_ci"

    @property
    @override
    def use_schema(self) -> bool:
        return False

    @override
    def make_asset(self) -> TableAsset:
        # Create a single data source for all tables
        data_source_name = self._random_resource_name()
        data_source = self.context.data_sources.add_postgres(
            name=data_source_name, connection_string=self.connection_string
        )

        # Add the main table asset
        main_asset = data_source.add_table_asset(
            name=self._random_resource_name(),
            table_name=self.table_name,
            schema_name=self.schema,
        )

        # Add the extra table assets
        for table_data in self.extra_table_data.values():
            asset = data_source.add_table_asset(
                name=self._random_resource_name(),
                table_name=table_data.name,
                schema_name=self.schema,
            )
            # Create a batch for each extra table
            batch_name = self._random_resource_name()
            batch = asset.add_batch_definition_whole_table(name=batch_name).get_batch()
            # Store the batch in the validator's batch manager
            validator = self.context.get_validator(batch=batch)
            validator.execution_engine.batch_manager.load_batch_list([batch])

        return main_asset
