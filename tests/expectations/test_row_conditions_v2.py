"""
Tests for the unified row conditions API (v2).

These tests demonstrate the new strongly typed row condition system that works
consistently across pandas, Spark, and SQL execution engines.
"""

from unittest.mock import Mock

import pytest

from great_expectations.expectations.row_conditions_v2 import (
    BaseRowCondition,
    ColumnReference,
    ComparisonCondition,
    InSetCondition,
    LogicalCondition,
    NotCondition,
    NullCheckCondition,
    RowConditionError,
    and_,
    col,
    eq,
    ge,
    gt,
    is_in,
    is_not_null,
    is_null,
    le,
    lt,
    ne,
    not_,
    not_in,
    or_,
)


class TestColumnReference:
    """Test ColumnReference functionality."""

    def test_valid_column_reference(self):
        """Test creating a valid column reference."""
        column = ColumnReference("age")
        assert column.name == "age"

    def test_invalid_column_reference_empty_name(self):
        """Test that empty column names raise an error."""
        with pytest.raises(RowConditionError, match="Column name must be a non-empty string"):
            ColumnReference("")

    def test_invalid_column_reference_none_name(self):
        """Test that None column names raise an error."""
        with pytest.raises(RowConditionError, match="Column name must be a non-empty string"):
            ColumnReference(None)

    def test_convenience_function(self):
        """Test the col() convenience function."""
        column = col("age")
        assert isinstance(column, ColumnReference)
        assert column.name == "age"


class TestComparisonCondition:
    """Test ComparisonCondition functionality."""

    def test_valid_comparison_condition(self):
        """Test creating a valid comparison condition."""
        condition = ComparisonCondition(col("age"), ">", 18)
        assert condition.column.name == "age"
        assert condition.operator == ">"
        assert condition.value == 18

    def test_invalid_operator(self):
        """Test that invalid operators raise an error."""
        with pytest.raises(RowConditionError, match="operator must be one of"):
            ComparisonCondition(col("age"), "~", 18)

    def test_invalid_value_type(self):
        """Test that invalid value types raise an error."""
        with pytest.raises(RowConditionError, match="value must be a string, number, or boolean"):
            ComparisonCondition(col("age"), ">", [1, 2, 3])

    def test_to_pandas_query_numeric(self):
        """Test conversion to pandas query syntax with numeric values."""
        condition = ComparisonCondition(col("age"), ">", 18)
        assert condition.to_pandas_query() == "age > 18"

    def test_to_pandas_query_string(self):
        """Test conversion to pandas query syntax with string values."""
        condition = ComparisonCondition(col("name"), "==", "John")
        assert condition.to_pandas_query() == 'name == "John"'

    def test_to_pandas_query_string_with_quotes(self):
        """Test conversion to pandas query syntax with string values containing quotes."""
        condition = ComparisonCondition(col("name"), "==", 'John "Johnny" Doe')
        assert condition.to_pandas_query() == 'name == "John \\"Johnny\\" Doe"'

    @pytest.mark.spark
    def test_to_spark_column(self, spark_session):
        """Test conversion to Spark Column expression."""
        condition = ComparisonCondition(col("age"), ">", 18)
        spark_col = condition.to_spark_column()

        # Test that it creates a valid Spark Column
        assert hasattr(spark_col, "_jc")  # Spark Column has _jc attribute

        # Test the string representation contains our condition
        col_str = str(spark_col)
        assert "age" in col_str
        assert ">" in col_str

    def test_to_sqlalchemy_expression(self):
        """Test conversion to SQLAlchemy expression."""
        condition = ComparisonCondition(col("age"), ">", 18)
        sql_expr = condition.to_sqlalchemy_expression()

        # Test the string representation
        assert str(sql_expr) == "age > :age_1"

    def test_convenience_functions(self):
        """Test convenience functions for creating comparison conditions."""
        age_col = col("age")

        # Test all comparison operators
        assert eq(age_col, 18).operator == "=="
        assert ne(age_col, 18).operator == "!="
        assert lt(age_col, 18).operator == "<"
        assert le(age_col, 18).operator == "<="
        assert gt(age_col, 18).operator == ">"
        assert ge(age_col, 18).operator == ">="

    def test_serialization(self):
        """Test serialization to dictionary."""
        condition = ComparisonCondition(col("age"), ">", 18)
        expected = {"type": "ComparisonCondition", "column": "age", "operator": ">", "value": 18}
        assert condition.to_dict() == expected


