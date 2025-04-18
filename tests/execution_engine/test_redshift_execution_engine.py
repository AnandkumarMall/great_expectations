from unittest.mock import Mock

import pytest
from sqlalchemy.sql.sqltypes import BOOLEAN, CHAR, INTEGER, VARCHAR

from great_expectations.execution_engine.redshift_execution_engine import RedshiftExecutionEngine
from great_expectations.validator.computed_metric import MetricValue
from great_expectations.validator.metric_configuration import (
    MetricConfiguration,
    MetricConfigurationID,
)


@pytest.mark.unit
def test_redshift_execution_engine_resolve_metrics():
    # arrange
    engine = RedshiftExecutionEngine(
        connection_string="redshift+psycopg2://foo:bar@baz:5439/dev?sslmode=require"
    )

    # Create a mock for the batch_manager
    batch_manager_mock = Mock()
    # Create a mock for the active_batch property
    active_batch_mock = Mock()
    # Set the active_batch property to return our mock
    batch_manager_mock.active_batch = active_batch_mock

    # Assign the mock to the engine
    engine._batch_manager = batch_manager_mock

    engine.raw_connection = Mock()

    metric = MetricConfiguration(
        metric_name="table.column_types",
        metric_domain_kwargs={},
        metric_value_kwargs={"include_nested": True},
    )

    mock_query_result_set = [
        ("foo", "boolean", None),
        ("bar", "integer", None),
        ("baz", "character", 14),
        ("qux", "character varying", 100),
    ]

    engine.execute_query = Mock(return_value=mock_query_result_set)

    #  act
    resolved_metrics: dict[MetricConfigurationID, MetricValue] = engine.resolve_metrics(
        metrics_to_resolve={metric},
        metrics={},
        runtime_configuration={"catch_exceptions": True},
    )

    # assert
    assert resolved_metrics

    # Get the actual metric ID from the resolved_metrics dictionary
    actual_metric_id = next(iter(resolved_metrics.keys()))

    # Get the actual result
    actual_result = resolved_metrics[actual_metric_id]

    # Check that the resolved_metrics dictionary contains the expected value
    # by comparing string representations of the types
    assert len(actual_result) == 4

    # Check each column type individually
    assert actual_result[0]["name"] == "foo"
    assert str(actual_result[0]["type"]) == str(BOOLEAN())

    assert actual_result[1]["name"] == "bar"
    assert str(actual_result[1]["type"]) == str(INTEGER())

    assert actual_result[2]["name"] == "baz"
    assert str(actual_result[2]["type"]) == str(CHAR(length=14))

    assert actual_result[3]["name"] == "qux"
    assert str(actual_result[3]["type"]) == str(VARCHAR(length=100))
