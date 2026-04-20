from __future__ import annotations

from great_expectations.compatibility import pyspark
from great_expectations.compatibility.pyspark import functions as F
from great_expectations.compatibility.sqlalchemy import (
    sqlalchemy as sa,
)
from great_expectations.core.metric_function_types import MetricPartialFunctionTypes
from great_expectations.execution_engine import (
    PandasExecutionEngine,
    SparkDFExecutionEngine,
    SqlAlchemyExecutionEngine,
)
from great_expectations.expectations.metrics.map_metric_provider import (
    ColumnMapMetricProvider,
    column_condition_partial,
)


class ColumnValuesUnique(ColumnMapMetricProvider):
    condition_metric_name = "column_values.unique"

    @column_condition_partial(engine=PandasExecutionEngine)
    def _pandas(cls, column, **kwargs):
        return ~column.duplicated(keep=False)

    # NOTE: 20201119 - JPC - We cannot split per-dialect into window and non-window functions
    # @column_condition_partial(
    #     engine=SqlAlchemyExecutionEngine,
    # )
    # def _sqlalchemy(cls, column, _table, **kwargs):
    #     dup_query = (
    #         sa.select(column)
    #         .select_from(_table)
    #         .group_by(column)
    #         .having(sa.func.count(column) > 1)
    #     )
    #
    #     return column.notin_(dup_query)

    @column_condition_partial(
        engine=SqlAlchemyExecutionEngine,
        partial_fn_type=MetricPartialFunctionTypes.WINDOW_CONDITION_FN,
    )
    def _sqlalchemy_window(cls, column, _table, **kwargs):
        # MySQL and SingleStore cannot reference a temp table more than once in the same
        # query, and SingleStore disallows correlated subselects with GROUP BY/HAVING.
        # Use a window function for these dialects to avoid both issues.
        dialect = kwargs.get("_dialect")
        try:
            dialect_name = dialect.dialect.name
        except AttributeError:
            try:
                dialect_name = dialect.name
            except AttributeError:
                dialect_name = ""
        if dialect and dialect_name in ("mysql", "singlestoredb"):
            return sa.func.count(column).over(partition_by=column) <= 1
        else:
            from_clause = _table.subquery() if isinstance(_table, sa.Select) else _table
            dup_query = (
                sa.select(column)
                .select_from(from_clause)
                .group_by(column)
                .having(sa.func.count(column) > 1)
            )
        return column.notin_(dup_query)

    @column_condition_partial(
        engine=SparkDFExecutionEngine,
        partial_fn_type=MetricPartialFunctionTypes.WINDOW_CONDITION_FN,
    )
    def _spark(cls, column, **kwargs):
        return F.count(F.lit(1)).over(pyspark.Window.partitionBy(column)) <= 1
