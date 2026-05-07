"""Unit tests for the dispatcher module.

Covers:
- Synthetic input per (family, format) cell — all 8 combinations.
- Unknown expectation type falls back to 'aggregate'.
- SQL sniffing: engine_hint=None + unexpected_index_query in result_dict → eff_engine='sql'.
- Per-expectation override route (expect_column_values_to_be_of_type on sql/spark).
- ParseError raised with a diagnostic message on bad input.
- test_family_table_covers_core_expectations: every expect_*.py in expectations/core/ is present.

All tests are marked @pytest.mark.unit and run via:
    pytest tests/unit/core/validation_result_schemas/test_dispatcher.py -m unit -v
"""

from __future__ import annotations

from pathlib import Path

import pytest

from great_expectations.core.result_format import ResultFormat
from great_expectations.core.validation_result_schemas.dispatcher import (
    _FAMILY_TABLE,
    ParseError,
    as_typed,
    family_for,
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
from great_expectations.core.validation_result_schemas.schemas.per_expectation_overrides import (
    ExpectColumnValuesToBeOfTypeSqlSparkResult,
)

# ---------------------------------------------------------------------------
# A canonical map expectation and aggregate expectation used across tests
# ---------------------------------------------------------------------------

MAP_EXPECTATION = "expect_column_values_to_be_between"
AGG_EXPECTATION = "expect_column_mean_to_be_between"

# ---------------------------------------------------------------------------
# Minimal valid result dicts per family x format
# ---------------------------------------------------------------------------

MAP_BOOLEAN_ONLY_DICT: dict = {}
MAP_BASIC_DICT: dict = {
    "element_count": 100,
    "unexpected_count": 5,
    "unexpected_percent": 5.0,
    "missing_count": 0,
    "missing_percent": 0.0,
    "unexpected_percent_total": 5.0,
    "unexpected_percent_nonmissing": 5.0,
    "partial_unexpected_list": [1, 2, 3],
}
MAP_SUMMARY_DICT: dict = {
    **MAP_BASIC_DICT,
    "partial_unexpected_counts": [{"value": 1, "count": 2}],
    "partial_unexpected_index_list": [0, 1],
}
MAP_COMPLETE_DICT: dict = {
    **MAP_SUMMARY_DICT,
    "unexpected_list": [1, 2, 3, 4, 5],
    "unexpected_index_list": [0, 1, 2, 3, 4],
}

AGG_BOOLEAN_ONLY_DICT: dict = {}
AGG_BASIC_DICT: dict = {"observed_value": 42.0}
AGG_SUMMARY_DICT: dict = {"observed_value": 42.0}
AGG_COMPLETE_DICT: dict = {
    "observed_value": 42.0,
    "unexpected_list": None,
    "unexpected_index_list": None,
}


# ---------------------------------------------------------------------------
# (family, format) matrix — 8 cells
# ---------------------------------------------------------------------------


class TestFamilyFormatMatrix:
    """as_typed returns the correct model class for every (family, format) cell."""

    @pytest.mark.unit
    def test_map_boolean_only(self):
        result = as_typed(
            MAP_BOOLEAN_ONLY_DICT,
            expectation_type=MAP_EXPECTATION,
            result_format=ResultFormat.BOOLEAN_ONLY,
        )
        assert isinstance(result, MapBooleanOnlyResult)

    @pytest.mark.unit
    def test_map_basic(self):
        result = as_typed(
            MAP_BASIC_DICT,
            expectation_type=MAP_EXPECTATION,
            result_format=ResultFormat.BASIC,
        )
        assert isinstance(result, MapBasicResult)
        assert result.element_count == 100
        assert result.unexpected_count == 5

    @pytest.mark.unit
    def test_map_summary(self):
        result = as_typed(
            MAP_SUMMARY_DICT,
            expectation_type=MAP_EXPECTATION,
            result_format=ResultFormat.SUMMARY,
        )
        assert isinstance(result, MapSummaryResult)
        assert result.partial_unexpected_index_list == [0, 1]

    @pytest.mark.unit
    def test_map_complete(self):
        result = as_typed(
            MAP_COMPLETE_DICT,
            expectation_type=MAP_EXPECTATION,
            result_format=ResultFormat.COMPLETE,
        )
        assert isinstance(result, MapCompleteResult)
        assert result.unexpected_list == [1, 2, 3, 4, 5]

    @pytest.mark.unit
    def test_aggregate_boolean_only(self):
        result = as_typed(
            AGG_BOOLEAN_ONLY_DICT,
            expectation_type=AGG_EXPECTATION,
            result_format=ResultFormat.BOOLEAN_ONLY,
        )
        assert isinstance(result, AggregateBooleanOnlyResult)

    @pytest.mark.unit
    def test_aggregate_basic(self):
        result = as_typed(
            AGG_BASIC_DICT,
            expectation_type=AGG_EXPECTATION,
            result_format=ResultFormat.BASIC,
        )
        assert isinstance(result, AggregateBasicResult)
        assert result.observed_value == 42.0

    @pytest.mark.unit
    def test_aggregate_summary(self):
        result = as_typed(
            AGG_SUMMARY_DICT,
            expectation_type=AGG_EXPECTATION,
            result_format=ResultFormat.SUMMARY,
        )
        assert isinstance(result, AggregateSummaryResult)

    @pytest.mark.unit
    def test_aggregate_complete(self):
        result = as_typed(
            AGG_COMPLETE_DICT,
            expectation_type=AGG_EXPECTATION,
            result_format=ResultFormat.COMPLETE,
        )
        assert isinstance(result, AggregateCompleteResult)


# ---------------------------------------------------------------------------
# family_for — unknown type falls back to 'aggregate'
# ---------------------------------------------------------------------------


class TestFamilyFor:
    @pytest.mark.unit
    def test_known_map_type(self):
        assert family_for("expect_column_values_to_be_between") == "map"

    @pytest.mark.unit
    def test_known_aggregate_type(self):
        assert family_for("expect_column_mean_to_be_between") == "aggregate"

    @pytest.mark.unit
    def test_unknown_type_falls_back_to_aggregate(self):
        assert family_for("expect_some_custom_unknown_expectation") == "aggregate"

    @pytest.mark.unit
    def test_unknown_type_dispatches_to_aggregate_class(self):
        """as_typed uses 'aggregate' family for unknown expectation types."""
        result = as_typed(
            AGG_BASIC_DICT,
            expectation_type="expect_some_custom_unknown_expectation",
            result_format=ResultFormat.BASIC,
        )
        assert isinstance(result, AggregateBasicResult)


# ---------------------------------------------------------------------------
# SQL sniffing
# ---------------------------------------------------------------------------


class TestSqlSniffing:
    @pytest.mark.unit
    def test_sql_sniff_sets_engine_via_unexpected_index_query(self):
        """When engine_hint is None but unexpected_index_query is in result_dict,
        eff_engine is sniffed as 'sql' and engine_hint is propagated to the model."""
        result_dict = {
            **MAP_COMPLETE_DICT,
            "unexpected_index_query": "SELECT * FROM table WHERE x < 0",
        }
        result = as_typed(
            result_dict,
            expectation_type=MAP_EXPECTATION,
            result_format=ResultFormat.COMPLETE,
            engine_hint=None,
        )
        assert isinstance(result, MapCompleteResult)
        assert result.unexpected_index_query == "SELECT * FROM table WHERE x < 0"
        assert result.engine_hint == "sql"

    @pytest.mark.unit
    def test_explicit_engine_hint_takes_precedence(self):
        """When engine_hint is supplied, SQL sniffing is bypassed."""
        result_dict = {
            **MAP_COMPLETE_DICT,
            "unexpected_index_query": "SELECT * FROM table WHERE x < 0",
        }
        result = as_typed(
            result_dict,
            expectation_type=MAP_EXPECTATION,
            result_format=ResultFormat.COMPLETE,
            engine_hint="pandas",
        )
        assert isinstance(result, MapCompleteResult)
        assert result.engine_hint == "pandas"

    @pytest.mark.unit
    def test_no_sniff_without_index_query(self):
        """When result_dict has no unexpected_index_query and engine_hint is None,
        engine_hint is not injected into the model."""
        result = as_typed(
            MAP_COMPLETE_DICT,
            expectation_type=MAP_EXPECTATION,
            result_format=ResultFormat.COMPLETE,
            engine_hint=None,
        )
        assert isinstance(result, MapCompleteResult)
        assert result.engine_hint is None


# ---------------------------------------------------------------------------
# Per-expectation override route
# ---------------------------------------------------------------------------


class TestPerExpectationOverride:
    @pytest.mark.unit
    def test_override_with_sql_engine_hint(self):
        """expect_column_values_to_be_of_type + sql → ExpectColumnValuesToBeOfTypeSqlSparkResult."""
        result_dict = {"observed_value": "int64"}
        result = as_typed(
            result_dict,
            expectation_type="expect_column_values_to_be_of_type",
            result_format=ResultFormat.SUMMARY,
            engine_hint="sql",
        )
        assert isinstance(result, ExpectColumnValuesToBeOfTypeSqlSparkResult)
        assert result.observed_value == "int64"

    @pytest.mark.unit
    def test_override_with_spark_engine_hint(self):
        """expect_column_values_to_be_of_type + spark → same override class."""
        result_dict = {"observed_value": "LongType"}
        result = as_typed(
            result_dict,
            expectation_type="expect_column_values_to_be_of_type",
            result_format=ResultFormat.COMPLETE,
            engine_hint="spark",
        )
        assert isinstance(result, ExpectColumnValuesToBeOfTypeSqlSparkResult)
        assert result.observed_value == "LongType"

    @pytest.mark.unit
    def test_override_sql_engine_hint_direct(self):
        """Explicit engine_hint='sql' triggers the override (no sniffing needed)."""
        result_dict = {"observed_value": "int64"}
        result = as_typed(
            result_dict,
            expectation_type="expect_column_values_to_be_of_type",
            result_format=ResultFormat.COMPLETE,
            engine_hint="sql",
        )
        assert isinstance(result, ExpectColumnValuesToBeOfTypeSqlSparkResult)
        assert result.observed_value == "int64"

    @pytest.mark.unit
    def test_no_override_without_engine_hint(self):
        """Without sql/spark engine_hint, falls through to family dispatch (map)."""
        result_dict = MAP_BASIC_DICT
        result = as_typed(
            result_dict,
            expectation_type="expect_column_values_to_be_of_type",
            result_format=ResultFormat.BASIC,
            engine_hint=None,
        )
        assert isinstance(result, MapBasicResult)


# ---------------------------------------------------------------------------
# ParseError — raised with diagnostic message
# ---------------------------------------------------------------------------


class TestParseError:
    @pytest.mark.unit
    def test_parse_error_raised_on_bad_dict(self):
        """A result_dict with extra fields not accepted by the schema → ParseError."""
        bad_dict = {"totally_unknown_field": "bad_value", "another_bad": 999}
        with pytest.raises(ParseError) as exc_info:
            as_typed(
                bad_dict,
                expectation_type=MAP_EXPECTATION,
                result_format=ResultFormat.BOOLEAN_ONLY,
            )
        msg = str(exc_info.value)
        assert "MapBooleanOnlyResult" in msg or "expect_column_values_to_be_between" in msg

    @pytest.mark.unit
    def test_parse_error_raised_for_override_on_bad_dict(self):
        """Override path raises ParseError when schema rejects extra/missing fields."""
        # ExpectColumnValuesToBeOfTypeSqlSparkResult has extra=forbid.
        # An extra field not on the model will trigger validation error.
        bad_dict = {"observed_value": "int64", "unexpected_extra_field": "boom"}
        with pytest.raises(ParseError) as exc_info:
            as_typed(
                bad_dict,
                expectation_type="expect_column_values_to_be_of_type",
                result_format=ResultFormat.SUMMARY,
                engine_hint="sql",
            )
        msg = str(exc_info.value)
        assert "expect_column_values_to_be_of_type" in msg

    @pytest.mark.unit
    def test_parse_error_wraps_validation_error(self):
        """ParseError.__cause__ is a pydantic.ValidationError."""
        from great_expectations.compatibility import pydantic

        bad_dict = {"bad_field": "unexpected"}
        with pytest.raises(ParseError) as exc_info:
            as_typed(
                bad_dict,
                expectation_type=AGG_EXPECTATION,
                result_format=ResultFormat.BOOLEAN_ONLY,
            )
        assert isinstance(exc_info.value.__cause__, pydantic.ValidationError)


# ---------------------------------------------------------------------------
# Coverage test — every expect_*.py in expectations/core/ must be in _FAMILY_TABLE
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_family_table_covers_core_expectations():
    """Every expect_*.py file in expectations/core/ must appear in _FAMILY_TABLE."""
    core_dir = (
        Path(__file__).parent
        / ".."
        / ".."
        / ".."
        / ".."
        / "great_expectations"
        / "expectations"
        / "core"
    )
    core_files = list(core_dir.glob("expect_*.py"))
    expectation_names = {
        f.name.replace(".py", "") for f in core_files if not f.name.startswith("__")
    }
    missing = expectation_names - set(_FAMILY_TABLE.keys())
    assert not missing, f"Missing from _FAMILY_TABLE: {sorted(missing)}"
