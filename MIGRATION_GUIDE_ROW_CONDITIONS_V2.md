# Row Conditions V2 Migration Guide

This guide helps you migrate from the old string-based row conditions API to the new unified, strongly typed row conditions API.

## Overview

The new row conditions API solves several critical problems with the existing system:

1. **Inconsistent APIs**: Different execution engines required different condition parsers
2. **Late validation**: Errors weren't caught until expectation execution time
3. **Poor portability**: Expectations with row conditions couldn't move between engine types
4. **Limited functionality**: The old parsers had restricted syntax support

## Key Benefits of V2 API

✅ **Cross-engine compatibility**: Write once, run on pandas, Spark, and SQL
✅ **Early validation**: Catch errors immediately when creating conditions
✅ **Strongly typed**: IDE support with autocomplete and type checking
✅ **Composable**: Build complex conditions from simple building blocks
✅ **Serializable**: Store and transmit conditions as JSON
✅ **Backward compatible**: Existing expectations continue to work

## Quick Start

### Old API (Engine-Specific)

```python
# Pandas only
expectation = context.suite.add_expectation(
    ExpectColumnValuesToBeInSet(
        column="user_type",
        value_set=["premium", "standard"],
        row_condition='age > 18 & status == "active"',
        condition_parser="pandas"
    )
)

# SQL only
expectation = context.suite.add_expectation(
    ExpectColumnValuesToBeInSet(
        column="user_type",
        value_set=["premium", "standard"],
        row_condition='col("age") > 18',
        condition_parser="great_expectations"
    )
)
```

### New API (Cross-Engine)

```python
from great_expectations.expectations.row_conditions_v2 import col, gt, eq, and_

# Works on pandas, Spark, AND SQL!
condition = and_(
    gt(col("age"), 18),
    eq(col("status"), "active")
)

expectation = context.suite.add_expectation(
    ExpectColumnValuesToBeInSet(
        column="user_type",
        value_set=["premium", "standard"],
        row_condition_v2=condition  # New field
    )
)
```

## Migration Steps

### Step 1: Import the New API

```python
from great_expectations.expectations.row_conditions_v2 import (
    # Column reference
    col,

    # Comparison operators
    eq, ne, lt, le, gt, ge,

    # Null checks
    is_null, is_not_null,

    # Set membership
    is_in, not_in,

    # Logical operators
    and_, or_, not_
)
```

### Step 2: Convert Simple Conditions

#### Comparisons

```python
# Old pandas
row_condition = "age > 18"
condition_parser = "pandas"

# New unified
condition = gt(col("age"), 18)
```

```python
# Old GE
row_condition = 'col("status") == "active"'
condition_parser = "great_expectations"

# New unified
condition = eq(col("status"), "active")
```

#### Null Checks

```python
# Old pandas
row_condition = "email.notna()"
condition_parser = "pandas"

# New unified
condition = is_not_null(col("email"))
```

```python
# Old GE
row_condition = 'col("phone").notNull()'
condition_parser = "great_expectations"

# New unified
condition = is_not_null(col("phone"))
```

### Step 3: Convert Complex Conditions

#### Logical AND

```python
# Old pandas
row_condition = 'age > 18 & status == "active"'
condition_parser = "pandas"

# New unified
condition = and_(
    gt(col("age"), 18),
    eq(col("status"), "active")
)
```

#### Logical OR

```python
# Old pandas
row_condition = 'age < 18 | age > 65'
condition_parser = "pandas"

# New unified
condition = or_(
    lt(col("age"), 18),
    gt(col("age"), 65)
)
```

#### Set Membership

```python
# Old pandas
row_condition = 'category in ["electronics", "books"]'
condition_parser = "pandas"

# New unified
condition = is_in(col("category"), ["electronics", "books"])
```

### Step 4: Update Expectation Configurations

#### Before (Old API)

```python
{
    "type": "expect_column_values_to_be_in_set",
    "kwargs": {
        "column": "user_type",
        "value_set": ["premium", "standard"],
        "row_condition": 'age > 18 & status == "active"',
        "condition_parser": "pandas"
    }
}
```

#### After (New API)

```python
{
    "type": "expect_column_values_to_be_in_set",
    "kwargs": {
        "column": "user_type",
        "value_set": ["premium", "standard"],
        "row_condition_v2": and_(
            gt(col("age"), 18),
            eq(col("status"), "active")
        )
    }
}
```

## Common Migration Patterns

### Pattern 1: Age-Based Filtering

```python
# Old: Multiple engine-specific versions needed
pandas_condition = "age >= 18"
spark_condition = "age >= 18"
sql_condition = 'col("age") >= 18'

# New: One condition works everywhere
condition = ge(col("age"), 18)
```

### Pattern 2: Status Filtering

```python
# Old: String escaping issues
pandas_condition = 'status == "active"'  # Careful with quotes!

# New: No escaping needed
condition = eq(col("status"), "active")
```

### Pattern 3: Complex Business Logic

