from unittest import mock
from uuid import uuid4

import pytest

from great_expectations.core.types import Comparable
from great_expectations.metrics import Metric
from great_expectations.metrics.domain import ColumnMap
from great_expectations.validator.metric_configuration import MetricConfiguration

BATCH_ID = str(uuid4())
TABLE = "my_table"
COLUMN = "my_column"

MOCK_METRIC_REGISTRY = {
    ColumnMap: ("above",),
}
FULLY_QUALIFIED_METRIC_NAME = "column_values.above"


class TestMetric:
    def test_metric_instantiation_raises(self):
        with pytest.raises(TypeError):
            Metric(ColumnMap(batch_id=BATCH_ID, table=TABLE, column=COLUMN))


class TestMetricDefinition:
    def test_success(self):
        with mock.patch("great_expectations.metrics.metric.METRIC_REGISTRY", MOCK_METRIC_REGISTRY):

            class Above(Metric[ColumnMap]):
                min_value: Comparable
                strict_min: bool = False

    def test_missing_domain_generic_raises(self):
        with pytest.raises(TypeError):

            class Above(Metric):
                min_value: Comparable
                strict_min: bool = False

    def test_unregistered_metric_raises(self):
        with pytest.raises(TypeError):

            class Above(Metric[ColumnMap]):
                min_value: Comparable
                strict_min: bool = False


class TestMetricInstantiation:
    with mock.patch("great_expectations.metrics.metric.METRIC_REGISTRY", MOCK_METRIC_REGISTRY):

        class Above(Metric[ColumnMap]):
            min_value: Comparable
            strict_min: bool = False

    def test_instantiation_success_positional_domain(self):
        self.Above(
            ColumnMap(
                batch_id=BATCH_ID,
                table=TABLE,
                column=COLUMN,
            ),
            min_value=42,
        )

    def test_instantiation_success_keyword_domain(self):
        self.Above(
            domain=ColumnMap(
                batch_id=BATCH_ID,
                table=TABLE,
                column=COLUMN,
            ),
            min_value=42,
        )

    def test_instantiation_missing_domain_raises(self):
        with pytest.raises(TypeError):
            self.Above(min_value=42)


class TestMetricToConfig:
    with mock.patch("great_expectations.metrics.metric.METRIC_REGISTRY", MOCK_METRIC_REGISTRY):

        class Above(Metric[ColumnMap]):
            min_value: Comparable
            strict_min: bool = False

    def test_success(self):
        expected_config = MetricConfiguration(
            metric_name=FULLY_QUALIFIED_METRIC_NAME,
            metric_domain_kwargs={
                "batch_id": BATCH_ID,
                "table": TABLE,
                "row_condition": None,
                "column": COLUMN,
            },
            metric_value_kwargs={
                "min_value": 42,
                "strict_min": False,
            },
        )

        metric = self.Above(
            ColumnMap(
                batch_id=BATCH_ID,
                table=TABLE,
                column=COLUMN,
            ),
            min_value=42,
        )
        actual_config = metric.to_config()

        assert actual_config.metric_name == expected_config.metric_name
        assert actual_config.metric_domain_kwargs == expected_config.metric_domain_kwargs
        assert actual_config.metric_value_kwargs == expected_config.metric_value_kwargs
