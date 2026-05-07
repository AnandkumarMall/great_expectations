"""Unit tests for field_validators.py.

Covers:
- classify_runtime_type for every declared RuntimeTypeName enum value
- validate_partial_unexpected_counts_fallback for both valid shapes
- root_validate_engine_required_fields for the skip-when-no-hint and
  assert-when-sql-and-requested cases

All tests are marked @pytest.mark.unit and run via:
    pytest tests/unit/core/validation_result_schemas/test_field_validators.py -m unit
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import pytest

from great_expectations.compatibility import pydantic
from great_expectations.core.validation_result_schemas.field_validators import (
    classify_runtime_type,
    root_validate_engine_required_fields,
    validate_partial_unexpected_counts_fallback,
    validate_unexpected_rows_passthrough,
)
from great_expectations.core.validation_result_schemas.types import RuntimeTypeName

# ---------------------------------------------------------------------------
# Helpers — minimal Pydantic v1 model for exercising validators
# ---------------------------------------------------------------------------


class _PartialCountsModel(pydantic.BaseModel):
    """Minimal model to exercise validate_partial_unexpected_counts_fallback."""

    partial_unexpected_counts: Optional[List[Any]] = None

    _validate_counts = pydantic.validator(
        "partial_unexpected_counts", pre=True, allow_reuse=True
    )(validate_partial_unexpected_counts_fallback)


class _PassthroughModel(pydantic.BaseModel):
    """Minimal model to exercise validate_unexpected_rows_passthrough."""

    unexpected_rows: Any = None

    _validate_rows = pydantic.validator("unexpected_rows", pre=True, allow_reuse=True)(
        validate_unexpected_rows_passthrough
    )


class _EngineHintModel(pydantic.BaseModel):
    """Minimal model to exercise root_validate_engine_required_fields.

    engine_hint is a regular pydantic field (no underscore prefix) so that it
    appears in the values dict during root validation.  In pydantic v1, fields
    starting with ``_`` are silently excluded from ``__fields__`` and never
    reach the root_validator — making the SQL check dead code.  Using a plain
    field name avoids that pitfall.
    """

    engine_hint: Optional[str] = None
    return_unexpected_index_query: Optional[bool] = None
    unexpected_index_query: Optional[str] = None

    _root_validate = pydantic.root_validator(allow_reuse=True)(
        root_validate_engine_required_fields
    )


# ---------------------------------------------------------------------------
# classify_runtime_type
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_classify_none() -> None:
    assert classify_runtime_type(None) == RuntimeTypeName.NONE


@pytest.mark.unit
def test_classify_bool() -> None:
    # bool must be checked before int since bool is a subclass of int
    assert classify_runtime_type(True) == RuntimeTypeName.BOOL
    assert classify_runtime_type(False) == RuntimeTypeName.BOOL


@pytest.mark.unit
def test_classify_int() -> None:
    assert classify_runtime_type(0) == RuntimeTypeName.INT
    assert classify_runtime_type(42) == RuntimeTypeName.INT
    assert classify_runtime_type(-1) == RuntimeTypeName.INT


@pytest.mark.unit
def test_classify_float() -> None:
    assert classify_runtime_type(3.14) == RuntimeTypeName.FLOAT
    assert classify_runtime_type(0.0) == RuntimeTypeName.FLOAT


@pytest.mark.unit
def test_classify_str() -> None:
    assert classify_runtime_type("hello") == RuntimeTypeName.STR
    assert classify_runtime_type("") == RuntimeTypeName.STR


@pytest.mark.unit
def test_classify_list() -> None:
    assert classify_runtime_type([]) == RuntimeTypeName.LIST
    assert classify_runtime_type([1, 2, 3]) == RuntimeTypeName.LIST


@pytest.mark.unit
def test_classify_dict() -> None:
    assert classify_runtime_type({}) == RuntimeTypeName.DICT
    assert classify_runtime_type({"key": "value"}) == RuntimeTypeName.DICT


@pytest.mark.unit
def test_classify_pandas_dataframe() -> None:
    """pandas DataFrame should return DATAFRAME_PANDAS without requiring pandas at import time."""
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"a": [1, 2, 3]})
    assert classify_runtime_type(df) == RuntimeTypeName.DATAFRAME_PANDAS


@pytest.mark.unit
def test_classify_spark_dataframe_other_when_pyspark_unavailable() -> None:
    """When pyspark is unavailable, a mock object named DataFrame from pyspark should
    be classified as DATAFRAME_SPARK if it looks like pyspark, or OTHER otherwise."""
    # Without actual pyspark, we simulate the check using a mock
    # The classifier should detect pyspark via module path inspection
    class _FakeSparkDataFrame:
        pass

    # Give it a pyspark-like module path
    _FakeSparkDataFrame.__module__ = "pyspark.sql.dataframe"
    _FakeSparkDataFrame.__name__ = "DataFrame"

    fake_spark_df = _FakeSparkDataFrame()
    result = classify_runtime_type(fake_spark_df)
    assert result == RuntimeTypeName.DATAFRAME_SPARK


@pytest.mark.unit
def test_classify_other_for_unknown_type() -> None:
    class _CustomObject:
        pass

    assert classify_runtime_type(_CustomObject()) == RuntimeTypeName.OTHER
    assert classify_runtime_type(object()) == RuntimeTypeName.OTHER


@pytest.mark.unit
def test_classify_never_raises() -> None:
    """classify_runtime_type must never raise regardless of input."""
    # Includes edge cases: class instances, iterators, generators
    class _WeirdObject:
        def __class_getitem__(cls, item: Any) -> Any:
            raise RuntimeError("should never be called")

    for value in [
        _WeirdObject(),
        (1, 2, 3),  # tuple -> OTHER
        {1, 2, 3},  # set -> OTHER
        lambda: None,  # callable -> OTHER
    ]:
        result = classify_runtime_type(value)
        assert isinstance(result, RuntimeTypeName), f"Expected RuntimeTypeName for {value!r}"


# ---------------------------------------------------------------------------
# validate_unexpected_rows_passthrough
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_passthrough_accepts_none() -> None:
    m = _PassthroughModel(unexpected_rows=None)
    assert m.unexpected_rows is None


@pytest.mark.unit
def test_passthrough_accepts_list() -> None:
    rows = [{"a": 1}, {"a": 2}]
    m = _PassthroughModel(unexpected_rows=rows)
    assert m.unexpected_rows == rows


@pytest.mark.unit
def test_passthrough_accepts_dict() -> None:
    m = _PassthroughModel(unexpected_rows={"a": 1})
    assert m.unexpected_rows == {"a": 1}


@pytest.mark.unit
def test_passthrough_returns_value_unchanged() -> None:
    sentinel = object()
    # Can't pass an arbitrary object through pydantic's JSON serialization, but
    # we can verify the validator function directly
    result = validate_unexpected_rows_passthrough(None, sentinel)
    assert result is sentinel


# ---------------------------------------------------------------------------
# validate_partial_unexpected_counts_fallback
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_partial_counts_accepts_none() -> None:
    m = _PartialCountsModel(partial_unexpected_counts=None)
    assert m.partial_unexpected_counts is None


@pytest.mark.unit
def test_partial_counts_accepts_canonical_shape() -> None:
    """Canonical shape: [{value: x, count: n}, ...]"""
    counts = [{"value": "foo", "count": 3}, {"value": "bar", "count": 1}]
    m = _PartialCountsModel(partial_unexpected_counts=counts)
    assert m.partial_unexpected_counts == counts


@pytest.mark.unit
def test_partial_counts_accepts_error_fallback_shape() -> None:
    """Error fallback shape: [{"error": "partial_exception_counts requires a hashable type"}]"""
    fallback = [{"error": "partial_exception_counts requires a hashable type"}]
    m = _PartialCountsModel(partial_unexpected_counts=fallback)
    assert m.partial_unexpected_counts == fallback


@pytest.mark.unit
def test_partial_counts_accepts_empty_list() -> None:
    m = _PartialCountsModel(partial_unexpected_counts=[])
    assert m.partial_unexpected_counts == []


@pytest.mark.unit
def test_partial_counts_returns_value_unchanged() -> None:
    counts = [{"value": "x", "count": 5}]
    result = validate_partial_unexpected_counts_fallback(None, counts)
    assert result == counts


@pytest.mark.unit
def test_partial_counts_none_returned_as_none() -> None:
    result = validate_partial_unexpected_counts_fallback(None, None)
    assert result is None


# ---------------------------------------------------------------------------
# root_validate_engine_required_fields
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_root_validate_no_hint_is_noop() -> None:
    """When no engine hint is present, the validator is a no-op (no assertion)."""
    # No engine_hint set; return_unexpected_index_query=True but no unexpected_index_query
    # should NOT raise because there is no hint to trigger the SQL check
    values: Dict[str, Any] = {
        "return_unexpected_index_query": True,
        "unexpected_index_query": None,
    }
    result = root_validate_engine_required_fields(None, values)
    assert result == values


@pytest.mark.unit
def test_root_validate_sql_hint_with_requested_and_present() -> None:
    """When engine_hint='sql', return_unexpected_index_query=True, and
    unexpected_index_query is present, the validator should pass."""
    values: Dict[str, Any] = {
        "engine_hint": "sql",
        "return_unexpected_index_query": True,
        "unexpected_index_query": "SELECT * FROM ...",
    }
    result = root_validate_engine_required_fields(None, values)
    assert result == values


@pytest.mark.unit
def test_root_validate_sql_hint_with_requested_but_missing_raises() -> None:
    """When engine_hint='sql', return_unexpected_index_query=True, but
    unexpected_index_query is absent (None), the validator should raise ValueError."""
    values: Dict[str, Any] = {
        "engine_hint": "sql",
        "return_unexpected_index_query": True,
        "unexpected_index_query": None,
    }
    with pytest.raises((ValueError, pydantic.ValidationError)):
        root_validate_engine_required_fields(None, values)


@pytest.mark.unit
def test_root_validate_sql_hint_without_requested_is_noop() -> None:
    """When engine_hint='sql' but return_unexpected_index_query is False/absent,
    the validator should pass even without unexpected_index_query."""
    values: Dict[str, Any] = {
        "engine_hint": "sql",
        "return_unexpected_index_query": False,
        "unexpected_index_query": None,
    }
    result = root_validate_engine_required_fields(None, values)
    assert result == values


@pytest.mark.unit
def test_root_validate_non_sql_hint_with_requested_but_missing_is_noop() -> None:
    """When engine_hint is not 'sql' (e.g., 'pandas'), the SQL assertion is skipped."""
    values: Dict[str, Any] = {
        "engine_hint": "pandas",
        "return_unexpected_index_query": True,
        "unexpected_index_query": None,
    }
    result = root_validate_engine_required_fields(None, values)
    assert result == values


@pytest.mark.unit
def test_root_validate_via_model_no_hint() -> None:
    """Integration check: model construction without engine hint passes."""
    m = _EngineHintModel(
        return_unexpected_index_query=True,
        unexpected_index_query=None,
    )
    assert m.return_unexpected_index_query is True
    assert m.unexpected_index_query is None


@pytest.mark.unit
def test_root_validate_via_model_sql_enforcement_fires() -> None:
    """Model-level SQL enforcement: engine_hint='sql' + return_unexpected_index_query=True
    + unexpected_index_query=None must raise pydantic.ValidationError.

    This test verifies that engine_hint is a real pydantic field (not a private
    attribute with underscore prefix), so the root_validator actually receives it
    in the values dict and can enforce the SQL-required-field constraint.
    """
    with pytest.raises(pydantic.ValidationError):
        _EngineHintModel(
            engine_hint="sql",
            return_unexpected_index_query=True,
            unexpected_index_query=None,
        )
