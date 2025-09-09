"""
Example integration of the new row conditions API with execution engines.

This module shows how the execution engines would be updated to support
the new unified row condition API while maintaining backward compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from great_expectations.exceptions import GreatExpectationsError
from great_expectations.expectations.row_conditions_integration import (
    get_pandas_query_from_domain_kwargs,
    get_spark_column_from_domain_kwargs,
    get_sqlalchemy_expression_from_domain_kwargs,
    has_row_condition,
)

if TYPE_CHECKING:
    import pandas as pd

    from great_expectations.compatibility import pyspark, sqlalchemy


def apply_row_condition_pandas(data: pd.DataFrame, domain_kwargs: Dict[str, Any]) -> pd.DataFrame:
    """
    Apply row condition filtering to a pandas DataFrame.

    This function replaces the existing row condition logic in PandasExecutionEngine
    and supports both old and new row condition APIs.

    Args:
        data: The pandas DataFrame to filter
        domain_kwargs: Domain kwargs that may contain row conditions

    Returns:
        Filtered DataFrame

    Raises:
        GreatExpectationsError: If row condition cannot be applied
    """
    if not has_row_condition(domain_kwargs):
        return data

    try:
        query_string = get_pandas_query_from_domain_kwargs(domain_kwargs)
        if query_string:
            return data.query(query_string)
        else:
            return data
    except Exception as e:
        raise GreatExpectationsError(
            f"Failed to apply row condition to pandas DataFrame: {e}"
        ) from e


def apply_row_condition_spark(
    data: pyspark.DataFrame, domain_kwargs: Dict[str, Any]
) -> pyspark.DataFrame:
    """
    Apply row condition filtering to a Spark DataFrame.

    This function replaces the existing row condition logic in SparkDFExecutionEngine
    and supports both old and new row condition APIs.

    Args:
        data: The Spark DataFrame to filter
        domain_kwargs: Domain kwargs that may contain row conditions

    Returns:
        Filtered DataFrame

    Raises:
        GreatExpectationsError: If row condition cannot be applied
    """
    if not has_row_condition(domain_kwargs):
        return data

    try:
        condition_column = get_spark_column_from_domain_kwargs(domain_kwargs)
        if condition_column is not None:
            return data.filter(condition_column)
        else:
            return data
    except Exception as e:
        raise GreatExpectationsError(
            f"Failed to apply row condition to Spark DataFrame: {e}"
        ) from e


def apply_row_condition_sqlalchemy(
    selectable: sqlalchemy.Selectable, domain_kwargs: Dict[str, Any]
) -> sqlalchemy.Selectable:
    """
    Apply row condition filtering to a SQLAlchemy selectable.

    This function replaces the existing row condition logic in SqlAlchemyExecutionEngine
    and supports both old and new row condition APIs.

    Args:
        selectable: The SQLAlchemy selectable to filter
        domain_kwargs: Domain kwargs that may contain row conditions

    Returns:
        Filtered selectable

    Raises:
        GreatExpectationsError: If row condition cannot be applied
    """
    from great_expectations.compatibility.sqlalchemy import sqlalchemy as sa

    if not has_row_condition(domain_kwargs):
        return selectable

    try:
        condition_expr = get_sqlalchemy_expression_from_domain_kwargs(domain_kwargs)
        if condition_expr is not None:
            return sa.select(sa.text("*")).select_from(selectable).where(condition_expr)
        else:
            return selectable
    except Exception as e:
        raise GreatExpectationsError(
            f"Failed to apply row condition to SQLAlchemy selectable: {e}"
        ) from e


# Example of how the execution engines would be updated
class ExampleUpdatedPandasExecutionEngine:
    """
    Example showing how PandasExecutionEngine.get_domain_records would be updated.

    This is not a complete implementation, just showing the key changes needed.
    """

    def get_domain_records(self, domain_kwargs: Dict[str, Any]) -> pd.DataFrame:
        """Updated version of get_domain_records with new row condition support."""
        # ... existing logic for getting base data ...
        data = self._get_base_data(domain_kwargs)  # Placeholder

        # NEW: Use the unified row condition application
        data = apply_row_condition_pandas(data, domain_kwargs)

        # ... rest of existing logic ...
        return data

    def _get_base_data(self, domain_kwargs: Dict[str, Any]) -> pd.DataFrame:
        """Placeholder for existing data retrieval logic."""
        import pandas as pd

        return pd.DataFrame()  # Placeholder


class ExampleUpdatedSparkExecutionEngine:
    """
    Example showing how SparkDFExecutionEngine.get_domain_records would be updated.
    """

    def get_domain_records(self, domain_kwargs: Dict[str, Any]) -> pyspark.DataFrame:
        """Updated version of get_domain_records with new row condition support."""
        # ... existing logic for getting base data ...
        data = self._get_base_data(domain_kwargs)  # Placeholder

        # NEW: Use the unified row condition application
        data = apply_row_condition_spark(data, domain_kwargs)

        # ... rest of existing logic ...
        return data

    def _get_base_data(self, domain_kwargs: Dict[str, Any]) -> pyspark.DataFrame:
        """Placeholder for existing data retrieval logic."""
        from pyspark.sql import SparkSession

        spark = SparkSession.getActiveSession()
        return spark.createDataFrame([], "")  # Placeholder


class ExampleUpdatedSqlAlchemyExecutionEngine:
    """
    Example showing how SqlAlchemyExecutionEngine.get_domain_records would be updated.
    """

    def get_domain_records(self, domain_kwargs: Dict[str, Any]) -> sqlalchemy.Selectable:
        """Updated version of get_domain_records with new row condition support."""
        # ... existing logic for getting base selectable ...
        selectable = self._get_base_selectable(domain_kwargs)  # Placeholder

        # NEW: Use the unified row condition application
        selectable = apply_row_condition_sqlalchemy(selectable, domain_kwargs)

        # ... rest of existing logic ...
        return selectable

    def _get_base_selectable(self, domain_kwargs: Dict[str, Any]) -> sqlalchemy.Selectable:
        """Placeholder for existing selectable creation logic."""
        from great_expectations.compatibility.sqlalchemy import sqlalchemy as sa

        return sa.text("SELECT 1")  # Placeholder


# Migration utilities for existing expectations
def update_expectation_with_row_condition_v2(
    expectation_config: Dict[str, Any],
    row_condition_v2: Any,  # BaseRowCondition
) -> Dict[str, Any]:
    """
    Update an expectation configuration to use the new row condition API.

    Args:
        expectation_config: Existing expectation configuration
        row_condition_v2: New row condition object

    Returns:
        Updated expectation configuration
    """
    updated_config = expectation_config.copy()

    # Update kwargs
    if "kwargs" not in updated_config:
        updated_config["kwargs"] = {}

    # Set new row condition
    updated_config["kwargs"]["row_condition_v2"] = row_condition_v2

    # Clear old row condition fields
    updated_config["kwargs"].pop("row_condition", None)
    updated_config["kwargs"].pop("condition_parser", None)

    return updated_config


def validate_row_condition_compatibility(expectation_config: Dict[str, Any]) -> Dict[str, str]:
    """
    Validate that row conditions in an expectation are compatible across engines.

    Args:
        expectation_config: Expectation configuration to validate

    Returns:
        Dictionary with validation results and recommendations
    """
    kwargs = expectation_config.get("kwargs", {})

    # Check if using new API
    if "row_condition_v2" in kwargs:
        return {
            "status": "compatible",
            "message": "Using new unified row condition API - compatible across all engines",
            "recommendation": "No action needed",
        }

    # Check old API
    row_condition = kwargs.get("row_condition")
    condition_parser = kwargs.get("condition_parser")

    if row_condition is None:
        return {
            "status": "no_condition",
            "message": "No row condition specified",
            "recommendation": "No action needed",
        }

    if condition_parser is None:
        return {
            "status": "error",
            "message": "row_condition specified without condition_parser",
            "recommendation": "Add condition_parser or migrate to row_condition_v2",
        }

    # Check compatibility
    if condition_parser == "pandas":
        return {
            "status": "limited",
            "message": "Row condition only works with pandas execution engine",
            "recommendation": "Migrate to row_condition_v2 for cross-engine compatibility",
        }
    elif condition_parser == "spark":
        return {
            "status": "limited",
            "message": "Row condition only works with Spark execution engine",
            "recommendation": "Migrate to row_condition_v2 for cross-engine compatibility",
        }
    elif condition_parser in ["great_expectations", "great_expectations__experimental__"]:
        return {
            "status": "partial",
            "message": "Row condition works with Spark and SQL engines but not pandas",
            "recommendation": "Migrate to row_condition_v2 for full cross-engine compatibility",
        }
    else:
        return {
            "status": "unknown",
            "message": f"Unknown condition_parser: {condition_parser}",
            "recommendation": "Migrate to row_condition_v2",
        }
