"""Reproduction for community issue #10849.

Metric-resolution failures are exposed on ``ExpectationValidationResult`` as a
dictionary keyed by metric ID. The public result contract instead documents a
flat ``exception_info`` dictionary with ``raised_exception``,
``exception_traceback``, and ``exception_message`` keys.

The report uses Spark, but the malformed result is assembled by the shared
validator after backend metric resolution. Pandas reproduces the same public
API contract violation without requiring an external backend.
"""

from __future__ import annotations

import pandas as pd
import pytest

import great_expectations as gx
import great_expectations.expectations as gxe

pytestmark = pytest.mark.integration


def test_metric_resolution_error_has_flat_exception_info() -> None:
    context = gx.get_context(mode="ephemeral")
    dataframe = pd.DataFrame(
        {
            "id": range(1, 100),
            "colname": ["NOT NULL" if row_id % 4 == 0 else None for row_id in range(1, 100)],
        }
    )

    datasource = context.data_sources.add_pandas(name="issue_10849_pandas")
    asset = datasource.add_dataframe_asset(name="issue_10849_asset")
    batch_definition = asset.add_batch_definition_whole_dataframe(
        name="issue_10849_batch_definition"
    )

    suite = context.suites.add(gx.ExpectationSuite(name="issue_10849_suite"))
    suite.add_expectation(
        gxe.ExpectColumnValuesToNotBeNull(
            column="colname",
            mostly=1,
        )
    )
    suite.add_expectation(
        gxe.ExpectColumnValuesToNotBeNull(
            column="___colname___",
            mostly=1,
        )
    )
    suite.save()

    validation_definition = context.validation_definitions.add(
        gx.ValidationDefinition(
            name="issue_10849_validation_definition",
            data=batch_definition,
            suite=suite,
        )
    )

    validation_result = validation_definition.run(
        batch_parameters={"dataframe": dataframe},
        result_format="COMPLETE",
    )

    results_by_column = {
        result.expectation_config.kwargs["column"]: result for result in validation_result.results
    }
    successful_result = results_by_column["colname"]
    error_result = results_by_column["___colname___"]
    assert successful_result.exception_info == {
        "raised_exception": False,
        "exception_traceback": None,
        "exception_message": None,
    }
    assert error_result.exception_info["raised_exception"] is True
    assert "___colname___" in error_result.exception_info["exception_message"]
    assert error_result.exception_info["exception_traceback"]
