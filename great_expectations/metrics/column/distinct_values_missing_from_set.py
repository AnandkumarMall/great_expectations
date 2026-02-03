from typing import List

from great_expectations.metrics.column import ColumnMetric
from great_expectations.metrics.metric_results import MetricResult


class ColumnDistinctValuesMissingFromSetResult(MetricResult[List]): ...


class ColumnDistinctValuesMissingFromSet(ColumnMetric[ColumnDistinctValuesMissingFromSetResult]):
    """List of expected values that are missing from the column.

    This returns values from the expected set that are not present in the column,
    without fetching all distinct values.
    """

    name = "column.distinct_values.missing_from_set"
    value_set: List
    limit: int = 20
