"""Aggregate-style validation result schema family.

Covers AggregateExpectation types (column-level aggregate expectations such as
expect_column_mean_to_be_between, expect_column_min_to_be_between, etc.).

Four format-discriminated classes share a common base:

    AggregateResultBase
    ├── AggregateBooleanOnlyResult  (BOOLEAN_ONLY)
    └── AggregateBasicResult        (BASIC)
        └── AggregateSummaryResult  (SUMMARY)
            └── AggregateCompleteResult  (COMPLETE)

Import rules (enforced by ruff banned-api):
- Pydantic symbols come exclusively from ``great_expectations.compatibility.pydantic``.
- No PEP 604 unions (``X | Y``); use ``Optional[X]`` or ``Union[X, Y]``.
- No direct ``import pydantic``.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from great_expectations.compatibility import pydantic
from great_expectations.compatibility.pydantic import BaseModel

# Scalar = Union[int, float, str, bool, None]; observed_value is broadly typed.
# Union order matters for pydantic v1: bool must come before int (bool is a subclass of
# int); float must come before int to avoid coercion of 3.14 → 3.  Putting the more
# specific numeric types first avoids silent coercion.
ObservedValue = Union[bool, float, int, str, List[Any], Dict[str, Any], None]


class AggregateResultBase(BaseModel):
    """Base for all aggregate-style result models.

    Fields here are the always-allowed superset shared by every format variant.
    ``extra = Extra.forbid`` is intentional: the matrix runner *wants* unexpected
    fields to fail validation so they surface in findings as cleanup queue entries.
    """

    class Config:
        extra = pydantic.Extra.forbid
        arbitrary_types_allowed = True

    observed_value: ObservedValue = None
    details: Optional[Dict[str, Any]] = None


class AggregateBooleanOnlyResult(AggregateResultBase):
    """ResultFormat.BOOLEAN_ONLY — typically empty result dict for aggregate expectations.

    The parent EVR carries ``success``.  The result dict for BOOLEAN_ONLY
    aggregate expectations typically has no additional fields.
    """

    pass  # BOOLEAN_ONLY: typically empty


class AggregateBasicResult(AggregateResultBase):
    """ResultFormat.BASIC — counts, percents, and partial lists.

    Note: ``unexpected_count`` is included here because a subset of aggregate
    expectations (e.g. ``expect_column_distinct_values_to_equal_set``) emit
    it alongside the standard aggregate fields.  It is Optional so that the
    majority of aggregate expectations — which do *not* emit it — continue to
    validate cleanly.
    """

    element_count: Optional[int] = None
    missing_count: Optional[int] = None
    missing_percent: Optional[float] = None
    unexpected_count: Optional[int] = None
    partial_unexpected_list: Optional[List[Any]] = None
    partial_missing_list: Optional[List[Any]] = None


class AggregateSummaryResult(AggregateBasicResult):
    """ResultFormat.SUMMARY — aggregate expectations rarely diverge from BASIC.

    Kept explicit so the dispatcher can name it distinctly.
    """

    pass  # Aggregate expectations rarely diverge between BASIC and SUMMARY


class AggregateCompleteResult(AggregateSummaryResult):
    """ResultFormat.COMPLETE — adds the full unexpected list and index list."""

    unexpected_list: Optional[List[Any]] = None
    unexpected_index_list: Optional[List[Any]] = None
