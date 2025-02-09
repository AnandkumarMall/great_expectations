from uuid import uuid4

import pytest

from great_expectations.compatibility.pydantic import ValidationError
from great_expectations.core.types import Comparable
from great_expectations.metrics import Metric
from great_expectations.metrics.domain import ColumnMap

BATCH_ID = str(uuid4())
TABLE = "my_table"
COLUMN = "my_column"


def test_definition_missing_domain_raises():
    class Above(Metric):
        min_value: Comparable
        strict_min: bool = False

        metric_name = "column_values.above"


def test_definition_missing_metric_name_raises():
    with pytest.raises(AttributeError):

        class Above(Metric[ColumnMap]):
            min_value: Comparable
            strict_min: bool = False


def test_definition_empty_string_metric_name_raises():
    with pytest.raises(ValueError):

        class Above(Metric[ColumnMap]):
            min_value: Comparable
            strict_min: bool = False

            metric_name = ""


def test_instantiation_missing_domain_raises():
    class Above(Metric[ColumnMap]):
        min_value: Comparable
        strict_min: bool = False

        metric_name = "column_values.above"

    with pytest.raises(ValidationError):
        Above(min_value=42)
