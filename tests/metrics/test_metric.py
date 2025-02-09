from uuid import uuid4

import pytest

from great_expectations.core.types import Comparable
from great_expectations.metrics import Metric
from great_expectations.metrics.domain import ColumnMap

BATCH_ID = str(uuid4())
TABLE = "my_table"
COLUMN = "my_column"


class TestMetricDefinition:
    def test_success(self):
        class Above(Metric[ColumnMap]):
            min_value: Comparable
            strict_min: bool = False

            metric_name = "column_values.above"

    def test_missing_domain_raises(self):
        with pytest.raises(TypeError):

            class Above(Metric):
                min_value: Comparable
                strict_min: bool = False

                metric_name = "column_values.above"

    def test_missing_metric_name_raises(self):
        with pytest.raises(AttributeError):

            class Above(Metric[ColumnMap]):
                min_value: Comparable
                strict_min: bool = False

    def test_empty_string_metric_name_raises(self):
        with pytest.raises(ValueError):

            class Above(Metric[ColumnMap]):
                min_value: Comparable
                strict_min: bool = False

                metric_name = ""


class TestMetricInstantiation:
    def test_instantiation_success_positional_domain(self):
        class Above(Metric[ColumnMap]):
            min_value: Comparable
            strict_min: bool = False

            metric_name = "column_values.above"

        Above(
            ColumnMap(
                batch_id=BATCH_ID,
                table=TABLE,
                column=COLUMN,
            ),
            min_value=42,
        )

    def test_instantiation_success_keyword_domain(self):
        class Above(Metric[ColumnMap]):
            min_value: Comparable
            strict_min: bool = False

            metric_name = "column_values.above"

        Above(
            domain=ColumnMap(
                batch_id=BATCH_ID,
                table=TABLE,
                column=COLUMN,
            ),
            min_value=42,
        )

    def test_instantiation_missing_domain_raises(self):
        class Above(Metric[ColumnMap]):
            min_value: Comparable
            strict_min: bool = False

            metric_name = "column_values.above"

        with pytest.raises(TypeError):
            Above(min_value=42)