class TestNullCheckCondition:
    """Test NullCheckCondition functionality."""

    def test_is_null_condition(self):
        """Test creating an is-null condition."""
        condition = NullCheckCondition(col("name"), True)
        assert condition.column.name == "name"
        assert condition.is_null is True

    def test_is_not_null_condition(self):
        """Test creating an is-not-null condition."""
        condition = NullCheckCondition(col("name"), False)
        assert condition.column.name == "name"
        assert condition.is_null is False

    def test_to_pandas_query_is_null(self):
        """Test conversion to pandas query for null check."""
        condition = NullCheckCondition(col("name"), True)
        assert condition.to_pandas_query() == "name.isna()"

    def test_to_pandas_query_is_not_null(self):
        """Test conversion to pandas query for not-null check."""
        condition = NullCheckCondition(col("name"), False)
        assert condition.to_pandas_query() == "name.notna()"

    @pytest.mark.spark
    def test_to_spark_column_is_null(self, spark_session):
        """Test conversion to Spark Column for null check."""
        condition = NullCheckCondition(col("name"), True)
        spark_col = condition.to_spark_column()

        # Test that it creates a valid Spark Column
        assert hasattr(spark_col, "_jc")
        col_str = str(spark_col)
        assert "name" in col_str
        assert "NULL" in col_str.upper()

    def test_to_sqlalchemy_expression_is_null(self):
        """Test conversion to SQLAlchemy for null check."""
        condition = NullCheckCondition(col("name"), True)
        sql_expr = condition.to_sqlalchemy_expression()
        assert str(sql_expr) == "name IS NULL"

    def test_to_sqlalchemy_expression_is_not_null(self):
        """Test conversion to SQLAlchemy for not-null check."""
        condition = NullCheckCondition(col("name"), False)
        sql_expr = condition.to_sqlalchemy_expression()
        assert str(sql_expr) == "name IS NOT NULL"

    def test_convenience_functions(self):
        """Test convenience functions for null checks."""
        name_col = col("name")

        null_condition = is_null(name_col)
        assert isinstance(null_condition, NullCheckCondition)
        assert null_condition.is_null is True

        not_null_condition = is_not_null(name_col)
        assert isinstance(not_null_condition, NullCheckCondition)
        assert not_null_condition.is_null is False

    def test_serialization(self):
        """Test serialization to dictionary."""
        condition = NullCheckCondition(col("name"), True)
        expected = {"type": "NullCheckCondition", "column": "name", "is_null": True}
        assert condition.to_dict() == expected


class TestInSetCondition:
    """Test InSetCondition functionality."""

    def test_in_set_condition(self):
        """Test creating an in-set condition."""
        condition = InSetCondition(col("status"), ["active", "pending"], False)
        assert condition.column.name == "status"
        assert condition.values == ["active", "pending"]
        assert condition.negate is False

    def test_not_in_set_condition(self):
        """Test creating a not-in-set condition."""
        condition = InSetCondition(col("status"), ["inactive", "deleted"], True)
        assert condition.negate is True

    def test_invalid_empty_values(self):
        """Test that empty values list raises an error."""
        with pytest.raises(RowConditionError, match="values must be a non-empty list"):
            InSetCondition(col("status"), [], False)

    def test_invalid_value_type(self):
        """Test that invalid value types raise an error."""
        with pytest.raises(
            RowConditionError, match="all values must be strings, integers, or floats"
        ):
            InSetCondition(col("status"), ["active", {"invalid": "dict"}], False)

    def test_to_pandas_query_in_set(self):
        """Test conversion to pandas query for in-set."""
        condition = InSetCondition(col("status"), ["active", "pending"], False)
        assert condition.to_pandas_query() == 'status in ["active", "pending"]'

    def test_to_pandas_query_not_in_set(self):
        """Test conversion to pandas query for not-in-set."""
        condition = InSetCondition(col("status"), ["inactive"], True)
        assert condition.to_pandas_query() == 'status not in ["inactive"]'

    def test_to_pandas_query_mixed_types(self):
        """Test conversion to pandas query with mixed value types."""
        condition = InSetCondition(col("value"), [1, 2.5, "three"], False)
        assert condition.to_pandas_query() == 'value in [1, 2.5, "three"]'

    @pytest.mark.spark
    def test_to_spark_column_in_set(self, spark_session):
        """Test conversion to Spark Column for in-set."""
        condition = InSetCondition(col("status"), ["active", "pending"], False)
        spark_col = condition.to_spark_column()

        assert hasattr(spark_col, "_jc")
        col_str = str(spark_col)
        assert "status" in col_str

    def test_to_sqlalchemy_expression_in_set(self):
        """Test conversion to SQLAlchemy for in-set."""
        condition = InSetCondition(col("status"), ["active", "pending"], False)
        sql_expr = condition.to_sqlalchemy_expression()

        # SQLAlchemy represents IN as "column IN (__[POSTCOMPILE_param_1])"
        expr_str = str(sql_expr)
        assert "status" in expr_str
        assert "IN" in expr_str

    def test_convenience_functions(self):
        """Test convenience functions for in-set conditions."""
        status_col = col("status")

        in_condition = is_in(status_col, ["active", "pending"])
        assert isinstance(in_condition, InSetCondition)
        assert in_condition.negate is False

        not_in_condition = not_in(status_col, ["inactive"])
        assert isinstance(not_in_condition, InSetCondition)
        assert not_in_condition.negate is True

    def test_serialization(self):
        """Test serialization to dictionary."""
        condition = InSetCondition(col("status"), ["active", "pending"], False)
        expected = {
            "type": "InSetCondition",
            "column": "status",
            "values": ["active", "pending"],
            "negate": False,
        }
        assert condition.to_dict() == expected


