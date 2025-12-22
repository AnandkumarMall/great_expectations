from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from great_expectations.core.result_format import ResultFormat
from great_expectations.data_context.util import file_relative_path
from great_expectations.expectations import UnexpectedRowsExpectation
from great_expectations.expectations.metrics.util import MAX_RESULT_RECORDS
from great_expectations.render.renderer.content_block.content_block import ContentBlockRenderer

if TYPE_CHECKING:
    from great_expectations.data_context import AbstractDataContext
    from great_expectations.datasource.fluent.interfaces import Batch
    from great_expectations.datasource.fluent.sqlite_datasource import SqliteDatasource


@pytest.fixture
def taxi_db_path() -> str:
    return file_relative_path(__file__, "../../test_sets/quickstart/yellow_tripdata.db")


@pytest.fixture
def sqlite_datasource(
    in_memory_runtime_context: AbstractDataContext, taxi_db_path: str
) -> SqliteDatasource:
    context = in_memory_runtime_context
    datasource_name = "my_sqlite_datasource"
    return context.data_sources.add_sqlite(
        datasource_name, connection_string=f"sqlite:///{taxi_db_path}"
    )


@pytest.fixture
def sqlite_batch(sqlite_datasource: SqliteDatasource) -> Batch:
    datasource = sqlite_datasource
    asset = datasource.add_table_asset("yellow_tripdata_sample_2022_01")

    batch_request = asset.build_batch_request()
    return asset.get_batch(batch_request)


@pytest.mark.unit
@pytest.mark.parametrize(
    "query",
    [
        pytest.param("SELECT * FROM table", id="no batch"),
        pytest.param("SELECT * FROM {{ batch }}", id="invalid format"),
        pytest.param("SELECT * FROM {active_batch}", id="legacy syntax"),
    ],
)
def test_unexpected_rows_expectation_invalid_query_info_message(query: str, caplog, capfd):
    # info log is emitted
    with caplog.at_level(logging.INFO):
        UnexpectedRowsExpectation(unexpected_rows_query=query)

    # stdout is printed to console
    out, _ = capfd.readouterr()
    assert "{batch}" in out


@pytest.mark.sqlite
@pytest.mark.parametrize(
    "query, expected_success, expected_observed_value, expected_count_unexpected_rows_returned",
    [
        pytest.param(
            "SELECT * FROM {batch} WHERE passenger_count > 7",
            True,
            0,
            0,
            id="success",
        ),
        pytest.param(
            # There is a single instance where passenger_count == 7
            "SELECT * FROM {batch} WHERE passenger_count > 6",
            False,
            1,
            1,
            id="failure",
        ),
        pytest.param(
            "SELECT * FROM {batch} WHERE passenger_count > 0",
            False,
            97853,
            MAX_RESULT_RECORDS,
            id="greater than MAX_RESULT_RECORDS unexpected rows",
        ),
    ],
)
def test_unexpected_rows_expectation_validate(
    sqlite_batch: Batch,
    query: str,
    expected_success: bool,
    expected_observed_value: int,
    expected_count_unexpected_rows_returned: int,
):
    batch = sqlite_batch

    expectation = UnexpectedRowsExpectation(unexpected_rows_query=query)
    result = batch.validate(expectation)

    assert result.success is expected_success

    res = result.result
    assert res["observed_value"] == expected_observed_value

    unexpected_count_rows_returned = len(res["details"]["unexpected_rows"])
    assert unexpected_count_rows_returned == expected_count_unexpected_rows_returned


@pytest.mark.unit
def test_unexpected_rows_expectation_correctly_interprets_query(
    sqlite_batch: Batch,
):
    query = "SELECT * FROM {batch}\r\n\t  ;\v\r ;"

    expectation = UnexpectedRowsExpectation(unexpected_rows_query=query)

    assert expectation.unexpected_rows_query == "SELECT * FROM {batch}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "description, unexpected_rows_query",
    [
        pytest.param(
            "passenger_count should be less than or equal to 7",
            "SELECT * FROM {batch} WHERE passenger_count > 7",
            id="with description",
        ),
        pytest.param(
            None,
            "SELECT * FROM {batch} WHERE passenger_count > 7",
            id="no description",
        ),
    ],
)
def test_unexpected_rows_expectation_render(
    description: str | None,
    unexpected_rows_query: str,
):
    expectation = UnexpectedRowsExpectation(
        description=description,
        unexpected_rows_query=unexpected_rows_query,
    )
    expectation.render()
    assert (
        expectation.rendered_content[0].value.params.get("unexpected_rows_query").get("value")
        == unexpected_rows_query
    )

    assert expectation.rendered_content[0].value.template == description
    assert (
        expectation.rendered_content[0].value.code_block.get("code_template_str")
        == "$unexpected_rows_query"
    )
    assert expectation.rendered_content[0].value.code_block.get("language") == "sql"


