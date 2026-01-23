from typing import Any

from great_expectations.metrics.column import ColumnMetric
from great_expectations.metrics.metric_results import MetricResult


class ColumnDistinctValuesNotEqualSetResult(MetricResult[dict[str, list[Any]]]): ...


class ColumnDistinctValuesNotEqualSet(ColumnMetric[ColumnDistinctValuesNotEqualSetResult]):
    """Values that differ between column and expected set.

    Returns a dictionary with two keys:
    - "in_column_not_in_set": values in column but not in expected set
    - "in_set_not_in_column": values in expected set but not in column

    Used for expect_column_distinct_values_to_equal_set to check bidirectional differences.

    Args:
        value_set: The set of expected values
        limit: Maximum number of differing values to return in each list (default: 20)
    """

    name = "column.distinct_values.not_equal_set"
    value_set: list[Any]
    limit: int = 20
