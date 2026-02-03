from typing import List

from great_expectations.metrics.column import ColumnMetric
from great_expectations.metrics.metric_results import MetricResult


class ColumnDistinctValuesMissingFromSetCountResult(MetricResult[int]): ...


class ColumnDistinctValuesMissingFromSetCount(
    ColumnMetric[ColumnDistinctValuesMissingFromSetCountResult]
):
    """Count of expected values that are missing from the column.

    This is used to efficiently determine if the column contains all expected values,
    without fetching all distinct values.
    """

    name = "column.distinct_values.missing_from_set.count"
    value_set: List
