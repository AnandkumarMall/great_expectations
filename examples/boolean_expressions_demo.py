"""
Demonstration of how boolean expressions work in pandas, Spark, and SQLAlchemy.

This shows that AND/OR conditions return the same types as individual conditions
because they're all boolean expressions that can be used for filtering.
"""

import pandas as pd
from great_expectations.expectations.row_conditions_v2 import (
    col, gt, eq, and_, or_, not_
)


def demonstrate_pandas_boolean_expressions():
    """Show how pandas boolean expressions work."""
    print("=== Pandas Boolean Expressions ===")

    # Create sample data
    df = pd.DataFrame({
        'age': [16, 25, 30, 45, 65],
        'status': ['inactive', 'active', 'active', 'inactive', 'active'],
        'subscription': ['basic', 'premium', 'basic', 'premium', 'basic']
    })

    print("Sample DataFrame:")
    print(df)
    print()

    # Individual condition - returns boolean Series
    age_condition = gt(col("age"), 18)
    age_query = age_condition.to_pandas_query()
    print(f"Age condition: {age_query}")
    age_mask = df.eval(age_query)
    print(f"Boolean mask: {age_mask.tolist()}")
    print(f"Filtered data:")
    print(df[age_mask])
    print()

    # Logical AND condition - also returns boolean Series
    and_condition = and_(
        gt(col("age"), 18),
        eq(col("status"), "active")
    )
    and_query = and_condition.to_pandas_query()
    print(f"AND condition: {and_query}")
    and_mask = df.eval(and_query)
    print(f"Boolean mask: {and_mask.tolist()}")
    print(f"Filtered data:")
    print(df[and_mask])
    print()

    # Logical OR condition - also returns boolean Series
    or_condition = or_(
        gt(col("age"), 60),
        eq(col("subscription"), "premium")
    )
    or_query = or_condition.to_pandas_query()
    print(f"OR condition: {or_query}")
    or_mask = df.eval(or_query)
    print(f"Boolean mask: {or_mask.tolist()}")
    print(f"Filtered data:")
    print(df[or_mask])
    print()


def demonstrate_spark_boolean_expressions():
    """Show how Spark boolean expressions work."""
    print("=== Spark Boolean Expressions ===")

    try:
        from pyspark.sql import SparkSession
        from pyspark.sql.functions import col as spark_col

        # Initialize Spark (if available)
        spark = SparkSession.builder.appName("BooleanDemo").getOrCreate()

        # Create sample data
        data = [
            (16, 'inactive', 'basic'),
            (25, 'active', 'premium'),
            (30, 'active', 'basic'),
            (45, 'inactive', 'premium'),
            (65, 'active', 'basic')
        ]
        df = spark.createDataFrame(data, ['age', 'status', 'subscription'])

        print("Sample Spark DataFrame:")
        df.show()

        # Individual condition - returns Column with boolean expression
        age_condition = gt(col("age"), 18)
        spark_age_col = age_condition.to_spark_column()
        print(f"Age condition type: {type(spark_age_col)}")
        print(f"Age condition string: {spark_age_col}")

        print("Filtered by age > 18:")
        df.filter(spark_age_col).show()

        # Logical AND condition - also returns Column with boolean expression
        and_condition = and_(
            gt(col("age"), 18),
            eq(col("status"), "active")
        )
        spark_and_col = and_condition.to_spark_column()
        print(f"AND condition type: {type(spark_and_col)}")
        print(f"AND condition string: {spark_and_col}")

        print("Filtered by age > 18 AND status = 'active':")
        df.filter(spark_and_col).show()

        # Logical OR condition - also returns Column with boolean expression
        or_condition = or_(
            gt(col("age"), 60),
            eq(col("subscription"), "premium")
        )
        spark_or_col = or_condition.to_spark_column()
        print(f"OR condition type: {type(spark_or_col)}")
        print(f"OR condition string: {spark_or_col}")

        print("Filtered by age > 60 OR subscription = 'premium':")
        df.filter(spark_or_col).show()

        spark.stop()

    except ImportError:
        print("Spark not available - skipping Spark demonstration")
    except Exception as e:
        print(f"Spark error: {e}")


