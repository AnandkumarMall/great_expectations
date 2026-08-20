from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from great_expectations.constants import MAX_RESULT_RECORDS
from great_expectations.execution_engine.duckdb_sql_utils import quote_ident
from great_expectations.expectations.metrics.util import (
    get_dbms_compatible_metric_domain_kwargs,
)

if TYPE_CHECKING:
    from great_expectations.execution_engine import DuckDBExecutionEngine


def _duckdb_map_condition_unexpected_count_aggregate_fn(
    cls,
    execution_engine: DuckDBExecutionEngine,
    metric_domain_kwargs: dict,
    metric_value_kwargs: dict,
    metrics: Dict[str, Any],
    **kwargs,
) -> tuple[str, dict, dict]:
    """Returns unexpected count for MapExpectations, as a bundleable SQL aggregate expression."""
    unexpected_condition, compute_domain_kwargs, accessor_domain_kwargs = metrics[
        "unexpected_condition"
    ]
    return (
        f"SUM(CASE WHEN {unexpected_condition} THEN 1 ELSE 0 END)",
        compute_domain_kwargs,
        accessor_domain_kwargs,
    )


def _duckdb_column_map_condition_values(
    cls,
    execution_engine: DuckDBExecutionEngine,
    metric_domain_kwargs: dict,
    metric_value_kwargs: dict,
    metrics: Dict[str, Any],
    **kwargs,
) -> list:
    """Returns the actual column values which do not meet an expected condition, for
    ColumnMapExpectation Expectations.
    """
    unexpected_condition, compute_domain_kwargs, accessor_domain_kwargs = metrics[
        "unexpected_condition"
    ]

    if "column" not in accessor_domain_kwargs:
        raise ValueError(  # noqa: TRY003 # FIXME CoP
            'No "column" found in provided metric_domain_kwargs, but it is required for a '
            "column map metric (_duckdb_column_map_condition_values)."
        )

    accessor_domain_kwargs = get_dbms_compatible_metric_domain_kwargs(
        metric_domain_kwargs=accessor_domain_kwargs,
        batch_columns_list=metrics["table.columns"],
    )
    column_name: str = accessor_domain_kwargs["column"]

    relation = execution_engine.get_domain_records(domain_kwargs=compute_domain_kwargs)
    filtered = relation.filter(unexpected_condition)

    result_format = metric_value_kwargs["result_format"]
    if result_format["result_format"] != "COMPLETE":
        filtered = filtered.limit(result_format["partial_unexpected_count"])

    rows = filtered.project(quote_ident(column_name)).fetchall()
    return [row[0] for row in rows[:MAX_RESULT_RECORDS]]


def _duckdb_column_map_condition_value_counts(
    cls,
    execution_engine: DuckDBExecutionEngine,
    metric_domain_kwargs: dict,
    metric_value_kwargs: dict,
    metrics: Dict[str, Any],
    **kwargs,
) -> list:
    """Returns value counts for the column values which do not meet an expected condition, for
    ColumnMapExpectation Expectations.
    """
    unexpected_condition, compute_domain_kwargs, accessor_domain_kwargs = metrics[
        "unexpected_condition"
    ]

    if "column" not in accessor_domain_kwargs:
        raise ValueError(  # noqa: TRY003 # FIXME CoP
            'No "column" found in provided metric_domain_kwargs, but it is required for a '
            "column map metric (_duckdb_column_map_condition_value_counts)."
        )

    accessor_domain_kwargs = get_dbms_compatible_metric_domain_kwargs(
        metric_domain_kwargs=accessor_domain_kwargs,
        batch_columns_list=metrics["table.columns"],
    )
    column_name: str = accessor_domain_kwargs["column"]
    col = quote_ident(column_name)

    relation = execution_engine.get_domain_records(domain_kwargs=compute_domain_kwargs)
    filtered = relation.filter(unexpected_condition)

    return filtered.aggregate(f"{col}, COUNT(*) AS unexpected_count", group_expr=col).fetchall()
