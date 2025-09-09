"""
Examples demonstrating the new unified row conditions API.

This file shows how to use the new strongly typed row conditions that work
consistently across pandas, Spark, and SQL execution engines.
"""

from great_expectations.expectations.row_conditions_v2 import (
    col, eq, ne, lt, le, gt, ge,
    is_null, is_not_null, is_in, not_in,
    and_, or_, not_
)


def example_basic_conditions():
    """Examples of basic row conditions."""

    print("=== Basic Comparison Conditions ===")

    # Age greater than 18
    age_condition = gt(col("age"), 18)
    print(f"Age > 18:")
    print(f"  Pandas: {age_condition.to_pandas_query()}")
    print(f"  SQL: {age_condition.to_sqlalchemy_expression()}")
    print()

    # Status equals "active"
    status_condition = eq(col("status"), "active")
    print(f"Status == 'active':")
    print(f"  Pandas: {status_condition.to_pandas_query()}")
    print(f"  SQL: {status_condition.to_sqlalchemy_expression()}")
    print()

    # Price between 10 and 100
    price_range = and_(ge(col("price"), 10), le(col("price"), 100))
    print(f"Price between 10 and 100:")
    print(f"  Pandas: {price_range.to_pandas_query()}")
    print(f"  SQL: {price_range.to_sqlalchemy_expression()}")
    print()


def example_null_conditions():
    """Examples of null check conditions."""

    print("=== Null Check Conditions ===")

    # Email is not null
    email_not_null = is_not_null(col("email"))
    print(f"Email is not null:")
    print(f"  Pandas: {email_not_null.to_pandas_query()}")
    print(f"  SQL: {email_not_null.to_sqlalchemy_expression()}")
    print()

    # Phone is null
    phone_null = is_null(col("phone"))
    print(f"Phone is null:")
    print(f"  Pandas: {phone_null.to_pandas_query()}")
    print(f"  SQL: {phone_null.to_sqlalchemy_expression()}")
    print()


def example_set_conditions():
    """Examples of set membership conditions."""

    print("=== Set Membership Conditions ===")

    # Category in specific set
    category_condition = is_in(col("category"), ["electronics", "books", "clothing"])
    print(f"Category in allowed set:")
    print(f"  Pandas: {category_condition.to_pandas_query()}")
    print(f"  SQL: {category_condition.to_sqlalchemy_expression()}")
    print()

    # Status not in excluded set
    status_excluded = not_in(col("status"), ["deleted", "banned"])
    print(f"Status not in excluded set:")
    print(f"  Pandas: {status_excluded.to_pandas_query()}")
    print(f"  SQL: {status_excluded.to_sqlalchemy_expression()}")
    print()


def example_complex_conditions():
    """Examples of complex logical conditions."""

    print("=== Complex Logical Conditions ===")

    # Active users who are either premium or have recent activity
    complex_condition = and_(
        eq(col("status"), "active"),
        or_(
            eq(col("subscription"), "premium"),
            le(col("days_since_last_login"), 30)
        )
    )

    print(f"Active users with premium subscription or recent activity:")
    print(f"  Pandas: {complex_condition.to_pandas_query()}")
    print(f"  SQL: {complex_condition.to_sqlalchemy_expression()}")
    print()

    # Users who are NOT in a specific age range
    age_exclusion = not_(and_(ge(col("age"), 13), lt(col("age"), 18)))
    print(f"Users NOT in age range 13-17:")
    print(f"  Pandas: {age_exclusion.to_pandas_query()}")
    print(f"  SQL: {age_exclusion.to_sqlalchemy_expression()}")
    print()


def example_business_logic_conditions():
    """Examples of real-world business logic conditions."""

    print("=== Business Logic Examples ===")

    # Valid customers for a promotion
    promotion_eligible = and_(
        eq(col("account_status"), "active"),
        ge(col("account_age_months"), 6),
        or_(
            ge(col("total_purchases"), 1000),
            ge(col("purchase_count"), 5)
        ),
        not_in(col("country"), ["restricted_country_1", "restricted_country_2"])
    )

    print(f"Customers eligible for promotion:")
    print(f"  Pandas: {promotion_eligible.to_pandas_query()}")
    print()

    # High-risk transactions
    high_risk_transaction = or_(
        gt(col("amount"), 10000),
        and_(
            gt(col("amount"), 1000),
            is_in(col("merchant_category"), ["gambling", "crypto", "cash_advance"])
        ),
        and_(
            gt(col("amount"), 500),
            eq(col("international_transaction"), True),
            is_null(col("verified_merchant"))
        )
    )

    print(f"High-risk transactions:")
    print(f"  Pandas: {high_risk_transaction.to_pandas_query()}")
    print()


