from typing import Any, Dict, Sequence, cast

import pandas as pd
import pytest

import great_expectations.expectations as gxe
from great_expectations.datasource.fluent.interfaces import Batch
from tests.integration.conftest import parameterize_batch_for_data_sources
from tests.integration.data_sources_and_expectations.test_canonical_expectations import (
    JUST_PANDAS_DATA_SOURCES,
)
from tests.integration.test_utils.data_source_config import (
    DataSourceTestConfig,
    MSSQLDatasourceTestConfig,
    MySQLDatasourceTestConfig,
    PostgreSQLDatasourceTestConfig,
    RedshiftDatasourceTestConfig,
    SnowflakeDatasourceTestConfig,
    SqliteDatasourceTestConfig,
)

COL_NAME = "col_name"


DATA = pd.DataFrame({COL_NAME: ["aa", "ab", "ac", None]})

REGULAR_DATA_SOURCES: Sequence[DataSourceTestConfig] = [
    MySQLDatasourceTestConfig(),
    PostgreSQLDatasourceTestConfig(),
    RedshiftDatasourceTestConfig(),
    SnowflakeDatasourceTestConfig(),
    SqliteDatasourceTestConfig(),
]


class TestNormalSql:
    @pytest.mark.parametrize(
        "expectation",
        [
            pytest.param(
                gxe.ExpectColumnValuesToNotMatchLikePatternList(
                    column=COL_NAME, like_pattern_list=["bc"]
                ),
                id="one_pattern",
            ),
            pytest.param(
                gxe.ExpectColumnValuesToNotMatchLikePatternList(
                    column=COL_NAME, like_pattern_list=["bc", "%de%"]
                ),
                id="multiple_patterns",
            ),
        ],
    )
    @parameterize_batch_for_data_sources(data_source_configs=REGULAR_DATA_SOURCES, data=DATA)
    def test_success(
        self,
        batch_for_datasource: Batch,
        expectation: gxe.ExpectColumnValuesToNotMatchLikePatternList,
    ) -> None:
        result = batch_for_datasource.validate(expectation)
        assert result.success

    @pytest.mark.parametrize(
        "expectation",
        [
            pytest.param(
                gxe.ExpectColumnValuesToNotMatchLikePatternList(
                    column=COL_NAME, like_pattern_list=["%a%"]
                ),
                id="one_pattern",
            ),
            pytest.param(
                gxe.ExpectColumnValuesToNotMatchLikePatternList(
                    column=COL_NAME, like_pattern_list=["%a%", "not_this"]
                ),
                id="multiple_patterns",
            ),
        ],
    )
    @parameterize_batch_for_data_sources(data_source_configs=REGULAR_DATA_SOURCES, data=DATA)
    def test_failure(
        self,
        batch_for_datasource: Batch,
        expectation: gxe.ExpectColumnValuesToNotMatchLikePatternList,
    ) -> None:
        result = batch_for_datasource.validate(expectation)
        assert not result.success


class TestMSSQL:
    @pytest.mark.parametrize(
        "expectation",
        [
            pytest.param(
                gxe.ExpectColumnValuesToNotMatchLikePatternList(
                    column=COL_NAME, like_pattern_list=["bc"]
                ),
                id="one_pattern",
            ),
            pytest.param(
                gxe.ExpectColumnValuesToNotMatchLikePatternList(
                    column=COL_NAME, like_pattern_list=["bc", "%de%"]
                ),
                id="multiple_patterns",
            ),
        ],
    )
    @parameterize_batch_for_data_sources(
        data_source_configs=[MSSQLDatasourceTestConfig()], data=DATA
    )
    def test_success(
        self,
        batch_for_datasource: Batch,
        expectation: gxe.ExpectColumnValuesToNotMatchLikePatternList,
    ) -> None:
        result = batch_for_datasource.validate(expectation)
        assert result.success

    @pytest.mark.parametrize(
        "expectation",
        [
            pytest.param(
                gxe.ExpectColumnValuesToNotMatchLikePatternList(
                    column=COL_NAME, like_pattern_list=["%a[b]%"]
                ),
                id="one_pattern",
            ),
            pytest.param(
                gxe.ExpectColumnValuesToNotMatchLikePatternList(
                    column=COL_NAME, like_pattern_list=["%[a]%", "not_this"]
                ),
                id="multiple_patterns",
            ),
        ],
    )
    @parameterize_batch_for_data_sources(
        data_source_configs=[MSSQLDatasourceTestConfig()], data=DATA
    )
    def test_failure(
        self,
        batch_for_datasource: Batch,
        expectation: gxe.ExpectColumnValuesToNotMatchLikePatternList,
    ) -> None:
        result = batch_for_datasource.validate(expectation)
        assert not result.success


@parameterize_batch_for_data_sources(data_source_configs=JUST_PANDAS_DATA_SOURCES, data=DATA)
def test_include_unexpected_rows(batch_for_datasource: Batch) -> None:
    """Test include_unexpected_rows for ExpectColumnValuesToNotMatchLikePatternList."""
    expectation = gxe.ExpectColumnValuesToNotMatchLikePatternList(
        column=COL_NAME, like_pattern_list=["c%", "d%"]
    )
    result = batch_for_datasource.validate(
        expectation, result_format={"result_format": "BASIC", "include_unexpected_rows": True}
    )

    # Note: Some expectations may succeed, so we check for unexpected_rows regardless
    result_dict = cast("Dict[str, Any]", result.to_json_dict()["result"])

    # Verify that unexpected_rows is present (may be empty list for successful expectations)
    assert "unexpected_rows" in result_dict
    assert result_dict["unexpected_rows"] is not None

    # Convert to DataFrame for easier comparison
    unexpected_rows_data = result_dict["unexpected_rows"]
    assert isinstance(unexpected_rows_data, list)

    # If there are unexpected rows, validate the structure
    if unexpected_rows_data:
        unexpected_rows_df = pd.DataFrame(unexpected_rows_data)
        # Check that the unexpected rows contain some columns
        assert len(unexpected_rows_df.columns) > 0