@pytest.mark.unit
def test_data_docs_rendering():
    query = "SELECT * FROM {batch} WHERE passenger_count > 7"
    expectation = UnexpectedRowsExpectation(unexpected_rows_query=query)
    results = ContentBlockRenderer.render(expectation.configuration)
    assert isinstance(results, list) and len(results) == 1
    result = results[0]
    assert result.string_template == {
        "template": "Unexpected rows query: $unexpected_rows_query",
        "params": {"unexpected_rows_query": query},
        "styling": {},
    }


class TestUnexpectedRowsExpectationResultFormat:
    """Test class for UnexpectedRowsExpectation result format behavior."""

    @pytest.mark.sqlite
    @pytest.mark.parametrize(
        "query, expected_success",
        [
            pytest.param(
                "SELECT * FROM {batch} WHERE passenger_count > 6",
                False,
                id="failure_case",
            ),
            pytest.param(
                "SELECT * FROM {batch} WHERE passenger_count > 7",
                True,
                id="success_case",
            ),
        ],
    )
    def test_boolean_only_without_flag(
        self, sqlite_batch: Batch, query: str, expected_success: bool
    ):
        """Test that BOOLEAN_ONLY without return_unexpected_rows/include_unexpected_rows
        doesn't include unexpected_rows."""
        batch = sqlite_batch
        expectation = UnexpectedRowsExpectation(unexpected_rows_query=query)
        result = batch.validate(
            expectation, result_format={"result_format": ResultFormat.BOOLEAN_ONLY}
        )

        assert result.success is expected_success
        # For BOOLEAN_ONLY without flags, result should be empty (post-processing clears it)
        assert result.result == {}

    @pytest.mark.sqlite
    @pytest.mark.parametrize(
        "flag_name, query, expected_success, expected_unexpected_count",
        [
            pytest.param(
                "return_unexpected_rows",
                "SELECT * FROM {batch} WHERE passenger_count > 6",
                False,
                1,
                id="return_unexpected_rows_failure",
            ),
            pytest.param(
                "include_unexpected_rows",
                "SELECT * FROM {batch} WHERE passenger_count > 6",
                False,
                1,
                id="include_unexpected_rows_failure",
            ),
            pytest.param(
                "return_unexpected_rows",
                "SELECT * FROM {batch} WHERE passenger_count > 7",
                True,
                0,
                id="return_unexpected_rows_success",
            ),
            pytest.param(
                "include_unexpected_rows",
                "SELECT * FROM {batch} WHERE passenger_count > 7",
                True,
                0,
                id="include_unexpected_rows_success",
            ),
        ],
    )
    def test_boolean_only_with_flag(
        self,
        sqlite_batch: Batch,
        flag_name: str,
        query: str,
        expected_success: bool,
        expected_unexpected_count: int,
    ):
        """Test that BOOLEAN_ONLY with return_unexpected_rows/include_unexpected_rows=True
        includes unexpected_rows."""
        batch = sqlite_batch
        expectation = UnexpectedRowsExpectation(unexpected_rows_query=query)
        result = batch.validate(
            expectation,
            result_format={
                "result_format": ResultFormat.BOOLEAN_ONLY,
                flag_name: True,
            },
        )

        assert result.success is expected_success
        # For BOOLEAN_ONLY with flag, unexpected_rows should be included
        assert "details" in result.result
        assert "unexpected_rows" in result.result["details"]
        assert len(result.result["details"]["unexpected_rows"]) == expected_unexpected_count

    @pytest.mark.sqlite
    @pytest.mark.parametrize(
        "result_format",
        [
            ResultFormat.BASIC,
            ResultFormat.SUMMARY,
            ResultFormat.COMPLETE,
        ],
    )
    def test_other_formats_always_include_unexpected_rows(
        self, sqlite_batch: Batch, result_format: ResultFormat
    ):
        """Test that other result formats (BASIC, SUMMARY, COMPLETE)
        always include unexpected_rows."""
        batch = sqlite_batch
        query = "SELECT * FROM {batch} WHERE passenger_count > 6"

        expectation = UnexpectedRowsExpectation(unexpected_rows_query=query)
        result = batch.validate(expectation, result_format={"result_format": result_format})

        assert result.success is False
        # For other result formats, unexpected_rows should always be included
        assert "details" in result.result
        assert "unexpected_rows" in result.result["details"]
        assert len(result.result["details"]["unexpected_rows"]) == 1
