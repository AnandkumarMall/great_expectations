"""
Unified Row Condition API for Great Expectations

This module provides a strongly typed, execution-engine-agnostic API for row conditions
that can be converted to pandas, Spark, and SQL syntax automatically.
"""

from __future__ import annotations

import abc
import operator
from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Literal, Union

from great_expectations.compatibility.pyspark import functions as F
from great_expectations.compatibility.sqlalchemy import sqlalchemy as sa
from great_expectations.compatibility.typing_extensions import override
from great_expectations.exceptions import GreatExpectationsError
from great_expectations.types import SerializableDictDot
from great_expectations.util import convert_to_json_serializable

if TYPE_CHECKING:
    from great_expectations.compatibility import pyspark, sqlalchemy


class RowConditionError(GreatExpectationsError):
    """Error raised when row condition operations fail."""

    pass


@dataclass
class ColumnReference:
    """Reference to a column in the dataset."""

    name: str

    def __post_init__(self):
        if not self.name or not isinstance(self.name, str):
            raise RowConditionError("Column name must be a non-empty string")


class BaseRowCondition(SerializableDictDot, abc.ABC):
    """Abstract base class for all row conditions.

    Provides a unified interface that can be converted to different execution engine formats.
    """

    @abc.abstractmethod
    def to_pandas_query(self) -> str:
        """Convert condition to pandas DataFrame.query() syntax."""
        pass

    @abc.abstractmethod
    def to_spark_column(self) -> pyspark.Column:
        """Convert condition to PySpark Column expression."""
        pass

    @abc.abstractmethod
    def to_sqlalchemy_expression(self) -> sqlalchemy.ColumnElement:
        """Convert condition to SQLAlchemy expression."""
        pass

    @abc.abstractmethod
    def validate(self) -> None:
        """Validate the condition configuration. Raises RowConditionError if invalid."""
        pass

    @override
    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {"type": self.__class__.__name__, **self._to_dict_impl()}

    @abc.abstractmethod
    def _to_dict_impl(self) -> dict:
        """Implementation-specific dictionary conversion."""
        pass

    @override
    def to_json_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return convert_to_json_serializable(data=self.to_dict())


@dataclass
class ComparisonCondition(BaseRowCondition):
    """Condition that compares a column to a value using an operator."""

    column: ColumnReference
    operator: Literal["==", "!=", "<", "<=", ">", ">="]
    value: Union[str, int, float, bool]

    def __post_init__(self):
        self.validate()

    @override
    def validate(self) -> None:
        """Validate the comparison condition."""
        if not isinstance(self.column, ColumnReference):
            raise RowConditionError("column must be a ColumnReference instance")

        valid_operators = {"==", "!=", "<", "<=", ">", ">="}
        if self.operator not in valid_operators:
            raise RowConditionError(f"operator must be one of {valid_operators}")

        # Validate value type
        if not isinstance(self.value, (str, int, float, bool)):
            raise RowConditionError("value must be a string, number, or boolean")

    @override
    def to_pandas_query(self) -> str:
        """Convert to pandas query syntax."""
        # Handle string values that need quoting
        if isinstance(self.value, str):
            # Escape quotes in the string value
            escaped_value = self.value.replace('"', '\\"')
            value_str = f'"{escaped_value}"'
        else:
            value_str = str(self.value)

        return f"{self.column.name} {self.operator} {value_str}"

    @override
    def to_spark_column(self) -> pyspark.Column:
        """Convert to Spark Column expression."""
        col: pyspark.Column = F.col(self.column.name)
        lit_value = F.lit(self.value)

        operators = {
            "==": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
        }

        return operators[self.operator](col, lit_value)

    @override
    def to_sqlalchemy_expression(self) -> sqlalchemy.ColumnElement:
        """Convert to SQLAlchemy expression."""
        col: sqlalchemy.ColumnElement = sa.column(self.column.name)

        operators = {
            "==": operator.eq,
            "!=": operator.ne,
            "<": operator.lt,
            "<=": operator.le,
            ">": operator.gt,
            ">=": operator.ge,
        }

        return operators[self.operator](col, self.value)

    @override
    def _to_dict_impl(self) -> dict:
        return {"column": self.column.name, "operator": self.operator, "value": self.value}


