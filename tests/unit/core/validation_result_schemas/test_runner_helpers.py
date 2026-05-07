"""Unit tests for matrix runner helpers.

Covers:
- assert_field_set_covered: all raw keys present in model passes;
  missing raw key raises AssertionError with key name; model extras are ignored
- summarize_raw_dict: empty dict, scalar/list/dict values, None values;
  structure only — never values
- _normalize_engine_hint: pandas passthrough, spark/dataframe normalization,
  all SQL dialects collapse to 'sql', unknown types returned as-is

All tests are marked @pytest.mark.unit and run via:
    pytest tests/unit/core/validation_result_schemas/test_runner_helpers.py -m unit
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pytest

from great_expectations.compatibility import pydantic
from great_expectations.core.validation_result_schemas.types import RuntimeTypeName
from tests.integration.data_sources_and_expectations.expectations import (
    _validation_result_schemas_helpers as _helpers,
)

_normalize_engine_hint = _helpers._normalize_engine_hint
assert_field_set_covered = _helpers.assert_field_set_covered
summarize_raw_dict = _helpers.summarize_raw_dict

# ---------------------------------------------------------------------------
# Minimal pydantic model for exercising assert_field_set_covered
# ---------------------------------------------------------------------------


class _SimpleModel(pydantic.BaseModel):
    """Minimal model with a known field set, plus an extra engine_hint field."""

    success: Optional[bool] = None
    result: Optional[Dict[str, Any]] = None
    exception_info: Optional[Dict[str, Any]] = None
    engine_hint: Optional[str] = None


# ---------------------------------------------------------------------------
# assert_field_set_covered
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_assert_field_set_covered_all_present() -> None:
    """When all raw keys exist in the model dict, no assertion is raised."""
    raw = {"success": True, "result": {"observed_value": 42}}
    model = _SimpleModel(success=True, result={"observed_value": 42})
    # Should not raise
    assert_field_set_covered(raw, model)


@pytest.mark.unit
def test_assert_field_set_covered_model_extra_keys_are_ok() -> None:
    """Model may have extra keys (engine_hint) not in raw — that's fine."""
    raw = {"success": True}
    model = _SimpleModel(success=True, engine_hint="pandas")
    # engine_hint is in model but not in raw — should not raise
    assert_field_set_covered(raw, model)


@pytest.mark.unit
def test_assert_field_set_covered_missing_raw_key_raises() -> None:
    """A raw key absent from the model dict causes AssertionError."""

    class _NarrowModel(pydantic.BaseModel):
        success: Optional[bool] = None

    raw = {"success": True, "missing_field": "some_value"}
    model = _NarrowModel(success=True)
    with pytest.raises(AssertionError, match="missing_field"):
        assert_field_set_covered(raw, model)


@pytest.mark.unit
def test_assert_field_set_covered_multiple_missing_keys_reported() -> None:
    """All absent keys are reported together in the AssertionError message."""

    class _EmptyModel(pydantic.BaseModel):
        pass

    raw = {"key_a": 1, "key_b": 2}
    model = _EmptyModel()
    with pytest.raises(AssertionError) as exc_info:
        assert_field_set_covered(raw, model)
    msg = str(exc_info.value)
    assert "key_a" in msg
    assert "key_b" in msg


# ---------------------------------------------------------------------------
# summarize_raw_dict
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_summarize_raw_dict_empty() -> None:
    """Empty dict returns empty raw_field_set and raw_field_types."""
    result = summarize_raw_dict({})
    assert result == {"raw_field_set": [], "raw_field_types": {}}


@pytest.mark.unit
def test_summarize_raw_dict_scalar_values() -> None:
    """Scalar values are classified to the correct RuntimeTypeName."""
    raw = {
        "an_int": 42,
        "a_float": 3.14,
        "a_str": "hello",
        "a_bool": True,
    }
    result = summarize_raw_dict(raw)
    assert result["raw_field_set"] == sorted(raw.keys())
    assert result["raw_field_types"]["an_int"] == RuntimeTypeName.INT.value
    assert result["raw_field_types"]["a_float"] == RuntimeTypeName.FLOAT.value
    assert result["raw_field_types"]["a_str"] == RuntimeTypeName.STR.value
    assert result["raw_field_types"]["a_bool"] == RuntimeTypeName.BOOL.value


@pytest.mark.unit
def test_summarize_raw_dict_collection_values() -> None:
    """list and dict values are classified correctly."""
    raw = {
        "a_list": [1, 2, 3],
        "a_dict": {"nested": True},
    }
    result = summarize_raw_dict(raw)
    assert result["raw_field_types"]["a_list"] == RuntimeTypeName.LIST.value
    assert result["raw_field_types"]["a_dict"] == RuntimeTypeName.DICT.value


@pytest.mark.unit
def test_summarize_raw_dict_none_values() -> None:
    """None values are classified as RuntimeTypeName.NONE."""
    raw = {"nullable_field": None}
    result = summarize_raw_dict(raw)
    assert result["raw_field_types"]["nullable_field"] == RuntimeTypeName.NONE.value


@pytest.mark.unit
def test_summarize_raw_dict_field_set_is_sorted() -> None:
    """raw_field_set must be in sorted order regardless of insertion order."""
    raw = {"z_last": 1, "a_first": 2, "m_middle": 3}
    result = summarize_raw_dict(raw)
    assert result["raw_field_set"] == ["a_first", "m_middle", "z_last"]


@pytest.mark.unit
def test_summarize_raw_dict_never_includes_values() -> None:
    """The result dict must not contain raw field values — only structure."""
    raw = {"secret_value": "do_not_leak_this"}
    result = summarize_raw_dict(raw)
    # Values should not appear anywhere in the output
    assert "do_not_leak_this" not in str(result)
    # But the key (structure) should be present
    assert "secret_value" in result["raw_field_set"]


# ---------------------------------------------------------------------------
# _normalize_engine_hint
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_normalize_engine_hint_pandas() -> None:
    assert _normalize_engine_hint("pandas") == "pandas"


@pytest.mark.unit
def test_normalize_engine_hint_spark() -> None:
    assert _normalize_engine_hint("spark") == "spark"


@pytest.mark.unit
def test_normalize_engine_hint_dataframe_to_spark() -> None:
    assert _normalize_engine_hint("dataframe") == "spark"


@pytest.mark.unit
@pytest.mark.parametrize(
    "dialect",
    [
        "sql",
        "snowflake",
        "postgres",
        "redshift",
        "databricks_sql",
        "sqlite",
        "bigquery",
        "mysql",
        "mssql",
    ],
)
def test_normalize_engine_hint_sql_dialects(dialect: str) -> None:
    """All SQL dialects collapse to 'sql'."""
    assert _normalize_engine_hint(dialect) == "sql"


@pytest.mark.unit
def test_normalize_engine_hint_unknown_passthrough() -> None:
    """Unknown engine types are returned as-is."""
    assert _normalize_engine_hint("unknown_engine_xyz") == "unknown_engine_xyz"
    assert _normalize_engine_hint("dask") == "dask"
    assert _normalize_engine_hint("") == ""