def demonstrate_sqlalchemy_boolean_expressions():
    """Show how SQLAlchemy boolean expressions work."""
    print("=== SQLAlchemy Boolean Expressions ===")

    from great_expectations.compatibility.sqlalchemy import sqlalchemy as sa

    # Create a mock table for demonstration
    metadata = sa.MetaData()
    users_table = sa.Table(
        'users',
        metadata,
        sa.Column('age', sa.Integer),
        sa.Column('status', sa.String(50)),
        sa.Column('subscription', sa.String(50))
    )

    # Individual condition - returns ColumnElement with boolean expression
    age_condition = gt(col("age"), 18)
    sql_age_expr = age_condition.to_sqlalchemy_expression()
    print(f"Age condition type: {type(sql_age_expr)}")
    print(f"Age condition SQL: {sql_age_expr}")

    # Show how it would be used in a query
    age_query = sa.select(users_table).where(sql_age_expr)
    print(f"Query with age condition: {age_query}")
    print()

    # Logical AND condition - also returns ColumnElement with boolean expression
    and_condition = and_(
        gt(col("age"), 18),
        eq(col("status"), "active")
    )
    sql_and_expr = and_condition.to_sqlalchemy_expression()
    print(f"AND condition type: {type(sql_and_expr)}")
    print(f"AND condition SQL: {sql_and_expr}")

    # Show how it would be used in a query
    and_query = sa.select(users_table).where(sql_and_expr)
    print(f"Query with AND condition: {and_query}")
    print()

    # Logical OR condition - also returns ColumnElement with boolean expression
    or_condition = or_(
        gt(col("age"), 60),
        eq(col("subscription"), "premium")
    )
    sql_or_expr = or_condition.to_sqlalchemy_expression()
    print(f"OR condition type: {type(sql_or_expr)}")
    print(f"OR condition SQL: {sql_or_expr}")

    # Show how it would be used in a query
    or_query = sa.select(users_table).where(sql_or_expr)
    print(f"Query with OR condition: {or_query}")
    print()


def demonstrate_boolean_expression_composition():
    """Show how boolean expressions compose naturally."""
    print("=== Boolean Expression Composition ===")

    # All of these return the same types because they're all boolean expressions
    simple_condition = gt(col("age"), 18)
    and_condition = and_(gt(col("age"), 18), eq(col("status"), "active"))
    or_condition = or_(gt(col("age"), 60), eq(col("subscription"), "premium"))
    not_condition = not_(eq(col("status"), "inactive"))

    # Complex nested condition
    complex_condition = and_(
        gt(col("age"), 18),
        or_(
            eq(col("subscription"), "premium"),
            and_(
                eq(col("status"), "active"),
                not_(eq(col("subscription"), "banned"))
            )
        )
    )

    print("All conditions return boolean expressions:")
    print(f"Simple: {simple_condition.to_pandas_query()}")
    print(f"AND: {and_condition.to_pandas_query()}")
    print(f"OR: {or_condition.to_pandas_query()}")
    print(f"NOT: {not_condition.to_pandas_query()}")
    print(f"Complex: {complex_condition.to_pandas_query()}")
    print()

    print("They can all be used interchangeably for filtering:")

    # Create sample DataFrame
    df = pd.DataFrame({
        'age': [16, 25, 30, 45, 65],
        'status': ['inactive', 'active', 'active', 'inactive', 'active'],
        'subscription': ['basic', 'premium', 'basic', 'premium', 'basic']
    })

    for name, condition in [
        ("Simple", simple_condition),
        ("AND", and_condition),
        ("OR", or_condition),
        ("NOT", not_condition),
        ("Complex", complex_condition)
    ]:
        query = condition.to_pandas_query()
        mask = df.eval(query)
        filtered_count = mask.sum()
        print(f"{name:8} condition filters to {filtered_count} rows")


def demonstrate_type_consistency():
    """Show that all conditions return consistent types across engines."""
    print("=== Type Consistency Across Engines ===")

    conditions = [
        ("Simple comparison", gt(col("age"), 18)),
        ("AND condition", and_(gt(col("age"), 18), eq(col("status"), "active"))),
        ("OR condition", or_(gt(col("age"), 60), eq(col("subscription"), "premium"))),
        ("NOT condition", not_(eq(col("status"), "inactive"))),
        ("Complex nested", and_(
            gt(col("age"), 18),
            or_(
                eq(col("subscription"), "premium"),
                eq(col("status"), "active")
            )
        ))
    ]

    print("All conditions return the same types for each engine:")
    print()

    for name, condition in conditions:
        pandas_result = condition.to_pandas_query()
        sql_result = condition.to_sqlalchemy_expression()

        print(f"{name}:")
        print(f"  Pandas query (str): {type(pandas_result).__name__}")
        print(f"  SQL expression: {type(sql_result).__name__}")

        try:
            spark_result = condition.to_spark_column()
            print(f"  Spark column: {type(spark_result).__name__}")
        except Exception:
            print(f"  Spark column: (not available)")

        print()


if __name__ == "__main__":
    print("Boolean Expressions in Row Conditions")
    print("=" * 50)
    print()

    demonstrate_pandas_boolean_expressions()
    print("\n" + "=" * 50 + "\n")

    demonstrate_spark_boolean_expressions()
    print("\n" + "=" * 50 + "\n")

    demonstrate_sqlalchemy_boolean_expressions()
    print("\n" + "=" * 50 + "\n")

    demonstrate_boolean_expression_composition()
    print("\n" + "=" * 50 + "\n")

    demonstrate_type_consistency()

    print("=" * 50)
    print("Key Insights:")
    print("1. ✅ Individual conditions return boolean expressions")
    print("2. ✅ AND/OR conditions also return boolean expressions")
    print("3. ✅ All can be used interchangeably for filtering")
    print("4. ✅ Types are consistent across all engines")
    print("5. ✅ Boolean expressions compose naturally")
