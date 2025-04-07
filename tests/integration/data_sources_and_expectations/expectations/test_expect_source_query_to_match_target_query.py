from datetime import datetime, timezone
from typing import Sequence

import pandas as pd

import great_expectations.expectations as gxe
from great_expectations.datasource.fluent.interfaces import Batch
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.test_utils.data_source_config import (
    DataSourceTestConfig,
    PostgreSQLDatasourceTestConfig,
)

# pandas and spark not currently supported by this Expecatation
ALL_SUPPORTED_DATA_SOURCES: Sequence[DataSourceTestConfig] = [
    PostgreSQLDatasourceTestConfig(),
]

TABLE_1 = pd.DataFrame(
    {
        "entity_id": [1, 2],
        "created_at": [
            datetime(year=2024, month=12, day=1, tzinfo=timezone.utc).date(),
            datetime(year=2024, month=11, day=30, tzinfo=timezone.utc).date(),
        ],
        "quantity": [1, 2],
        "temperature": [75, 92],
        "color": ["red", "red"],
    }
)

TABLE_2 = pd.DataFrame(
    {
        "entity_id": [1, 2],
        "created_at": [
            datetime(year=2024, month=12, day=1, tzinfo=timezone.utc).date(),
            datetime(year=2024, month=11, day=30, tzinfo=timezone.utc).date(),
        ],
        "total_quantity": [1, 2],
    }
)

DATE_COLUMN = "created_at"

SUCCESS_QUERIES = [
    ("SELECT quantity FROM {batch}", "SELECT quantity FROM {batch}"),
]


@parameterize_batch_for_data_sources(
    data_source_configs=ALL_SUPPORTED_DATA_SOURCES,
    data=TABLE_1,
    extra_data={"table_2": TABLE_2},
)
def test_expect_source_query_to_match_target_query_set_success(
    batch_for_datasource: Batch,
) -> None:
    # Get the target batch from the same data source
    target_asset = batch_for_datasource.data_asset.datasource.add_query_asset(
        name="table_2",
        query="SELECT * FROM table_2",
    )
    target_batch = target_asset.build_batch_request()
    target_batch = target_asset.get_batch(target_batch)

    expectation = gxe.ExpectSourceQueryToMatchTargetQuery(
        description="Expect 2 queries from 2 different Data Sources to return the same result",
        target_query=SUCCESS_QUERIES[0][
            0
        ],  # queries the data sources in ALL_SUPPORTED_DATA_SOURCES
        source_data_source_name=batch_for_datasource.data_asset.datasource.name,
        source_query=SUCCESS_QUERIES[0][
            1
        ],  # queries the data source provided by the Expectation (source_data_source_name)
    )
    result = batch_for_datasource.validate(expectation)
    assert result.success
    assert result.exception_info.get("raised_exception") is False
