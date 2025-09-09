"""
Integration layer for the new row conditions API.

This module provides utilities to integrate the new strongly typed row conditions
with the existing execution engine infrastructure.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Union

from great_expectations.expectations.model_field_types import (
    CONDITION_PARSER_GREAT_EXPECTATIONS,
    CONDITION_PARSER_GREAT_EXPECTATIONS_DEPRECATED,
    CONDITION_PARSER_PANDAS,
    CONDITION_PARSER_SPARK,
)
from great_expectations.expectations.row_conditions_v2 import BaseRowCondition

if TYPE_CHECKING:
    from great_expectations.compatibility import pyspark, sqlalchemy


def apply_row_condition_to_domain_kwargs(
    domain_kwargs: Dict[str, Any],
    row_condition: Union[BaseRowCondition, str, None],
    condition_parser: Union[str, None] = None,
) -> Dict[str, Any]:
    """
    Apply row condition to domain kwargs, supporting both old and new APIs.

    This function serves as a bridge between the old string-based row conditions
    and the new strongly typed row conditions.

    Args:
        domain_kwargs: The domain kwargs dictionary to modify
        row_condition: Either a BaseRowCondition instance (new API) or string (old API)
        condition_parser: The condition parser type (only needed for old API)

    Returns:
        Modified domain_kwargs with appropriate row condition fields set

    Raises:
        ValueError: If using old API without proper condition_parser
    """
    if row_condition is None:
        return domain_kwargs

    # Make a copy to avoid modifying the original
    result_kwargs = domain_kwargs.copy()

    if isinstance(row_condition, BaseRowCondition):
        # New API: Store the condition object and mark it as v2
        result_kwargs["row_condition_v2"] = row_condition
        result_kwargs["row_condition"] = None  # Clear old field
        result_kwargs["condition_parser"] = None  # Not needed with v2
    else:
        # Old API: Keep existing behavior
        if condition_parser is None:
            raise ValueError(
                "condition_parser is required when using string-based row_condition. "
                "Consider migrating to the new row condition API for better portability."
            )
        result_kwargs["row_condition"] = row_condition
        result_kwargs["condition_parser"] = condition_parser
        result_kwargs["row_condition_v2"] = None  # Clear new field

    return result_kwargs


def get_pandas_query_from_domain_kwargs(domain_kwargs: Dict[str, Any]) -> Union[str, None]:
    """
    Extract pandas query string from domain kwargs, supporting both APIs.

    Args:
        domain_kwargs: Domain kwargs that may contain row conditions

    Returns:
        Pandas query string or None if no row condition

    Raises:
        ValueError: If old API is used with non-pandas condition parser
    """
    # Check for new API first
    row_condition_v2 = domain_kwargs.get("row_condition_v2")
    if row_condition_v2 is not None:
        if isinstance(row_condition_v2, BaseRowCondition):
            return row_condition_v2.to_pandas_query()
        else:
            raise ValueError("row_condition_v2 must be a BaseRowCondition instance")

    # Fall back to old API
    row_condition = domain_kwargs.get("row_condition")
    if row_condition is not None:
        condition_parser = domain_kwargs.get("condition_parser")
        if condition_parser == CONDITION_PARSER_PANDAS:
            return row_condition
        else:
            raise ValueError(
                f"Cannot convert condition_parser '{condition_parser}' to pandas query. "
                "Use row_condition_v2 for cross-engine compatibility."
            )

    return None


def get_spark_column_from_domain_kwargs(
    domain_kwargs: Dict[str, Any],
) -> Union[pyspark.Column, None]:
    """
    Extract Spark Column from domain kwargs, supporting both APIs.

    Args:
        domain_kwargs: Domain kwargs that may contain row conditions

    Returns:
        Spark Column or None if no row condition

    Raises:
        ValueError: If old API is used with unsupported condition parser
    """
    # Import here to avoid circular imports
    from great_expectations.expectations.row_conditions import (
        parse_condition_to_spark,
    )

    # Check for new API first
    row_condition_v2 = domain_kwargs.get("row_condition_v2")
    if row_condition_v2 is not None:
        if isinstance(row_condition_v2, BaseRowCondition):
            return row_condition_v2.to_spark_column()
        else:
            raise ValueError("row_condition_v2 must be a BaseRowCondition instance")

    # Fall back to old API
    row_condition = domain_kwargs.get("row_condition")
    if row_condition is not None:
        condition_parser = domain_kwargs.get("condition_parser")
        if condition_parser == CONDITION_PARSER_SPARK:
            # For old Spark parser, pass through the raw condition
            # This maintains backward compatibility
            return row_condition  # This should be a Spark Column already
        elif condition_parser in [
            CONDITION_PARSER_GREAT_EXPECTATIONS,
            CONDITION_PARSER_GREAT_EXPECTATIONS_DEPRECATED,
        ]:
            return parse_condition_to_spark(row_condition)
        else:
            raise ValueError(
                f"Cannot convert condition_parser '{condition_parser}' to Spark Column. "
                "Use row_condition_v2 for cross-engine compatibility."
            )

    return None


def get_sqlalchemy_expression_from_domain_kwargs(
    domain_kwargs: Dict[str, Any],
) -> Union[sqlalchemy.ColumnElement, None]:
    """
    Extract SQLAlchemy expression from domain kwargs, supporting both APIs.

    Args:
        domain_kwargs: Domain kwargs that may contain row conditions

    Returns:
        SQLAlchemy ColumnElement or None if no row condition

    Raises:
        ValueError: If old API is used with unsupported condition parser
    """
    # Import here to avoid circular imports
    from great_expectations.expectations.row_conditions import (
        parse_condition_to_sqlalchemy,
    )

    # Check for new API first
    row_condition_v2 = domain_kwargs.get("row_condition_v2")
    if row_condition_v2 is not None:
        if isinstance(row_condition_v2, BaseRowCondition):
            return row_condition_v2.to_sqlalchemy_expression()
        else:
            raise ValueError("row_condition_v2 must be a BaseRowCondition instance")

    # Fall back to old API
    row_condition = domain_kwargs.get("row_condition")
    if row_condition is not None:
        condition_parser = domain_kwargs.get("condition_parser")
        if condition_parser in [
            CONDITION_PARSER_GREAT_EXPECTATIONS,
            CONDITION_PARSER_GREAT_EXPECTATIONS_DEPRECATED,
        ]:
            return parse_condition_to_sqlalchemy(row_condition)
        else:
            raise ValueError(
                f"Cannot convert condition_parser '{condition_parser}' to SQLAlchemy expression. "
                "Use row_condition_v2 for cross-engine compatibility."
            )

    return None


def has_row_condition(domain_kwargs: Dict[str, Any]) -> bool:
    """
    Check if domain kwargs contain any row condition (old or new API).

    Args:
        domain_kwargs: Domain kwargs to check

    Returns:
        True if any row condition is present
    """
    return (
        domain_kwargs.get("row_condition_v2") is not None
        or domain_kwargs.get("row_condition") is not None
    )


def get_row_condition_description(domain_kwargs: Dict[str, Any]) -> Union[str, None]:
    """
    Get a human-readable description of the row condition.

    Args:
        domain_kwargs: Domain kwargs that may contain row conditions

    Returns:
        Human-readable description or None if no row condition
    """
    # Check for new API first
    row_condition_v2 = domain_kwargs.get("row_condition_v2")
    if row_condition_v2 is not None:
        if isinstance(row_condition_v2, BaseRowCondition):
            # Use pandas query as a readable representation
            try:
                return f"where {row_condition_v2.to_pandas_query()}"
            except Exception:
                return "where <complex condition>"
        else:
            return "where <invalid condition>"

    # Fall back to old API
    row_condition = domain_kwargs.get("row_condition")
    if row_condition is not None:
        condition_parser = domain_kwargs.get("condition_parser")
        if condition_parser == CONDITION_PARSER_PANDAS or condition_parser in [
            CONDITION_PARSER_GREAT_EXPECTATIONS,
            CONDITION_PARSER_GREAT_EXPECTATIONS_DEPRECATED,
        ]:
            return f"where {row_condition}"
        elif condition_parser == CONDITION_PARSER_SPARK:
            return "where <spark condition>"
        else:
            return f"where <{condition_parser} condition>"

    return None


# Utility functions for migration
def migrate_string_condition_to_v2(
    condition_string: str, condition_parser: str
) -> BaseRowCondition:
    """
    Migrate a string-based condition to the new v2 API.

    This is a best-effort migration that handles common cases.
    Complex conditions may need manual migration.

    Args:
        condition_string: The old condition string
        condition_parser: The old condition parser type

    Returns:
        BaseRowCondition instance

    Raises:
        ValueError: If migration is not possible
    """
    from great_expectations.expectations.row_conditions_v2 import (
        col,
        eq,
        ge,
        gt,
        is_not_null,
        is_null,
        le,
        lt,
        ne,
    )

    # This is a simplified migration for demonstration
    # A full implementation would need more sophisticated parsing

    if condition_parser == CONDITION_PARSER_PANDAS:
        # Try to parse simple pandas conditions
        condition_string = condition_string.strip()

        # Handle simple comparisons like "age > 18"
        for op in [">=", "<=", "==", "!=", ">", "<"]:
            if op in condition_string:
                parts = condition_string.split(op, 1)
                if len(parts) == 2:
                    column_name = parts[0].strip()
                    value_str = parts[1].strip()

                    # Try to parse the value
                    final_value: Union[str, int, float]
                    try:
                        if (value_str.startswith('"') and value_str.endswith('"')) or (
                            value_str.startswith("'") and value_str.endswith("'")
                        ):
                            final_value = value_str[1:-1]  # Remove quotes
                        elif "." in value_str:
                            final_value = float(value_str)
                        else:
                            final_value = int(value_str)
                    except ValueError:
                        final_value = value_str  # Keep as string

                    # Create the appropriate condition
                    column = col(column_name)
                    if op == "==":
                        return eq(column, final_value)
                    elif op == "!=":
                        return ne(column, final_value)
                    elif op == "<":
                        return lt(column, final_value)
                    elif op == "<=":
                        return le(column, final_value)
                    elif op == ">":
                        return gt(column, final_value)
                    elif op == ">=":
                        return ge(column, final_value)

        # Handle null checks like "column.isna()" or "column.notna()"
        if ".isna()" in condition_string:
            column_name = condition_string.replace(".isna()", "").strip()
            return is_null(col(column_name))
        elif ".notna()" in condition_string:
            column_name = condition_string.replace(".notna()", "").strip()
            return is_not_null(col(column_name))

    elif condition_parser in [
        CONDITION_PARSER_GREAT_EXPECTATIONS,
        CONDITION_PARSER_GREAT_EXPECTATIONS_DEPRECATED,
    ]:
        # Try to parse GE conditions like 'col("age") > 18'
        from great_expectations.expectations.row_conditions import (
            _parse_great_expectations_condition,
        )

        try:
            parsed = _parse_great_expectations_condition(condition_string)
            column_name = parsed["column"]
            column = col(column_name)

            if parsed.get("notnull"):
                return is_not_null(column)
            elif "op" in parsed:
                op = parsed["op"]
                condition_value: Union[str, int, float]
                if "condition_value" in parsed:
                    condition_value = parsed["condition_value"]
                elif "fnumber" in parsed:
                    value_str = parsed["fnumber"]
                    try:
                        condition_value = (
                            int(value_str) if value_str.isdigit() else float(value_str)
                        )
                    except ValueError:
                        condition_value = value_str
                else:
                    raise ValueError(f"Cannot determine value from parsed condition: {parsed}")

                # Create the appropriate condition
                if op == "==":
                    return eq(column, condition_value)
                elif op == "!=":
                    return ne(column, condition_value)
                elif op == "<":
                    return lt(column, condition_value)
                elif op == "<=":
                    return le(column, condition_value)
                elif op == ">":
                    return gt(column, condition_value)
                elif op == ">=":
                    return ge(column, condition_value)

        except Exception as e:
            raise ValueError(f"Cannot migrate GE condition '{condition_string}': {e}")

    # If we get here, migration failed
    raise ValueError(
        f"Cannot migrate condition '{condition_string}' with parser '{condition_parser}'. "
        "Manual migration to row_condition_v2 may be required."
    )