class TestLogicalCondition:
    """Test LogicalCondition functionality."""

    def test_and_condition(self):
        """Test creating an AND condition."""
        cond1 = ComparisonCondition(col("age"), ">", 18)
        cond2 = ComparisonCondition(col("status"), "==", "active")

        and_condition = LogicalCondition("AND", [cond1, cond2])
        assert and_condition.operator == "AND"
        assert len(and_condition.conditions) == 2

    def test_or_condition(self):
        """Test creating an OR condition."""
        cond1 = ComparisonCondition(col("age"), "<", 18)
        cond2 = ComparisonCondition(col("age"), ">", 65)

        or_condition = LogicalCondition("OR", [cond1, cond2])
        assert or_condition.operator == "OR"

    def test_invalid_operator(self):
        """Test that invalid logical operators raise an error."""
        cond1 = ComparisonCondition(col("age"), ">", 18)
        cond2 = ComparisonCondition(col("status"), "==", "active")

        with pytest.raises(RowConditionError, match="operator must be 'AND' or 'OR'"):
            LogicalCondition("XOR", [cond1, cond2])

    def test_insufficient_conditions(self):
        """Test that insufficient conditions raise an error."""
        cond1 = ComparisonCondition(col("age"), ">", 18)

        with pytest.raises(
            RowConditionError, match="conditions must be a list with at least 2 items"
        ):
            LogicalCondition("AND", [cond1])

    def test_to_pandas_query_and(self):
        """Test conversion to pandas query for AND."""
        cond1 = ComparisonCondition(col("age"), ">", 18)
        cond2 = ComparisonCondition(col("status"), "==", "active")

        and_condition = LogicalCondition("AND", [cond1, cond2])
        expected = '(age > 18) & (status == "active")'
        assert and_condition.to_pandas_query() == expected

    def test_to_pandas_query_or(self):
        """Test conversion to pandas query for OR."""
        cond1 = ComparisonCondition(col("age"), "<", 18)
        cond2 = ComparisonCondition(col("age"), ">", 65)

        or_condition = LogicalCondition("OR", [cond1, cond2])
        expected = "(age < 18) | (age > 65)"
        assert or_condition.to_pandas_query() == expected

    @pytest.mark.spark
    def test_to_spark_column_and(self, spark_session):
        """Test conversion to Spark Column for AND."""
        cond1 = ComparisonCondition(col("age"), ">", 18)
        cond2 = ComparisonCondition(col("status"), "==", "active")

        and_condition = LogicalCondition("AND", [cond1, cond2])
        spark_col = and_condition.to_spark_column()

        assert hasattr(spark_col, "_jc")

    def test_to_sqlalchemy_expression_and(self):
        """Test conversion to SQLAlchemy for AND."""
        cond1 = ComparisonCondition(col("age"), ">", 18)
        cond2 = ComparisonCondition(col("status"), "==", "active")

        and_condition = LogicalCondition("AND", [cond1, cond2])
        sql_expr = and_condition.to_sqlalchemy_expression()

        expr_str = str(sql_expr)
        assert "age > " in expr_str
        assert "status = " in expr_str
        assert "AND" in expr_str

    def test_convenience_functions(self):
        """Test convenience functions for logical conditions."""
        cond1 = ComparisonCondition(col("age"), ">", 18)
        cond2 = ComparisonCondition(col("status"), "==", "active")

        and_condition = and_(cond1, cond2)
        assert isinstance(and_condition, LogicalCondition)
        assert and_condition.operator == "AND"

        or_condition = or_(cond1, cond2)
        assert isinstance(or_condition, LogicalCondition)
        assert or_condition.operator == "OR"

    def test_nested_logical_conditions(self):
        """Test nested logical conditions."""
        # (age > 18 AND status == "active") OR (age < 18 AND guardian_consent == True)
        adult_condition = and_(gt(col("age"), 18), eq(col("status"), "active"))

        minor_condition = and_(lt(col("age"), 18), eq(col("guardian_consent"), True))

        overall_condition = or_(adult_condition, minor_condition)

        # Test that it can be converted to pandas query
        query = overall_condition.to_pandas_query()
        assert "age > 18" in query
        assert 'status == "active"' in query
        assert "age < 18" in query
        assert "guardian_consent == True" in query
        assert "&" in query  # AND operators
        assert "|" in query  # OR operator

    def test_serialization(self):
        """Test serialization to dictionary."""
        cond1 = ComparisonCondition(col("age"), ">", 18)
        cond2 = ComparisonCondition(col("status"), "==", "active")

        and_condition = LogicalCondition("AND", [cond1, cond2])
        result = and_condition.to_dict()

        assert result["type"] == "LogicalCondition"
        assert result["operator"] == "AND"
        assert len(result["conditions"]) == 2
        assert result["conditions"][0]["type"] == "ComparisonCondition"
        assert result["conditions"][1]["type"] == "ComparisonCondition"


