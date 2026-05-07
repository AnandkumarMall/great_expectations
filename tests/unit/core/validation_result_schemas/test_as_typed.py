"""Unit tests for ExpectationValidationResult.as_typed().

Covers requirements 2.1-2.6 and 6.1-6.5:
- Returns the correct typed model for map/aggregate expectations.
- Does not mutate the EVR in any way.
- EVR equality is preserved before and after calling as_typed().
- No new attributes appear in vars(evr) after the call.
- Missing expectation_config falls back to expectation_type='unknown' (aggregate family).
- result_format can be specified as a string, enum, or dict-with-result_format.

All tests are marked @pytest.mark.unit and run via:
    pytest tests/unit/core/validation_result_schemas/test_as_typed.py -m unit -v
"""
from __future__ import annotations

import json
from typing import Optional

import pytest

from great_expectations.core.expectation_validation_result import (
    ExpectationValidationResult,
)
from great_expectations.core.validation_result_schemas.schemas.aggregate_result import (
    AggregateBasicResult,
    AggregateBooleanOnlyResult,
    AggregateCompleteResult,
    AggregateSummaryResult,
)
from great_expectations.core.validation_result_schemas.schemas.map_result import (
    MapBasicResult,
    MapBooleanOnlyResult,
    MapCompleteResult,
    MapSummaryResult,
)
from great_expectations.expectations.expectation_configuration import (
    ExpectationConfiguration,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

MAP_BASIC_RESULT = {
    "element_count": 100,
    "unexpected_count": 0,
    "unexpected_percent": 0.0,
    "missing_count": 0,
    "missing_percent": 0.0,
    "unexpected_percent_total": 0.0,
    "unexpected_percent_nonmissing": 0.0,
    "partial_unexpected_list": [],
}

MAP_SUMMARY_RESULT = {
    **MAP_BASIC_RESULT,
    "partial_unexpected_counts": [],
    "partial_unexpected_index_list": [],
}

MAP_COMPLETE_RESULT = {
    **MAP_SUMMARY_RESULT,
    "unexpected_list": [],
    "unexpected_index_list": [],
}

AGG_BASIC_RESULT = {
    "observed_value": 42.0,
}

AGG_SUMMARY_RESULT = {
    "observed_value": 42.0,
}

AGG_COMPLETE_RESULT = {
    "observed_value": 42.0,
    "unexpected_list": None,
    "unexpected_index_list": None,
}


def build_map_evr(
    result_format: str = "BASIC", result: Optional[dict] = None
) -> ExpectationValidationResult:
    """Build a map-family EVR (expect_column_values_to_not_be_null)."""
    config = ExpectationConfiguration(
        type="expect_column_values_to_not_be_null",
        kwargs={"column": "col_a", "result_format": result_format},
    )
    return ExpectationValidationResult(
        success=True,
        expectation_config=config,
        result=result if result is not None else dict(MAP_BASIC_RESULT),
    )


def build_agg_evr(result_format: str = "BASIC") -> ExpectationValidationResult:
    """Build an aggregate-family EVR (expect_column_mean_to_be_between)."""
    config = ExpectationConfiguration(
        type="expect_column_mean_to_be_between",
        kwargs={"column": "col_a", "min_value": 0, "result_format": result_format},
    )
    return ExpectationValidationResult(
        success=True,
        expectation_config=config,
        result=dict(AGG_BASIC_RESULT),
    )


# ---------------------------------------------------------------------------
# Return type checks — map family
# ---------------------------------------------------------------------------


class TestMapFamilyReturnTypes:
    """as_typed returns the correct map-family model class for each ResultFormat."""

    @pytest.mark.unit
    def test_map_boolean_only(self):
        config = ExpectationConfiguration(
            type="expect_column_values_to_not_be_null",
            kwargs={"column": "col_a", "result_format": "BOOLEAN_ONLY"},
        )
        evr = ExpectationValidationResult(
            success=True,
            expectation_config=config,
            result={},
        )
        typed = evr.as_typed()
        assert isinstance(typed, MapBooleanOnlyResult)

    @pytest.mark.unit
    def test_map_basic(self):
        evr = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        typed = evr.as_typed()
        assert isinstance(typed, MapBasicResult)

    @pytest.mark.unit
    def test_map_summary(self):
        evr = build_map_evr(result_format="SUMMARY", result=dict(MAP_SUMMARY_RESULT))
        typed = evr.as_typed()
        assert isinstance(typed, MapSummaryResult)

    @pytest.mark.unit
    def test_map_complete(self):
        evr = build_map_evr(result_format="COMPLETE", result=dict(MAP_COMPLETE_RESULT))
        typed = evr.as_typed()
        assert isinstance(typed, MapCompleteResult)


# ---------------------------------------------------------------------------
# Return type checks — aggregate family
# ---------------------------------------------------------------------------


class TestAggregateFamilyReturnTypes:
    """as_typed returns the correct aggregate-family model class for each ResultFormat."""

    @pytest.mark.unit
    def test_aggregate_boolean_only(self):
        config = ExpectationConfiguration(
            type="expect_column_mean_to_be_between",
            kwargs={"column": "col_a", "result_format": "BOOLEAN_ONLY"},
        )
        evr = ExpectationValidationResult(
            success=True,
            expectation_config=config,
            result={},
        )
        typed = evr.as_typed()
        assert isinstance(typed, AggregateBooleanOnlyResult)

    @pytest.mark.unit
    def test_aggregate_basic(self):
        evr = build_agg_evr(result_format="BASIC")
        typed = evr.as_typed()
        assert isinstance(typed, AggregateBasicResult)

    @pytest.mark.unit
    def test_aggregate_summary(self):
        evr = build_agg_evr(result_format="SUMMARY")
        typed = evr.as_typed()
        assert isinstance(typed, AggregateSummaryResult)

    @pytest.mark.unit
    def test_aggregate_complete(self):
        config = ExpectationConfiguration(
            type="expect_column_mean_to_be_between",
            kwargs={"column": "col_a", "result_format": "COMPLETE"},
        )
        evr = ExpectationValidationResult(
            success=True,
            expectation_config=config,
            result=dict(AGG_COMPLETE_RESULT),
        )
        typed = evr.as_typed()
        assert isinstance(typed, AggregateCompleteResult)


# ---------------------------------------------------------------------------
# No mutation
# ---------------------------------------------------------------------------


class TestNoMutation:
    """as_typed must not mutate self in any way."""

    @pytest.mark.unit
    def test_result_dict_not_mutated(self):
        evr = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        before_result = dict(evr.result)
        _ = evr.as_typed()
        assert dict(evr.result) == before_result

    @pytest.mark.unit
    def test_to_json_dict_identical_after_call(self):
        evr = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        before_dict = json.dumps(evr.to_json_dict(), sort_keys=True)
        _ = evr.as_typed()
        assert json.dumps(evr.to_json_dict(), sort_keys=True) == before_dict

    @pytest.mark.unit
    def test_no_new_attributes(self):
        evr = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        before_vars = set(vars(evr).keys())
        _ = evr.as_typed()
        assert set(vars(evr).keys()) == before_vars


# ---------------------------------------------------------------------------
# EVR equality preserved
# ---------------------------------------------------------------------------


class TestEqualityPreserved:
    """as_typed must not affect EVR equality."""

    @pytest.mark.unit
    def test_equality_before_and_after_as_typed(self):
        evr1 = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        evr2 = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        assert evr1 == evr2
        _ = evr1.as_typed()
        assert evr1 == evr2

    @pytest.mark.unit
    def test_to_json_dict_byte_identical_pair(self):
        evr1 = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        evr2 = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        assert json.dumps(evr1.to_json_dict(), sort_keys=True) == json.dumps(
            evr2.to_json_dict(), sort_keys=True
        )
        _ = evr1.as_typed()
        assert json.dumps(evr1.to_json_dict(), sort_keys=True) == json.dumps(
            evr2.to_json_dict(), sort_keys=True
        )


# ---------------------------------------------------------------------------
# Missing expectation_config fallback
# ---------------------------------------------------------------------------


class TestMissingConfigFallback:
    """When expectation_config is None, expectation_type defaults to 'unknown'."""

    @pytest.mark.unit
    def test_none_config_routes_to_aggregate_fallback(self):
        """'unknown' is not in the family table → falls back to 'aggregate' family."""
        evr = ExpectationValidationResult(
            success=True,
            expectation_config=None,
            result={},
        )
        # family_for('unknown') returns 'aggregate' (fallback)
        # result_format defaults to DEFAULT_RESULT_FORMAT (SUMMARY)
        # AggregateSummaryResult is the expected class for aggregate + SUMMARY
        typed = evr.as_typed()
        assert isinstance(typed, AggregateSummaryResult)

    @pytest.mark.unit
    def test_none_config_no_mutation(self):
        evr = ExpectationValidationResult(
            success=True,
            expectation_config=None,
            result={},
        )
        before_vars = set(vars(evr).keys())
        _ = evr.as_typed()
        assert set(vars(evr).keys()) == before_vars


# ---------------------------------------------------------------------------
# result_format normalization: string, enum, dict-with-result_format
# ---------------------------------------------------------------------------


class TestResultFormatNormalization:
    """result_format from kwargs is normalized from string, enum, or dict shapes."""

    @pytest.mark.unit
    def test_string_result_format(self):
        """result_format stored as plain string in kwargs."""
        evr = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        typed = evr.as_typed()
        assert isinstance(typed, MapBasicResult)

    @pytest.mark.unit
    def test_enum_result_format(self):
        """result_format stored as ResultFormat enum in kwargs."""
        from great_expectations.core.result_format import ResultFormat

        config = ExpectationConfiguration(
            type="expect_column_values_to_not_be_null",
            kwargs={"column": "col_a", "result_format": ResultFormat.BASIC},
        )
        evr = ExpectationValidationResult(
            success=True,
            expectation_config=config,
            result=dict(MAP_BASIC_RESULT),
        )
        typed = evr.as_typed()
        assert isinstance(typed, MapBasicResult)

    @pytest.mark.unit
    def test_dict_result_format(self):
        """result_format stored as dict with 'result_format' key in kwargs."""
        config = ExpectationConfiguration(
            type="expect_column_values_to_not_be_null",
            kwargs={
                "column": "col_a",
                "result_format": {"result_format": "BASIC", "partial_unexpected_count": 20},
            },
        )
        evr = ExpectationValidationResult(
            success=True,
            expectation_config=config,
            result=dict(MAP_BASIC_RESULT),
        )
        typed = evr.as_typed()
        assert isinstance(typed, MapBasicResult)

    @pytest.mark.unit
    def test_missing_result_format_defaults_to_summary(self):
        """When result_format is absent from kwargs, DEFAULT_RESULT_FORMAT (SUMMARY) is used."""
        config = ExpectationConfiguration(
            type="expect_column_values_to_not_be_null",
            kwargs={"column": "col_a"},  # no result_format
        )
        evr = ExpectationValidationResult(
            success=True,
            expectation_config=config,
            result=dict(MAP_SUMMARY_RESULT),
        )
        typed = evr.as_typed()
        # DEFAULT_RESULT_FORMAT is SUMMARY → MapSummaryResult
        assert isinstance(typed, MapSummaryResult)


# ---------------------------------------------------------------------------
# engine_hint passthrough
# ---------------------------------------------------------------------------


class TestEngineHintPassthrough:
    """engine_hint is forwarded to the dispatcher without mutating the EVR."""

    @pytest.mark.unit
    def test_engine_hint_pandas_map_basic(self):
        evr = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        typed = evr.as_typed(engine_hint="pandas")
        assert isinstance(typed, MapBasicResult)

    @pytest.mark.unit
    def test_engine_hint_does_not_mutate_evr(self):
        evr = build_map_evr(result_format="BASIC", result=dict(MAP_BASIC_RESULT))
        before_vars = set(vars(evr).keys())
        before_result = dict(evr.result)
        _ = evr.as_typed(engine_hint="pandas")
        assert set(vars(evr).keys()) == before_vars
        assert dict(evr.result) == before_result
