"""Map-style validation result schema family.

Covers ColumnMapExpectation (26), ColumnPairMapExpectation (3), and
MulticolumnMapExpectation (3) = 32 map-style core expectations.

Four format-discriminated classes share a common base:

    MapResultBase
    ├── MapBooleanOnlyResult  (BOOLEAN_ONLY)
    └── MapBasicResult        (BASIC)
        └── MapSummaryResult  (SUMMARY)
            └── MapCompleteResult  (COMPLETE)

Import rules (enforced by ruff banned-api):
- Pydantic symbols come exclusively from ``great_expectations.compatibility.pydantic``.
- No PEP 604 unions (``X | Y``); use ``Optional[X]`` or ``Union[X, Y]``.
- No direct ``import pydantic``.
"""

from __future__ import annotations

from typing import Any, List, Optional

from great_expectations.compatibility import pydantic
from great_expectations.compatibility.pydantic import BaseModel
from great_expectations.core.validation_result_schemas.field_validators import (
    root_validate_engine_required_fields,
    validate_partial_unexpected_counts_fallback,
    validate_unexpected_rows_passthrough,
)


class MapResultBase(BaseModel):
    """Base for all map-style result models.

    Fields here are the always-allowed superset shared by every format variant.
    ``extra = Extra.forbid`` is intentional: the matrix runner *wants* unexpected
    fields to fail validation so they surface in findings as cleanup queue entries.
    """

    class Config:
        extra = pydantic.Extra.forbid
        arbitrary_types_allowed = True

    # Internal engine hint — declared as a normal field so it appears in the
    # values dict during root validation.  ``exclude=True`` is not used here
    # because pydantic v1's per-field exclude is Config-based; callers that want
    # to omit this field from .dict() output should call .dict(exclude={"engine_hint"}).
    engine_hint: Optional[str] = None

    # SQL-only, optional everywhere; root validator enforces presence when applicable
    unexpected_index_query: Optional[str] = None
    unexpected_index_column_names: Optional[List[str]] = None


class MapBooleanOnlyResult(MapResultBase):
    """ResultFormat.BOOLEAN_ONLY — empty result dict for map expectations.

    The parent EVR carries ``success``.  The result dict may carry only the
    SQL index-query overflow fields when ``return_unexpected_index_query=True``.
    """

    pass  # No additional fields beyond the SQL index-query fields in base


class MapBasicResult(MapResultBase):
    """ResultFormat.BASIC — counts, percents, and the partial unexpected list.

    Note: ``observed_value`` is included here because a small set of map
    expectations (e.g. ``expect_column_values_to_be_of_type``,
    ``expect_column_values_to_be_in_type_list``) emit it alongside the
    standard map fields on the pandas engine path.  It is Optional so that
    the majority of map expectations — which do *not* emit it — continue to
    validate cleanly.
    """

    element_count: Optional[int] = None
    unexpected_count: Optional[int] = None
    unexpected_percent: Optional[float] = None
    missing_count: Optional[int] = None
    missing_percent: Optional[float] = None
    unexpected_percent_total: Optional[float] = None
    unexpected_percent_nonmissing: Optional[float] = None
    partial_unexpected_list: Optional[List[Any]] = None
    # Some map expectations (e.g. expect_column_values_to_be_of_type on pandas)
    # emit observed_value alongside the standard map fields.
    observed_value: Optional[Any] = None
    # engine-typed; classified at runtime, not validated by type
    unexpected_rows: Any = None

    _validate_rows = pydantic.validator("unexpected_rows", pre=True, allow_reuse=True)(
        validate_unexpected_rows_passthrough
    )


class MapSummaryResult(MapBasicResult):
    """ResultFormat.SUMMARY — adds counts and index list for partial unexpected."""

    partial_unexpected_counts: Optional[List[Any]] = None
    partial_unexpected_index_list: Optional[List[Any]] = None

    _validate_counts = pydantic.validator("partial_unexpected_counts", pre=True, allow_reuse=True)(
        validate_partial_unexpected_counts_fallback
    )


class MapCompleteResult(MapSummaryResult):
    """ResultFormat.COMPLETE — adds the full unexpected list and index list.

    Also carries the root validator that enforces SQL engine-required fields:
    when ``engine_hint='sql'`` and ``return_unexpected_index_query=True``,
    ``unexpected_index_query`` must be present.
    """

    unexpected_list: Optional[List[Any]] = None
    unexpected_index_list: Optional[List[Any]] = None

    _root_validate = pydantic.root_validator(allow_reuse=True)(root_validate_engine_required_fields)