class TestNotCondition:
    """Test NotCondition functionality."""

    def test_not_condition(self):
        """Test creating a NOT condition."""
        base_condition = ComparisonCondition(col("age"), ">", 18)
        not_condition = NotCondition(base_condition)

        assert isinstance(not_condition.condition, ComparisonCondition)

    def test_to_pandas_query(self):
        """Test conversion to pandas query for NOT."""
        base_condition = ComparisonCondition(col("age"), ">", 18)
        not_condition = NotCondition(base_condition)

        assert not_condition.to_pandas_query() == "~(age > 18)"

    @pytest.mark.spark
    def test_to_spark_column(self, spark_session):
        """Test conversion to Spark Column for NOT."""
        base_condition = ComparisonCondition(col("age"), ">", 18)
        not_condition = NotCondition(base_condition)

        spark_col = not_condition.to_spark_column()
        assert hasattr(spark_col, "_jc")

    def test_to_sqlalchemy_expression(self):
        """Test conversion to SQLAlchemy for NOT."""
        base_condition = ComparisonCondition(col("age"), ">", 18)
        not_condition = NotCondition(base_condition)

        sql_expr = not_condition.to_sqlalchemy_expression()
        expr_str = str(sql_expr)
        assert "NOT" in expr_str
        assert "age > " in expr_str

    def test_convenience_function(self):
        """Test convenience function for NOT condition."""
        base_condition = ComparisonCondition(col("age"), ">", 18)
        not_condition = not_(base_condition)

        assert isinstance(not_condition, NotCondition)
        assert not_condition.condition == base_condition

    def test_serialization(self):
        """Test serialization to dictionary."""
        base_condition = ComparisonCondition(col("age"), ">", 18)
        not_condition = NotCondition(base_condition)

        result = not_condition.to_dict()
        assert result["type"] == "NotCondition"
        assert result["condition"]["type"] == "ComparisonCondition"


