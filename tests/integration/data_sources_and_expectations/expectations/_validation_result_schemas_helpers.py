"""Matrix runner helpers for validation result schema tests.

Underscore-prefixed so pytest does not collect this file.

These helpers are imported by the matrix runner and its unit tests.
They are intentionally free of test framework dependencies so they can
be used in both pytest fixtures and standalone scripts.
"""
from __future__ import annotations

from great_expectations.core.validation_result_schemas.field_validators import (
    classify_runtime_type,
)

# ---------------------------------------------------------------------------
# SQL dialect normalisation table (from design.md)
# ---------------------------------------------------------------------------

_SQL_DIALECTS = frozenset(
    {
        "sql",
        "snowflake",
        "postgres",
        "redshift",
        "databricks_sql",
        "sqlite",
        "bigquery",
        "mysql",
        "mssql",
    }
)


def _normalize_engine_hint(datasource_type: str) -> str:
    """Collapse SQL dialects to 'sql'; pass through 'pandas' and 'spark'.

    Unknown types are returned as-is.
    """
    if datasource_type == "pandas":
        return "pandas"
    if datasource_type in ("spark", "dataframe"):
        return "spark"
    if datasource_type in _SQL_DIALECTS:
        return "sql"
    # Fallback: return as-is for unknown types
    return datasource_type


def assert_field_set_covered(raw_result_dict: dict, parsed_model) -> None:
    """Assert every key in raw_result_dict is reachable in parsed_model.dict().

    The parsed model may have extra fields (like engine_hint) not in the raw
    dict — that is fine.  The reverse is NOT fine: raw dict keys that are
    absent from the model indicate information loss.

    Raises AssertionError with the offending key(s) if any raw key is missing
    from the model's dict() output.
    """
    model_dict = parsed_model.dict()
    missing = [k for k in raw_result_dict if k not in model_dict]
    assert not missing, (
        f"Fields in raw_result_dict not covered by parsed model: {missing}"
    )


def summarize_raw_dict(raw: dict) -> dict:
    """Extract structure (field names and types) from a result dict, never values.

    Returns a dict with keys:
    - raw_field_set: sorted list of field names
    - raw_field_types: {field_name: RuntimeTypeName.value}
    """
    return {
        "raw_field_set": sorted(raw.keys()),
        "raw_field_types": {k: classify_runtime_type(v).value for k, v in raw.items()},
    }