@dataclass
class NullCheckCondition(BaseRowCondition):
    """Condition that checks if a column is null or not null."""

    column: ColumnReference
    is_null: bool = True  # True for IS NULL, False for IS NOT NULL

    def __post_init__(self):
        self.validate()

    @override
    def validate(self) -> None:
        """Validate the null check condition."""
        if not isinstance(self.column, ColumnReference):
            raise RowConditionError("column must be a ColumnReference instance")

        if not isinstance(self.is_null, bool):
            raise RowConditionError("is_null must be a boolean")

    @override
    def to_pandas_query(self) -> str:
        """Convert to pandas query syntax."""
        if self.is_null:
            return f"{self.column.name}.isna()"
        else:
            return f"{self.column.name}.notna()"

    @override
    def to_spark_column(self) -> pyspark.Column:
        """Convert to Spark Column expression."""
        col: pyspark.Column = F.col(self.column.name)
        if self.is_null:
            return col.isNull()
        else:
            return col.isNotNull()

    @override
    def to_sqlalchemy_expression(self) -> sqlalchemy.ColumnElement:
        """Convert to SQLAlchemy expression."""
        col: sqlalchemy.ColumnElement = sa.column(self.column.name)
        if self.is_null:
            return col.is_(None)
        else:
            return sa.not_(col.is_(None))

    @override
    def _to_dict_impl(self) -> dict:
        return {"column": self.column.name, "is_null": self.is_null}


@dataclass
class InSetCondition(BaseRowCondition):
    """Condition that checks if a column value is in a set of values."""

    column: ColumnReference
    values: List[Union[str, int, float]]
    negate: bool = False  # True for NOT IN, False for IN

    def __post_init__(self):
        self.validate()

    @override
    def validate(self) -> None:
        """Validate the in-set condition."""
        if not isinstance(self.column, ColumnReference):
            raise RowConditionError("column must be a ColumnReference instance")

        if not isinstance(self.values, list) or len(self.values) == 0:
            raise RowConditionError("values must be a non-empty list")

        # Check that all values are of supported types
        for value in self.values:
            if not isinstance(value, (str, int, float)):
                raise RowConditionError("all values must be strings, integers, or floats")

        if not isinstance(self.negate, bool):
            raise RowConditionError("negate must be a boolean")

    @override
    def to_pandas_query(self) -> str:
        """Convert to pandas query syntax."""
        # Format the values list for pandas
        formatted_values = []
        for value in self.values:
            if isinstance(value, str):
                escaped_value = value.replace('"', '\\"')
                formatted_values.append(f'"{escaped_value}"')
            else:
                formatted_values.append(str(value))

        values_str = f"[{', '.join(formatted_values)}]"

        if self.negate:
            return f"{self.column.name} not in {values_str}"
        else:
            return f"{self.column.name} in {values_str}"

    @override
    def to_spark_column(self) -> pyspark.Column:
        """Convert to Spark Column expression."""
        col: pyspark.Column = F.col(self.column.name)
        condition = col.isin(self.values)

        if self.negate:
            return ~condition
        else:
            return condition

    @override
    def to_sqlalchemy_expression(self) -> sqlalchemy.ColumnElement:
        """Convert to SQLAlchemy expression."""
        col: sqlalchemy.ColumnElement = sa.column(self.column.name)
        condition = col.in_(self.values)

        if self.negate:
            return sa.not_(condition)
        else:
            return condition

    @override
    def _to_dict_impl(self) -> dict:
        return {"column": self.column.name, "values": self.values, "negate": self.negate}