class TestComplexConditions:
    """Test complex combinations of conditions."""

    def test_complex_business_logic(self):
        """Test a complex business logic condition."""
        # Example: Active users who are either premium subscribers or have made recent purchases
        # (status == "active") AND ((subscription == "premium") OR (last_purchase_days <= 30))

        active_condition = eq(col("status"), "active")
        premium_condition = eq(col("subscription"), "premium")
        recent_purchase_condition = le(col("last_purchase_days"), 30)

        subscriber_or_recent = or_(premium_condition, recent_purchase_condition)
        final_condition = and_(active_condition, subscriber_or_recent)

        # Test pandas conversion
        pandas_query = final_condition.to_pandas_query()
        expected_parts = [
            'status == "active"',
            'subscription == "premium"',
            "last_purchase_days <= 30",
            "&",  # AND
            "|",  # OR
        ]

        for part in expected_parts:
            assert part in pandas_query

    @pytest.mark.spark
    def test_complex_condition_spark_conversion(self, spark_session):
        """Test that complex conditions can be converted to Spark."""
        # NOT ((age < 18) OR (status == "inactive"))
        minor_condition = lt(col("age"), 18)
        inactive_condition = eq(col("status"), "inactive")
        excluded_condition = or_(minor_condition, inactive_condition)
        final_condition = not_(excluded_condition)

        # Should not raise an exception
        spark_col = final_condition.to_spark_column()
        assert hasattr(spark_col, "_jc")

    def test_complex_condition_sql_conversion(self):
        """Test that complex conditions can be converted to SQL."""
        # (category IN ["electronics", "books"]) AND (price > 10.0) AND (stock IS NOT NULL)
        category_condition = is_in(col("category"), ["electronics", "books"])
        price_condition = gt(col("price"), 10.0)
        stock_condition = is_not_null(col("stock"))

        final_condition = and_(category_condition, price_condition, stock_condition)

        # Should not raise an exception
        sql_expr = final_condition.to_sqlalchemy_expression()
        expr_str = str(sql_expr)

        # Should contain all the expected parts
        assert "category" in expr_str
        assert "price" in expr_str
        assert "stock" in expr_str
        assert "AND" in expr_str

    def test_json_serialization_complex_condition(self):
        """Test JSON serialization of complex conditions."""
        # Create a complex nested condition
        condition = and_(
            gt(col("age"), 18),
            or_(eq(col("status"), "premium"), is_not_null(col("referral_code"))),
            not_(is_in(col("country"), ["banned_country_1", "banned_country_2"])),
        )

        # Should be serializable to JSON
        json_dict = condition.to_json_dict()

        # Verify structure
        assert json_dict["type"] == "LogicalCondition"
        assert json_dict["operator"] == "AND"
        assert len(json_dict["conditions"]) == 3

        # Verify nested OR condition
        or_condition = json_dict["conditions"][1]
        assert or_condition["type"] == "LogicalCondition"
        assert or_condition["operator"] == "OR"

        # Verify nested NOT condition
        not_condition = json_dict["conditions"][2]
        assert not_condition["type"] == "NotCondition"


class TestErrorHandling:
    """Test error handling and validation."""

    def test_early_validation_comparison(self):
        """Test that comparison conditions are validated early."""
        # This should fail immediately, not during execution
        with pytest.raises(RowConditionError):
            ComparisonCondition(col("age"), "invalid_op", 18)

    def test_early_validation_in_set(self):
        """Test that in-set conditions are validated early."""
        # This should fail immediately
        with pytest.raises(RowConditionError):
            InSetCondition(col("status"), [], False)  # Empty list

    def test_early_validation_logical(self):
        """Test that logical conditions are validated early."""
        # This should fail immediately
        with pytest.raises(RowConditionError):
            LogicalCondition("INVALID", [])

    def test_nested_validation(self):
        """Test that nested condition validation works."""
        # Create an invalid nested condition
        invalid_condition = Mock(spec=BaseRowCondition)
        invalid_condition.validate.side_effect = RowConditionError("Invalid nested condition")

        with pytest.raises(RowConditionError, match="Invalid nested condition"):
            LogicalCondition("AND", [ComparisonCondition(col("age"), ">", 18), invalid_condition])


class TestBackwardCompatibility:
    """Test that the new API can coexist with the old system."""

    def test_conversion_from_old_format(self):
        """Test converting from old string-based conditions to new format."""
        # This would be part of a migration utility
        old_condition = 'col("age") > 18'

        # For now, we can show how the new API would handle this
        new_condition = gt(col("age"), 18)

        # Both should produce equivalent results
        pandas_query = new_condition.to_pandas_query()
        assert "age > 18" in pandas_query

    def test_serialization_compatibility(self):
        """Test that new conditions can be serialized for storage."""
        condition = and_(gt(col("age"), 18), eq(col("status"), "active"))

        # Should be serializable
        serialized = condition.to_json_dict()
        assert isinstance(serialized, dict)
        assert "type" in serialized

        # Could be stored in expectation configuration
        expectation_config = {
            "type": "expect_column_values_to_be_in_set",
            "kwargs": {
                "column": "user_id",
                "value_set": [1, 2, 3],
                "row_condition_v2": serialized,  # New field
            },
        }

        assert expectation_config["kwargs"]["row_condition_v2"]["type"] == "LogicalCondition"