def example_migration_from_old_api():
    """Examples showing migration from old string-based API."""

    print("=== Migration Examples ===")

    # Old pandas API
    old_pandas_condition = 'age > 18 & status == "active"'
    print(f"Old pandas condition: {old_pandas_condition}")

    # New unified API (equivalent)
    new_condition = and_(
        gt(col("age"), 18),
        eq(col("status"), "active")
    )
    print(f"New unified condition (pandas): {new_condition.to_pandas_query()}")
    print(f"New unified condition (SQL): {new_condition.to_sqlalchemy_expression()}")
    print()

    # Old GE API
    old_ge_condition = 'col("age") > 18'
    print(f"Old GE condition: {old_ge_condition}")

    # New unified API (equivalent)
    new_ge_condition = gt(col("age"), 18)
    print(f"New unified condition (pandas): {new_ge_condition.to_pandas_query()}")
    print(f"New unified condition (SQL): {new_ge_condition.to_sqlalchemy_expression()}")
    print()


def example_expectation_usage():
    """Examples of using new row conditions in expectations."""

    print("=== Expectation Usage Examples ===")

    # Example expectation configuration with new row condition
    from great_expectations.expectations.row_conditions_v2 import and_, eq, gt

    # Condition: Active adult users
    adult_active_users = and_(
        gt(col("age"), 18),
        eq(col("status"), "active")
    )

    # Old way (engine-specific)
    old_expectation_config = {
        "type": "expect_column_values_to_be_in_set",
        "kwargs": {
            "column": "user_type",
            "value_set": ["premium", "standard"],
            "row_condition": 'age > 18 & status == "active"',  # Only works with pandas
            "condition_parser": "pandas"
        }
    }

    # New way (cross-engine compatible)
    new_expectation_config = {
        "type": "expect_column_values_to_be_in_set",
        "kwargs": {
            "column": "user_type",
            "value_set": ["premium", "standard"],
            "row_condition_v2": adult_active_users  # Works with all engines
        }
    }

    print("Old expectation config (pandas only):")
    print(f"  row_condition: {old_expectation_config['kwargs']['row_condition']}")
    print(f"  condition_parser: {old_expectation_config['kwargs']['condition_parser']}")
    print()

    print("New expectation config (all engines):")
    print(f"  Pandas equivalent: {adult_active_users.to_pandas_query()}")
    print(f"  SQL equivalent: {adult_active_users.to_sqlalchemy_expression()}")
    print()


def example_validation_benefits():
    """Examples showing early validation benefits."""

    print("=== Early Validation Benefits ===")

    try:
        # This will fail immediately with a clear error message
        from great_expectations.expectations.row_conditions_v2 import ComparisonCondition, col
        invalid_condition = ComparisonCondition(col("age"), "invalid_operator", 18)
    except Exception as e:
        print(f"Early validation caught error: {e}")

    try:
        # This will also fail immediately
        from great_expectations.expectations.row_conditions_v2 import InSetCondition, col
        invalid_set_condition = InSetCondition(col("status"), [], False)  # Empty list
    except Exception as e:
        print(f"Early validation caught error: {e}")

    print("With the old API, these errors would only be caught during expectation execution!")
    print()


def example_serialization():
    """Examples of condition serialization."""

    print("=== Serialization Examples ===")

    # Create a complex condition
    condition = and_(
        gt(col("age"), 18),
        or_(
            eq(col("status"), "premium"),
            is_not_null(col("referral_code"))
        )
    )

    # Serialize to dictionary
    serialized = condition.to_dict()
    print("Serialized condition:")
    import json
    print(json.dumps(serialized, indent=2))
    print()

    # This can be stored in expectation configurations, databases, etc.
    # and later reconstructed into the original condition object


if __name__ == "__main__":
    """Run all examples."""

    print("Row Conditions V2 API Examples")
    print("=" * 50)
    print()

    example_basic_conditions()
    example_null_conditions()
    example_set_conditions()
    example_complex_conditions()
    example_business_logic_conditions()
    example_migration_from_old_api()
    example_expectation_usage()
    example_validation_benefits()
    example_serialization()

    print("=" * 50)
    print("All examples completed!")
    print()
    print("Key benefits of the new API:")
    print("1. ✅ Works consistently across pandas, Spark, and SQL")
    print("2. ✅ Early validation with clear error messages")
    print("3. ✅ Strongly typed and IDE-friendly")
    print("4. ✅ Composable and reusable conditions")
    print("5. ✅ JSON serializable for storage and transmission")
    print("6. ✅ Backward compatible with existing expectations")
