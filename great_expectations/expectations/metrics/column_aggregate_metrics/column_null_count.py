from __future__ import annotations

from great_expectations.compatibility.sqlalchemy import sqlalchemy as sa
from great_expectations.execution_engine import (
    SqlAlchemyExecutionEngine,
)
from great_expectations.expectations.metrics.column_aggregate_metric_provider import (
    ColumnAggregateMetricProvider,
    column_aggregate_partial,
)


class ColumnNullCount(ColumnAggregateMetricProvider):
    metric_name = "column.null_count"
    value_keys = ()

    # TODO - Investigate whether we want to use column_aggregate_partial or another decorator
    #        Maybe doing a NotNull metric count would be better
    #        Another alternative would be to have a percent null metric
    @column_aggregate_partial(engine=SqlAlchemyExecutionEngine)
    def _sqlalchemy(cls, column, **kwargs):
        # This counts all rows and subtracts rows where the column is not null, effectively giving null count.
        return sa.func.count() - sa.func.count(column)

    # TODO - Validate these work and fix if they don't
    #       Investigate whether we can use column_aggregate_partial or another decorator
    # @column_aggregate_partial(engine=PandasExecutionEngine)
    # def _pandas(cls, column, **kwargs):
    #     return column.isnull().sum()

    # @column_aggregate_partial(engine=SparkDFExecutionEngine)
    # def _spark(cls, column, **kwargs):
    #     # Do this import above:
    #     # from great_expectations.compatibility.pyspark import functions as F
    #     return F.sum(column.isNull().cast("int"))