@dataclass
class LogicalCondition(BaseRowCondition):
    """Condition that combines multiple conditions with logical operators."""

    operator: Literal["AND", "OR"]
    conditions: List[BaseRowCondition]

    def __post_init__(self):
        self.validate()

    @override
    def validate(self) -> None:
        """Validate the logical condition."""
        if self.operator not in {"AND", "OR"}:
            raise RowConditionError("operator must be 'AND' or 'OR'")

        if not isinstance(self.conditions, list) or len(self.conditions) < 2:
            raise RowConditionError("conditions must be a list with at least 2 items")

        for condition in self.conditions:
            if not isinstance(condition, BaseRowCondition):
                raise RowConditionError("all conditions must be BaseRowCondition instances")
            condition.validate()

    @override
    def to_pandas_query(self) -> str:
        """Convert to pandas query syntax."""
        condition_strs = [f"({cond.to_pandas_query()})" for cond in self.conditions]

        if self.operator == "AND":
            return " & ".join(condition_strs)
        else:  # OR
            return " | ".join(condition_strs)

    @override
    def to_spark_column(self) -> pyspark.Column:
        """Convert to Spark Column expression."""
        result = self.conditions[0].to_spark_column()

        for condition in self.conditions[1:]:
            spark_condition = condition.to_spark_column()
            if self.operator == "AND":
                result = result & spark_condition
            else:  # OR
                result = result | spark_condition

        return result

    @override
    def to_sqlalchemy_expression(self) -> sqlalchemy.ColumnElement:
        """Convert to SQLAlchemy expression."""
        result = self.conditions[0].to_sqlalchemy_expression()

        for condition in self.conditions[1:]:
            sql_condition = condition.to_sqlalchemy_expression()
            if self.operator == "AND":
                result = sa.and_(result, sql_condition)
            else:  # OR
                result = sa.or_(result, sql_condition)

        return result

    @override
    def _to_dict_impl(self) -> dict:
        return {
            "operator": self.operator,
            "conditions": [cond.to_dict() for cond in self.conditions],
        }


@dataclass
class NotCondition(BaseRowCondition):
    """Condition that negates another condition."""

    condition: BaseRowCondition

    def __post_init__(self):
        self.validate()

    @override
    def validate(self) -> None:
        """Validate the not condition."""
        if not isinstance(self.condition, BaseRowCondition):
            raise RowConditionError("condition must be a BaseRowCondition instance")
        self.condition.validate()

    @override
    def to_pandas_query(self) -> str:
        """Convert to pandas query syntax."""
        return f"~({self.condition.to_pandas_query()})"

    @override
    def to_spark_column(self) -> pyspark.Column:
        """Convert to Spark Column expression."""
        return ~self.condition.to_spark_column()

    @override
    def to_sqlalchemy_expression(self) -> sqlalchemy.ColumnElement:
        """Convert to SQLAlchemy expression."""
        return sa.not_(self.condition.to_sqlalchemy_expression())

    @override
    def _to_dict_impl(self) -> dict:
        return {"condition": self.condition.to_dict()}


# Convenience functions for creating conditions
def col(name: str) -> ColumnReference:
    """Create a column reference."""
    return ColumnReference(name)


def eq(column: ColumnReference, value: Union[str, float, bool]) -> ComparisonCondition:
    """Create an equality condition."""
    return ComparisonCondition(column, "==", value)


def ne(column: ColumnReference, value: Union[str, float, bool]) -> ComparisonCondition:
    """Create a not-equal condition."""
    return ComparisonCondition(column, "!=", value)


def lt(column: ColumnReference, value: Union[str, float, bool]) -> ComparisonCondition:
    """Create a less-than condition."""
    return ComparisonCondition(column, "<", value)


def le(column: ColumnReference, value: Union[str, float, bool]) -> ComparisonCondition:
    """Create a less-than-or-equal condition."""
    return ComparisonCondition(column, "<=", value)


def gt(column: ColumnReference, value: Union[str, float, bool]) -> ComparisonCondition:
    """Create a greater-than condition."""
    return ComparisonCondition(column, ">", value)


def ge(column: ColumnReference, value: Union[str, float, bool]) -> ComparisonCondition:
    """Create a greater-than-or-equal condition."""
    return ComparisonCondition(column, ">=", value)


def is_null(column: ColumnReference) -> NullCheckCondition:
    """Create an is-null condition."""
    return NullCheckCondition(column, True)


def is_not_null(column: ColumnReference) -> NullCheckCondition:
    """Create an is-not-null condition."""
    return NullCheckCondition(column, False)


def is_in(column: ColumnReference, values: List[Union[str, int, float]]) -> InSetCondition:
    """Create an in-set condition."""
    return InSetCondition(column, values, False)


def not_in(column: ColumnReference, values: List[Union[str, int, float]]) -> InSetCondition:
    """Create a not-in-set condition."""
    return InSetCondition(column, values, True)


def and_(*conditions: BaseRowCondition) -> LogicalCondition:
    """Create an AND condition."""
    return LogicalCondition("AND", list(conditions))


def or_(*conditions: BaseRowCondition) -> LogicalCondition:
    """Create an OR condition."""
    return LogicalCondition("OR", list(conditions))


def not_(condition: BaseRowCondition) -> NotCondition:
    """Create a NOT condition."""
    return NotCondition(condition)
