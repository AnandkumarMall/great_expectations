from great_expectations.metrics.column import ColumnMetric
from great_expectations.metrics.metric_results import MetricResult


# TODO: Maybe we can update null_count.py instead of introducing this.
class ColumnAggregateNullCountResult(MetricResult[int]): ...


class ColumnAggregateNullCount(ColumnMetric[ColumnAggregateNullCountResult]):
    """Count of null values in a column"""

    name = "column.null_count"