```python
# Old: Hard to read and maintain
pandas_condition = '(age > 18) & (status == "active") & (subscription.isin(["premium", "gold"])) & (last_login_days <= 30)'

# New: Clear and composable
condition = and_(
    gt(col("age"), 18),
    eq(col("status"), "active"),
    is_in(col("subscription"), ["premium", "gold"]),
    le(col("last_login_days"), 30)
)
```

### Pattern 4: Null Handling

```python
# Old: Different syntax per engine
pandas_condition = "email.notna()"
ge_condition = 'col("email").notNull()'

# New: Consistent syntax
condition = is_not_null(col("email"))
```

## Advanced Examples

### Complex Business Rules

```python
# Eligible customers for a promotion
promotion_eligible = and_(
    eq(col("account_status"), "active"),
    ge(col("account_age_months"), 6),
    or_(
        ge(col("total_purchases"), 1000),
        ge(col("purchase_count"), 5)
    ),
    not_in(col("country"), ["restricted_country_1", "restricted_country_2"]),
    is_not_null(col("email"))
)
```

### Risk Assessment

```python
# High-risk transaction detection
high_risk = or_(
    gt(col("amount"), 10000),
    and_(
        gt(col("amount"), 1000),
        is_in(col("merchant_category"), ["gambling", "crypto"])
    ),
    and_(
        eq(col("international"), True),
        is_null(col("verified_merchant"))
    )
)
```

## Automated Migration

For large codebases, use the migration utility:

```python
from great_expectations.expectations.row_conditions_integration import (
    migrate_string_condition_to_v2
)

# Migrate existing conditions
old_condition = 'age > 18 & status == "active"'
old_parser = "pandas"

try:
    new_condition = migrate_string_condition_to_v2(old_condition, old_parser)
    print(f"Migrated successfully: {new_condition.to_pandas_query()}")
except ValueError as e:
    print(f"Manual migration needed: {e}")
```

## Validation and Testing

### Early Error Detection

```python
# Old API: Errors only caught at runtime
try:
    validator.expect_column_values_to_be_in_set(
        column="status",
        value_set=["active"],
        row_condition="invalid syntax here",
        condition_parser="pandas"
    )
except Exception as e:
    print("Runtime error!")

# New API: Errors caught immediately
try:
    condition = ComparisonCondition(col("age"), "invalid_op", 18)
except RowConditionError as e:
    print(f"Immediate validation error: {e}")
```

### Cross-Engine Testing

```python
# Test that your condition works on all engines
condition = and_(gt(col("age"), 18), eq(col("status"), "active"))

# Pandas
pandas_query = condition.to_pandas_query()
print(f"Pandas: {pandas_query}")

# Spark
spark_column = condition.to_spark_column()
print(f"Spark: {spark_column}")

# SQL
sql_expr = condition.to_sqlalchemy_expression()
print(f"SQL: {sql_expr}")
```

## Backward Compatibility

The new API is fully backward compatible:

- Existing expectations with `row_condition` and `condition_parser` continue to work
- You can gradually migrate expectations one at a time
- Both APIs can coexist in the same suite

## Performance Considerations

The new API has minimal performance overhead:

- Condition objects are lightweight
- Conversion to engine-specific formats is fast
- No additional network calls or I/O

## Troubleshooting

### Common Issues

1. **Import Errors**
   ```python
   # Wrong
   from great_expectations.expectations.row_conditions import col

   # Correct
   from great_expectations.expectations.row_conditions_v2 import col
   ```

2. **Operator Confusion**
   ```python
   # Wrong: Using Python 'and' keyword
   condition = gt(col("age"), 18) and eq(col("status"), "active")

   # Correct: Using and_() function
   condition = and_(gt(col("age"), 18), eq(col("status"), "active"))
   ```

3. **Value Type Errors**
   ```python
   # Wrong: Invalid value type
   condition = eq(col("status"), ["active"])  # List not allowed

   # Correct: Use proper value type
   condition = eq(col("status"), "active")    # String
   condition = is_in(col("status"), ["active", "pending"])  # List for set membership
   ```

### Getting Help

- Check the validation error messages - they're designed to be helpful
- Use the migration utility for complex conditions
- Test conditions on a small dataset first
- Refer to the examples in `examples/row_conditions_v2_examples.py`

## Next Steps

1. **Start with simple conditions**: Migrate basic comparisons first
2. **Test thoroughly**: Verify conditions work on your target execution engines
3. **Update gradually**: Migrate expectations one at a time
4. **Remove old fields**: Once migrated, remove `row_condition` and `condition_parser`
5. **Share conditions**: Reuse common conditions across multiple expectations

## Benefits Realized

After migration, you'll enjoy:

- ✅ **Portability**: Move expectations between pandas, Spark, and SQL freely
- ✅ **Reliability**: Catch configuration errors immediately
- ✅ **Maintainability**: Clear, readable condition definitions
- ✅ **Productivity**: IDE support with autocomplete and type hints
- ✅ **Consistency**: Same syntax across all execution engines

The new row conditions API represents a significant improvement in Great Expectations' usability and reliability. Happy migrating!
