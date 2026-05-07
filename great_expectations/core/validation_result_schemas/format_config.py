"""ResultFormatConfig TypedDict for internal use by the validation result dispatcher.

These types are not part of the public API and must not be exported via
great_expectations/__init__.py or decorated with @public_api.
"""

from __future__ import annotations

from typing import TypedDict


class ResultFormatConfigRequired(TypedDict):
    """Required keys always present in a parsed result-format config dict."""

    result_format: str  # one of the 4 ResultFormat enum values
    partial_unexpected_count: int
    include_unexpected_rows: bool
    map_expectation_unexpected_rows_as_dict: bool


class ResultFormatConfig(ResultFormatConfigRequired, total=False):
    """Full result-format config dict including optional keys.

    The two-class overlay pattern (required base + total=False subclass) lets us
    express "required + optional" without NotRequired[...], which requires
    Python 3.11+.  This keeps the code parseable on Python 3.10.
    """

    exclude_unexpected_values: bool
    return_unexpected_index_query: bool
