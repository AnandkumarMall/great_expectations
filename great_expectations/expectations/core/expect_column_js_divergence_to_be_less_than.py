from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar, Dict, Optional, Type, Union

import altair as alt
import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

from great_expectations.compatibility import pydantic
from great_expectations.core.suite_parameters import (
    SuiteParameterDict,  # noqa: TC001 # FIXME CoP
)
from great_expectations.execution_engine.util import (
    is_valid_categorical_partition_object,
    is_valid_partition_object,
)
from great_expectations.expectations.expectation import (
    COLUMN_DESCRIPTION,
    ColumnAggregateExpectation,
    _style_row_condition,
    render_suite_parameter_string,
)
from great_expectations.expectations.metadata_types import DataQualityIssues, SupportedDataSources
from great_expectations.expectations.model_field_descriptions import FAILURE_SEVERITY_DESCRIPTION
from great_expectations.render import (
    AtomicDiagnosticRendererType,
    AtomicPrescriptiveRendererType,
    LegacyDescriptiveRendererType,
    LegacyDiagnosticRendererType,
    LegacyRendererType,
    RenderedAtomicContent,
    RenderedContentBlockContainer,
    RenderedGraphContent,
    RenderedStringTemplateContent,
    renderedAtomicValueSchema,
)
from great_expectations.render.renderer.renderer import renderer
from great_expectations.render.renderer_configuration import (
    RendererConfiguration,
    RendererSchema,
    RendererTableValue,
    RendererValueType,
)
from great_expectations.render.util import (
    coerce_stringdtype_to_object,
    num_to_str,
    parse_row_condition_string,
    substitute_none_for_missing,
)
from great_expectations.validator.metric_configuration import MetricConfiguration

if TYPE_CHECKING:
    from great_expectations.core import (
        ExpectationValidationResult,
    )
    from great_expectations.execution_engine import ExecutionEngine
    from great_expectations.expectations.expectation_configuration import (
        ExpectationConfiguration,
    )
    from great_expectations.render.renderer_configuration import AddParamArgs
    from great_expectations.validator.validator import (
        ValidationDependencies,
    )

logger = logging.getLogger(__name__)
logging.captureWarnings(True)

EXPECTATION_SHORT_DESCRIPTION = (
    "Expect the Jensen-Shannon (JS) divergence of the specified column "
    "with respect to the partition object to be lower than the provided threshold."
)
PARTITION_OBJECT_DESCRIPTION = "The expected partition object."

THRESHOLD_DESCRIPTION = (
    "The maximum JS divergence for which to return success=True. "
    "JS divergence is bounded between 0 and ln(2) ≈ 0.693 (using natural log). "
    "If JS divergence is larger than the provided threshold, the test will return success=False."
)
BUCKETIZE_DATA_DESCRIPTION = (
    "If True, then continuous data will be bucketized before evaluation. Setting "
    "this parameter to false allows evaluation of JS divergence with a None partition object for "
    "profiling against discrete data."
)
SUPPORTED_DATA_SOURCES = [
    SupportedDataSources.PANDAS.value,
    SupportedDataSources.SPARK.value,
    SupportedDataSources.SQLITE.value,
    SupportedDataSources.POSTGRESQL.value,
    SupportedDataSources.AURORA.value,
    SupportedDataSources.CITUS.value,
    SupportedDataSources.ALLOY.value,
    SupportedDataSources.NEON.value,
    SupportedDataSources.MYSQL.value,
    SupportedDataSources.SQL_SERVER.value,
    SupportedDataSources.BIGQUERY.value,
    SupportedDataSources.SNOWFLAKE.value,
    SupportedDataSources.REDSHIFT.value,
]
DATA_QUALITY_ISSUES = [DataQualityIssues.NUMERIC.value]


class ExpectColumnJSDivergenceToBeLessThan(ColumnAggregateExpectation):
    __doc__ = f"""{EXPECTATION_SHORT_DESCRIPTION}

    Jensen-Shannon (JS) divergence is a symmetrized and smoothed version of KL divergence. \
    It measures the similarity between two probability distributions. Unlike KL divergence, \
    JS divergence is always finite, symmetric, and bounded between 0 and ln(2) ≈ 0.693 \
    (using natural log). A value of 0 indicates identical distributions.

    In many practical contexts, choosing a threshold between 0.1 and 0.4 will provide a useful test.

    This expectation works on both categorical and continuous partitions. See notes below for details.

    ExpectColumnJsDivergenceToBeLessThan is a \
    Column Aggregate Expectation.

    Column Aggregate Expectations are one of the most common types of Expectation.
    They are evaluated for a single column, and produce an aggregate Metric, such as a mean, standard deviation, number of unique values, column type, etc.
    If that Metric meets the conditions you set, the Expectation considers that data valid.

    Args:
        column (str): \
            {COLUMN_DESCRIPTION}
        partition_object (dict or None): \
            {PARTITION_OBJECT_DESCRIPTION} See [partition_object](https://docs.greatexpectations.io/docs/reference/expectations/distributional_expectations/#partition-objects).
        threshold (float or None): \
            {THRESHOLD_DESCRIPTION}
        bucketize_data (boolean): \
            {BUCKETIZE_DATA_DESCRIPTION}

    Other Parameters:
        result_format (str or None): \
            Which output mode to use: BOOLEAN_ONLY, BASIC, COMPLETE, or SUMMARY. \
            For more detail, see [result_format](https://docs.greatexpectations.io/docs/reference/expectations/result_format).
        catch_exceptions (boolean or None): \
            If True, then catch exceptions and include them as part of the result object. \
            For more detail, see [catch_exceptions](https://docs.greatexpectations.io/docs/reference/expectations/standard_arguments/#catch_exceptions).
        meta (dict or None): \
            A JSON-serializable dictionary (nesting allowed) that will be included in the output without \
            modification. For more detail, see [meta](https://docs.greatexpectations.io/docs/reference/expectations/standard_arguments/#meta).
        severity (str or None): \
            {FAILURE_SEVERITY_DESCRIPTION} \
            For more detail, see [failure severity](https://docs.greatexpectations.io/docs/cloud/expectations/expectations_overview/#failure-severity).

    Returns:
        An [ExpectationSuiteValidationResult](https://docs.greatexpectations.io/docs/terms/validation_result)

        Exact fields vary depending on the values passed to result_format, catch_exceptions, and meta.

    Notes:
        * observed_value field in the result object is a float representing the JS divergence
        * details.observed_partition in the result object is a dict representing the partition \
          observed in the data
        * details.expected_partition in the result object is a dict representing the partition \
          against which the data were compared

        If the partition_object is categorical, this expectation will expect the values in column to also be \
        categorical.

        * If the column includes values that are not present in the partition, they will be assigned \
          zero expected weight. JS divergence handles this gracefully (unlike KL divergence, which \
          would go to infinity).
        * If the partition includes values that are not present in the column, the test will simply \
          include zero observed weight for that value.

        If the partition_object is continuous, this expectation will discretize the values in the column \
        according to the bins specified in the partition_object, and apply the test to the resulting distribution.

    Supported Data Sources:
        [{SUPPORTED_DATA_SOURCES[0]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[1]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[2]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[3]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[4]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[5]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[6]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[7]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[8]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[9]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[10]}](https://docs.greatexpectations.io/docs/application_integration_support/)
        [{SUPPORTED_DATA_SOURCES[11]}](https://docs.greatexpectations.io/docs/application_integration_support/)

    Data Quality Issues:
        {DATA_QUALITY_ISSUES[0]}

    Example Data:
                test
            0 	"A"
            1 	"A"
            2 	"A"
            3   "A"
            4   "A"
            5   "B"
            6   "B"
            7   "B"
            8   "C"
            9   "C"

    Code Examples:
        Passing Case:
            Input:
                ExpectColumnJSDivergenceToBeLessThan(
                    column="test",
                    partition_object={{"weights": [0.5, 0.3, 0.2], "values": ["A", "B", "C"]}},
                    threshold=0.1
            )

            Output:
                {{
                  "exception_info": {{
                    "raised_exception": false,
                    "exception_traceback": null,
                    "exception_message": null
                  }},
                  "result": {{
                    "observed_value": 0.0,
                    "details": {{
                      "observed_partition": {{
                        "values": [
                          "A",
                          "B",
                          "C"
                        ],
                        "weights": [
                          0.5,
                          0.3,
                          0.2
                        ]
                      }},
                      "expected_partition": {{
                        "values": [
                          "A",
                          "B",
                          "C"
                        ],
                        "weights": [
                          0.5,
                          0.3,
                          0.2
                        ]
                      }}
                    }}
                  }},
                  "meta": {{}},
                  "success": true
                }}

        Failing Case:
            Input:
                ExpectColumnJSDivergenceToBeLessThan(
                    column="test",
                    partition_object={{"weights": [0.3333333333333333, 0.3333333333333333, 0.3333333333333333], "values": ["A", "B", "C"]}},
                    threshold=0.01
                )

            Output:
                {{
                  "exception_info": {{
                    "raised_exception": false,
                    "exception_traceback": null,
                    "exception_message": null
                  }},
                  "result": {{
                    "observed_value": 0.017455300026098748,
                    "details": {{
                      "observed_partition": {{
                        "values": [
                          "A",
                          "B",
                          "C"
                        ],
                        "weights": [
                          0.5,
                          0.3,
                          0.2
                        ]
                      }},
                      "expected_partition": {{
                        "values": [
                          "A",
                          "B",
                          "C"
                        ],
                        "weights": [
                          0.3333333333333333,
                          0.3333333333333333,
                          0.3333333333333333
                        ]
                      }}
                    }}
                  }},
                  "meta": {{}},
                  "success": false
                }}
    """  # noqa: E501

    partition_object: Union[dict, SuiteParameterDict, None] = pydantic.Field(
        description=PARTITION_OBJECT_DESCRIPTION
    )
    threshold: Union[float, SuiteParameterDict, None] = pydantic.Field(
        description=THRESHOLD_DESCRIPTION
    )
    bucketize_data: Union[bool, SuiteParameterDict] = pydantic.Field(
        default=True, description=BUCKETIZE_DATA_DESCRIPTION
    )

    library_metadata: ClassVar[Dict[str, Union[str, list, bool]]] = {
        "maturity": "experimental",
        "tags": [
            "core expectation",
            "column aggregate expectation",
            "distributional expectation",
        ],
        "contributors": ["@great_expectations"],
        "requirements": [],
        "has_full_test_suite": False,
        "manually_reviewed_code": False,
    }

    _library_metadata = library_metadata

    success_keys = (
        "partition_object",
        "threshold",
        "bucketize_data",
    )
    args_keys = (
        "column",
        "partition_object",
        "threshold",
    )

    class Config:
        title = "Expect column JS divergence to be less than"

        @staticmethod
        def schema_extra(
            schema: Dict[str, Any], model: Type[ExpectColumnJSDivergenceToBeLessThan]
        ) -> None:
            ColumnAggregateExpectation.Config.schema_extra(schema, model)
            schema["properties"]["metadata"]["properties"].update(
                {
                    "data_quality_issues": {
                        "title": "Data Quality Issues",
                        "type": "array",
                        "const": DATA_QUALITY_ISSUES,
                    },
                    "library_metadata": {
                        "title": "Library Metadata",
                        "type": "object",
                        "const": model._library_metadata,
                    },
                    "short_description": {
                        "title": "Short Description",
                        "type": "string",
                        "const": EXPECTATION_SHORT_DESCRIPTION,
                    },
                    "supported_data_sources": {
                        "title": "Supported Data Sources",
                        "type": "array",
                        "const": SUPPORTED_DATA_SOURCES,
                    },
                }
            )

    def get_validation_dependencies(
        self,
        execution_engine: Optional[ExecutionEngine] = None,
        runtime_configuration: Optional[dict] = None,
    ) -> ValidationDependencies:
        validation_dependencies: ValidationDependencies = super().get_validation_dependencies(
            execution_engine, runtime_configuration
        )
        configuration = self.configuration
        partition_object = configuration.kwargs.get("partition_object")
        domain_kwargs = configuration.get_domain_kwargs()
        is_categorical = None
        bins = None
        if partition_object is None:
            if configuration.kwargs.get(
                "bucketize_data", self._get_default_value("bucketize_data")
            ):
                is_categorical = False
                partition_metric_configuration = MetricConfiguration(
                    metric_name="column.partition",
                    metric_domain_kwargs=domain_kwargs,
                    metric_value_kwargs={
                        "bins": "auto",
                        "allow_relative_error": False,
                    },
                )
                from great_expectations.validator.metrics_calculator import (
                    MetricsCalculator,
                )

                metrics_calculator = MetricsCalculator(
                    execution_engine=execution_engine,
                    show_progress_bars=True,
                )
                resolved_metrics, _ = metrics_calculator.compute_metrics(
                    metric_configurations=[partition_metric_configuration],
                    runtime_configuration=None,
                    min_graph_edges_pbar_enable=0,
                )

                bins = resolved_metrics[partition_metric_configuration.id]
                hist_metric_configuration = MetricConfiguration(
                    metric_name="column.histogram",
                    metric_domain_kwargs=domain_kwargs,
                    metric_value_kwargs={
                        "bins": tuple(bins),
                    },
                )
                nonnull_configuration = MetricConfiguration(
                    metric_name="column_values.nonnull.count",
                    metric_domain_kwargs=domain_kwargs,
                    metric_value_kwargs=None,
                )
                validation_dependencies.set_metric_configuration(
                    metric_name="column.partition",
                    metric_configuration=partition_metric_configuration,
                )
                validation_dependencies.set_metric_configuration(
                    metric_name="column.histogram",
                    metric_configuration=hist_metric_configuration,
                )
                validation_dependencies.set_metric_configuration(
                    metric_name="column_values.nonnull.count",
                    metric_configuration=nonnull_configuration,
                )
            else:
                is_categorical = True
                counts_configuration = MetricConfiguration(
                    metric_name="column.value_counts",
                    metric_domain_kwargs=domain_kwargs,
                    metric_value_kwargs={
                        "sort": "value",
                    },
                )
                nonnull_configuration = MetricConfiguration(
                    metric_name="column_values.nonnull.count",
                    metric_domain_kwargs=domain_kwargs,
                )
                validation_dependencies.set_metric_configuration(
                    metric_name="column.value_counts",
                    metric_configuration=counts_configuration,
                )
                validation_dependencies.set_metric_configuration(
                    metric_name="column_values.nonnull.count",
                    metric_configuration=nonnull_configuration,
                )
        if is_categorical is True or is_valid_categorical_partition_object(partition_object):
            validation_dependencies.set_metric_configuration(
                metric_name="column.value_counts",
                metric_configuration=MetricConfiguration(
                    metric_name="column.value_counts",
                    metric_domain_kwargs=domain_kwargs,
                    metric_value_kwargs={
                        "sort": "value",
                    },
                ),
            )
            validation_dependencies.set_metric_configuration(
                metric_name="column_values.nonnull.count",
                metric_configuration=MetricConfiguration(
                    metric_name="column_values.nonnull.count",
                    metric_domain_kwargs=domain_kwargs,
                    metric_value_kwargs=None,
                ),
            )
        else:
            if bins is None:
                if not is_valid_partition_object(partition_object):
                    raise ValueError("Invalid partition_object provided")  # noqa: TRY003
                bins = partition_object["bins"]

            hist_metric_configuration = MetricConfiguration(
                metric_name="column.histogram",
                metric_domain_kwargs=domain_kwargs,
                metric_value_kwargs={
                    "bins": bins,
                },
            )
            validation_dependencies.set_metric_configuration(
                metric_name="column.histogram",
                metric_configuration=hist_metric_configuration,
            )
            nonnull_configuration = MetricConfiguration(
                metric_name="column_values.nonnull.count",
                metric_domain_kwargs=domain_kwargs,
                metric_value_kwargs=None,
            )
            validation_dependencies.set_metric_configuration(
                metric_name="column_values.nonnull.count",
                metric_configuration=nonnull_configuration,
            )
            below_partition = MetricConfiguration(
                metric_name="column_values.between.count",
                metric_domain_kwargs=domain_kwargs,
                metric_value_kwargs={"max_value": bins[0], "strict_max": True},
            )
            validation_dependencies.set_metric_configuration(
                metric_name="below_partition", metric_configuration=below_partition
            )
            above_partition = MetricConfiguration(
                metric_name="column_values.between.count",
                metric_domain_kwargs=domain_kwargs,
                metric_value_kwargs={"min_value": bins[-1], "strict_min": True},
            )
            validation_dependencies.set_metric_configuration(
                metric_name="above_partition", metric_configuration=above_partition
            )

        return validation_dependencies

    def _validate(
        self,
        metrics: Dict,
        runtime_configuration: Optional[dict] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ):
        configuration = self.configuration
        bucketize_data = configuration.kwargs.get(
            "bucketize_data", self._get_default_value("bucketize_data")
        )
        partition_object = configuration.kwargs.get(
            "partition_object", self._get_default_value("partition_object")
        )
        threshold = configuration.kwargs.get("threshold", self._get_default_value("threshold"))

        if partition_object is None:
            if bucketize_data:
                bins = list(metrics["column.partition"])
                weights = list(
                    np.array(metrics["column.histogram"]) / metrics["column_values.nonnull.count"]
                )
                tail_weights = (1 - sum(weights)) / 2
                partition_object = {
                    "bins": bins,
                    "weights": weights,
                    "tail_weights": [tail_weights, tail_weights],
                }
            else:
                partition_object = {
                    "values": list(metrics["column.value_counts"].index),
                    "weights": list(
                        np.array(metrics["column.value_counts"])
                        / metrics["column_values.nonnull.count"]
                    ),
                }

        if not is_valid_partition_object(partition_object):
            raise ValueError("Invalid partition object.")  # noqa: TRY003

        if threshold is not None and ((not isinstance(threshold, (int, float))) or (threshold < 0)):
            raise ValueError("Threshold must be specified, greater than or equal to zero.")  # noqa: TRY003

        if is_valid_categorical_partition_object(partition_object):
            observed_weights = (
                metrics["column.value_counts"] / metrics["column_values.nonnull.count"]
            )
            expected_weights = pd.Series(
                partition_object["weights"],
                index=partition_object["values"],
                name="expected",
            )
            test_df = pd.concat([expected_weights, observed_weights], axis=1)

            pk = test_df["count"].fillna(0)
            qk = test_df["expected"].fillna(0)

            js_divergence = jensenshannon(pk, qk) ** 2

            if threshold is None:
                success = True
            else:
                success = js_divergence <= threshold

            return_obj = {
                "success": success,
                "result": {
                    "observed_value": js_divergence,
                    "details": {
                        "observed_partition": {
                            "values": test_df.index.tolist(),
                            "weights": pk.tolist(),
                        },
                        "expected_partition": {
                            "values": test_df.index.tolist(),
                            "weights": qk.tolist(),
                        },
                    },
                },
            }

        else:
            if bucketize_data is False:
                raise ValueError(  # noqa: TRY003
                    "JS Divergence cannot be computed with a continuous partition object and the "
                    "bucketize_data parameter set to false."
                )
            nonnull_count = metrics["column_values.nonnull.count"]
            hist = np.array(metrics["column.histogram"])

            below_partition = metrics["below_partition"]
            above_partition = metrics["above_partition"]

            observed_weights = hist / nonnull_count

            expected_weights = np.array(partition_object["weights"])

            # Strip -inf / +inf bins and fold their weights into explicit tail entries
            tail_expected = partition_object.get("tail_weights", [0, 0])

            if (partition_object["bins"][0] == -np.inf) and (
                partition_object["bins"][-1] == np.inf
            ):
                expected_bins = partition_object["bins"][1:-1]
                tail_expected = [expected_weights[0], expected_weights[-1]]
                expected_weights = expected_weights[1:-1]
                tail_observed = [observed_weights[0], observed_weights[-1]]
                observed_weights = observed_weights[1:-1]
            elif partition_object["bins"][0] == -np.inf:
                expected_bins = partition_object["bins"][1:]
                tail_expected = [expected_weights[0], tail_expected[1]]
                expected_weights = expected_weights[1:]
                tail_observed = [observed_weights[0], above_partition / nonnull_count]
                observed_weights = observed_weights[1:]
            elif partition_object["bins"][-1] == np.inf:
                expected_bins = partition_object["bins"][:-1]
                tail_expected = [tail_expected[0], expected_weights[-1]]
                expected_weights = expected_weights[:-1]
                tail_observed = [below_partition / nonnull_count, observed_weights[-1]]
                observed_weights = observed_weights[:-1]
            else:
                expected_bins = partition_object["bins"]
                tail_observed = [
                    below_partition / nonnull_count,
                    above_partition / nonnull_count,
                ]

            comb_expected_weights = np.concatenate(
                ([tail_expected[0]], expected_weights, [tail_expected[1]])
            )
            comb_observed_weights = np.concatenate(
                ([tail_observed[0]], observed_weights, [tail_observed[1]])
            )

            js_divergence = jensenshannon(comb_observed_weights, comb_expected_weights) ** 2

            if threshold is None:
                success = True
            else:
                success = js_divergence <= threshold

            return_obj = {
                "success": success,
                "result": {
                    "observed_value": js_divergence,
                    "details": {
                        "observed_partition": {
                            "bins": expected_bins,
                            "weights": observed_weights.tolist(),
                            "tail_weights": list(tail_observed),
                        },
                        "expected_partition": {
                            "bins": expected_bins,
                            "weights": expected_weights.tolist(),
                            "tail_weights": list(tail_expected),
                        },
                    },
                },
            }

        return return_obj

    # ---- Rendering helpers (shared with KL divergence chart structure) ----

    @classmethod
    def _get_js_divergence_chart(cls, partition_object, header=None):
        weights = partition_object["weights"]

        if len(weights) > 60:  # noqa: PLR2004
            return cls._get_js_divergence_partition_object_table(partition_object, header=header)

        chart_pixel_width = (len(weights) / 60.0) * 500
        chart_pixel_width = max(chart_pixel_width, 250)
        chart_container_col_width = round((len(weights) / 60.0) * 6)
        if chart_container_col_width < 4:  # noqa: PLR2004
            chart_container_col_width = 4
        elif chart_container_col_width >= 5:  # noqa: PLR2004
            chart_container_col_width = 6
        elif chart_container_col_width >= 4:  # noqa: PLR2004
            chart_container_col_width = 5

        mark_bar_args = {}
        if len(weights) == 1:
            mark_bar_args["size"] = 20

        if partition_object.get("bins"):
            bins = partition_object["bins"]
            bins_x1 = [round(value, 1) for value in bins[:-1]]
            bins_x2 = [round(value, 1) for value in bins[1:]]

            df = pd.DataFrame({"bin_min": bins_x1, "bin_max": bins_x2, "fraction": weights})

            bars = (
                alt.Chart(df)
                .mark_bar()
                .encode(
                    x="bin_min:O",
                    x2="bin_max:O",
                    y="fraction:Q",
                    tooltip=["bin_min", "bin_max", "fraction"],
                )
                .properties(width=chart_pixel_width, height=400, autosize="fit")
            )
            chart = bars.to_dict()
        elif partition_object.get("values"):
            is_boolean_list = all(isinstance(value, bool) for value in partition_object["values"])
            if is_boolean_list:
                values = [str(value) for value in partition_object["values"]]
            else:
                values = partition_object["values"]

            df = pd.DataFrame({"values": values, "fraction": weights})
            bars = (
                alt.Chart(df)
                .mark_bar()
                .encode(x="values:N", y="fraction:Q", tooltip=["values", "fraction"])
                .properties(width=chart_pixel_width, height=400, autosize="fit")
            )
            chart = bars.to_dict()

        styling = {
            "classes": [
                f"col-{chart_container_col_width!s}",
                "mt-2",
                "pl-1",
                "pr-1",
            ],
            "parent": {"styles": {"list-style-type": "none"}},
        }

        if header:
            return RenderedGraphContent(
                **{
                    "content_block_type": "graph",
                    "graph": chart,
                    "header": header,
                    "styling": styling,
                }
            )
        else:
            return RenderedGraphContent(
                **{
                    "content_block_type": "graph",
                    "graph": chart,
                    "styling": styling,
                }
            )

    @classmethod
    def _atomic_js_divergence_chart_template(cls, partition_object: dict) -> tuple:
        weights = partition_object.get("weights", [])

        chart_pixel_width = (len(weights) / 60.0) * 500
        chart_pixel_width = max(chart_pixel_width, 250)
        chart_container_col_width = round((len(weights) / 60.0) * 6)
        if chart_container_col_width < 4:  # noqa: PLR2004
            chart_container_col_width = 4
        elif chart_container_col_width >= 5:  # noqa: PLR2004
            chart_container_col_width = 6
        elif chart_container_col_width >= 4:  # noqa: PLR2004
            chart_container_col_width = 5

        mark_bar_args = {}
        if len(weights) == 1:
            mark_bar_args["size"] = 20

        chart = {}
        if partition_object.get("bins"):
            bins = partition_object["bins"]
            bins_x1 = [round(value, 1) for value in bins[:-1]]
            bins_x2 = [round(value, 1) for value in bins[1:]]

            df = pd.DataFrame({"bin_min": bins_x1, "bin_max": bins_x2, "fraction": weights})

            bars = (
                alt.Chart(df)
                .mark_bar()
                .encode(
                    x="bin_min:O",
                    x2="bin_max:O",
                    y="fraction:Q",
                    tooltip=["bin_min", "bin_max", "fraction"],
                )
                .properties(width=chart_pixel_width, height=400, autosize="fit")
            )
            chart = bars.to_dict()
        elif partition_object.get("values"):
            is_boolean_list = all(isinstance(value, bool) for value in partition_object["values"])
            if is_boolean_list:
                values = [str(value) for value in partition_object["values"]]
            else:
                values = partition_object["values"]

            df = pd.DataFrame({"values": values, "fraction": weights})
            coerce_stringdtype_to_object(df)

            bars = (
                alt.Chart(df)
                .mark_bar()
                .encode(x="values:N", y="fraction:Q", tooltip=["values", "fraction"])
                .properties(width=chart_pixel_width, height=400, autosize="fit")
            )
            chart = bars.to_dict()

        return chart, chart_container_col_width

    @classmethod
    def _get_js_divergence_partition_object_table(cls, partition_object, header=None):
        table_rows = []
        fractions = partition_object["weights"]

        if partition_object.get("bins"):
            bins = partition_object["bins"]
            for idx, fraction in enumerate(fractions):
                if idx == len(fractions) - 1:
                    table_rows.append(
                        [
                            f"[{num_to_str(bins[idx])} - {num_to_str(bins[idx + 1])}]",
                            num_to_str(fraction),
                        ]
                    )
                else:
                    table_rows.append(
                        [
                            f"[{num_to_str(bins[idx])} - {num_to_str(bins[idx + 1])})",
                            num_to_str(fraction),
                        ]
                    )
        else:
            values = partition_object["values"]
            table_rows = [[value, num_to_str(fractions[idx])] for idx, value in enumerate(values)]

        header_row = (
            ["Interval", "Fraction"] if partition_object.get("bins") else ["Value", "Fraction"]
        )
        table_styling = {
            "classes": ["table-responsive"],
            "body": {
                "classes": ["table", "table-sm", "table-bordered", "mt-2", "mb-2"],
            },
            "parent": {
                "classes": ["show-scrollbars", "p-2"],
                "styles": {
                    "list-style-type": "none",
                    "overflow": "auto",
                    "max-height": "80vh",
                },
            },
        }

        result: dict = {
            "content_block_type": "table",
            "header_row": header_row,
            "table": table_rows,
            "styling": table_styling,
        }
        if header:
            result["header"] = header
        return result

    @classmethod
    def _atomic_partition_object_table_template(cls, partition_object: dict):
        table_rows = []
        fractions = partition_object["weights"]

        if partition_object.get("bins"):
            bins = partition_object["bins"]
            for idx, fraction in enumerate(fractions):
                interval_start = num_to_str(bins[idx])
                interval_end = num_to_str(bins[idx + 1])
                interval_closing_symbol = "]" if idx == (len(fractions) - 1) else ")"
                table_rows.append(
                    [
                        RendererTableValue(
                            schema=RendererSchema(type=RendererValueType.STRING),
                            value=f"[{interval_start} - {interval_end}{interval_closing_symbol}",
                        ),
                        RendererTableValue(
                            schema=RendererSchema(type=RendererValueType.STRING),
                            value=num_to_str(fraction),
                        ),
                    ]
                )
        else:
            values = partition_object["values"]
            table_rows = [
                [
                    RendererTableValue(
                        schema=RendererSchema(type=RendererValueType.STRING),
                        value=str(value),
                    ),
                    RendererTableValue(
                        schema=RendererSchema(type=RendererValueType.STRING),
                        value=num_to_str(fractions[idx]),
                    ),
                ]
                for idx, value in enumerate(values)
            ]

        interval_or_value = "Interval" if partition_object.get("bins") else "Value"
        header_row = [
            RendererTableValue(
                schema=RendererSchema(type=RendererValueType.STRING),
                value=interval_or_value,
            ),
            RendererTableValue(
                schema=RendererSchema(type=RendererValueType.STRING), value="Fraction"
            ),
        ]

        return header_row, table_rows

    @classmethod
    def _prescriptive_template(
        cls,
        renderer_configuration: RendererConfiguration,
    ) -> RendererConfiguration:
        add_param_args: AddParamArgs = (
            ("column", RendererValueType.STRING),
            ("mostly", RendererValueType.NUMBER),
            ("threshold", RendererValueType.NUMBER),
        )
        for name, param_type in add_param_args:
            renderer_configuration.add_param(name=name, param_type=param_type)

        expected_partition_object = renderer_configuration.kwargs.get("partition_object", {})
        weights = expected_partition_object.get("weights", [])

        if not expected_partition_object:
            template_str = "can match any distribution."
        else:
            template_str = (
                "Jensen-Shannon (JS) divergence with respect to the following distribution must be "
                "lower than $threshold."
            )

        if renderer_configuration.include_column_name:
            template_str = f"$column {template_str}"

        if len(weights) > 60:  # noqa: PLR2004
            (
                renderer_configuration.header_row,
                renderer_configuration.table,
            ) = cls._atomic_partition_object_table_template(
                partition_object=expected_partition_object
            )
        else:
            renderer_configuration.graph, _ = cls._atomic_js_divergence_chart_template(
                partition_object=expected_partition_object
            )

        renderer_configuration.template_str = template_str

        return renderer_configuration

    @classmethod
    @renderer(renderer_type=AtomicPrescriptiveRendererType.SUMMARY)
    @render_suite_parameter_string
    def _prescriptive_summary(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
    ) -> RenderedAtomicContent:
        renderer_configuration = RendererConfiguration(
            configuration=configuration,
            result=result,
            runtime_configuration=runtime_configuration,
        )
        renderer_configuration = cls._prescriptive_template(
            renderer_configuration=renderer_configuration
        )

        if renderer_configuration.graph:
            value_obj = renderedAtomicValueSchema.load(
                {
                    "header": {
                        "schema": {"type": "StringValueType"},
                        "value": {
                            "template": renderer_configuration.template_str,
                            "params": renderer_configuration.params.dict(),
                        },
                    },
                    "graph": renderer_configuration.graph,
                    "meta_notes": renderer_configuration.meta_notes,
                    "schema": {"type": "GraphType"},
                }
            )
            value_type = "GraphType"
        else:
            header_row = [value.dict() for value in renderer_configuration.header_row]
            table = []
            for row in renderer_configuration.table:
                table.append([value.dict() for value in row])
            value_obj = renderedAtomicValueSchema.load(
                {
                    "header": {
                        "schema": {"type": "StringValueType"},
                        "value": {
                            "template": renderer_configuration.template_str,
                            "params": renderer_configuration.params.dict(),
                        },
                    },
                    "header_row": header_row,
                    "table": table,
                    "meta_notes": renderer_configuration.meta_notes,
                    "schema": {"type": "TableType"},
                }
            )
            value_type = "TableType"

        return RenderedAtomicContent(
            name="atomic.prescriptive.summary",
            value=value_obj,
            value_type=value_type,
        )

    @classmethod
    @renderer(renderer_type=LegacyRendererType.PRESCRIPTIVE)
    @render_suite_parameter_string
    def _prescriptive_renderer(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
        **kwargs,
    ):
        runtime_configuration = runtime_configuration or {}
        include_column_name = runtime_configuration.get("include_column_name") is not False
        _ = runtime_configuration.get("styling")
        params = substitute_none_for_missing(
            configuration.kwargs,
            [
                "column",
                "partition_object",
                "threshold",
                "row_condition",
                "condition_parser",
            ],
        )

        expected_distribution = None
        if not params.get("partition_object"):
            template_str = "can match any distribution."
        else:
            template_str = (
                "Jensen-Shannon (JS) divergence with respect to the following distribution must be "
                "lower than $threshold."
            )
            expected_distribution = cls._get_js_divergence_chart(params.get("partition_object"))

        if include_column_name:
            template_str = f"$column {template_str}"

        styling = runtime_configuration.get("styling") if runtime_configuration else None

        if params["row_condition"] is not None:
            conditional_template_str = parse_row_condition_string(params["row_condition"])

            template_str, styling = _style_row_condition(
                conditional_template_str,
                template_str,
                params,
                styling,
            )

        expectation_string_obj = {
            "content_block_type": "string_template",
            "string_template": {"template": template_str, "params": params},
        }

        if expected_distribution:
            return [expectation_string_obj, expected_distribution]
        else:
            return [expectation_string_obj]

    @classmethod
    def _atomic_diagnostic_observed_value_template(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
    ):
        observed_partition_object = result.result.get("details", {}).get("observed_partition", {})
        weights = observed_partition_object.get("weights", [])

        observed_value = (
            num_to_str(result.result.get("observed_value"))
            if result.result.get("observed_value")
            else result.result.get("observed_value")
        )
        header_template_str = "JS Divergence: $observed_value"
        header_params_with_json_schema = {
            "observed_value": {
                "schema": {"type": "string"},
                "value": str(observed_value) if observed_value else "None",
            }
        }

        chart = None
        chart_container_col_width = None
        distribution_table_header_row = None
        distribution_table_rows = None

        if len(weights) > 60:  # noqa: PLR2004
            (
                distribution_table_header_row,
                distribution_table_rows,
            ) = cls._atomic_partition_object_table_template(
                partition_object=observed_partition_object
            )
        else:
            chart, chart_container_col_width = cls._atomic_js_divergence_chart_template(
                partition_object=observed_partition_object
            )

        return (
            header_template_str,
            header_params_with_json_schema,
            chart,
            chart_container_col_width,
            distribution_table_header_row,
            distribution_table_rows,
        )

    @classmethod
    @renderer(renderer_type=AtomicDiagnosticRendererType.OBSERVED_VALUE)
    def _atomic_diagnostic_observed_value(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
    ):
        if not result.result.get("details"):
            value_obj = renderedAtomicValueSchema.load(
                {
                    "template": "--",
                    "params": {},
                    "schema": {"type": "StringValueType"},
                }
            )
            return RenderedAtomicContent(
                name="atomic.diagnostic.observed_value",
                value=value_obj,
                value_type="StringValueType",
            )

        (
            header_template_str,
            header_params_with_json_schema,
            chart,
            _chart_container_col_width,
            distribution_table_header_row,
            distribution_table_rows,
        ) = cls._atomic_diagnostic_observed_value_template(
            configuration,
            result,
            runtime_configuration,
        )

        if chart is not None:
            value_obj = renderedAtomicValueSchema.load(
                {
                    "header": {
                        "schema": {"type": "StringValueType"},
                        "value": {
                            "template": header_template_str,
                            "params": header_params_with_json_schema,
                        },
                    },
                    "graph": chart,
                    "schema": {"type": "GraphType"},
                }
            )
            value_type = "GraphType"
        else:
            value_obj = renderedAtomicValueSchema.load(
                {
                    "header": {
                        "schema": {"type": "StringValueType"},
                        "value": {
                            "template": header_template_str,
                            "params": header_params_with_json_schema,
                        },
                    },
                    "header_row": distribution_table_header_row,
                    "table": distribution_table_rows,
                    "schema": {"type": "TableType"},
                }
            )
            value_type = "TableType"

        return RenderedAtomicContent(
            name="atomic.diagnostic.observed_value",
            value=value_obj,
            value_type=value_type,
        )

    @classmethod
    @renderer(renderer_type=LegacyDiagnosticRendererType.OBSERVED_VALUE)
    def _diagnostic_observed_value_renderer(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
        **kwargs,
    ):
        if not result.result.get("details"):
            return "--"

        observed_partition_object = result.result["details"]["observed_partition"]
        observed_distribution = cls._get_js_divergence_chart(observed_partition_object)

        observed_value = (
            num_to_str(result.result.get("observed_value"))
            if result.result.get("observed_value")
            else result.result.get("observed_value")
        )

        observed_value_content_block = RenderedStringTemplateContent(
            **{
                "content_block_type": "string_template",
                "string_template": {
                    "template": "JS Divergence: $observed_value",
                    "params": {
                        "observed_value": str(observed_value) if observed_value else "None",
                    },
                    "styling": {"classes": ["mb-2"]},
                },
            }
        )

        return RenderedContentBlockContainer(
            **{
                "content_block_type": "content_block_container",
                "content_blocks": [observed_value_content_block, observed_distribution],
            }
        )

    @classmethod
    @renderer(renderer_type=LegacyDescriptiveRendererType.HISTOGRAM)
    def _descriptive_histogram_renderer(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
        **kwargs,
    ):
        assert result, "Must pass in result."
        observed_partition_object = result.result["details"]["observed_partition"]
        weights = observed_partition_object["weights"]
        if len(weights) > 60:  # noqa: PLR2004
            return None

        header = RenderedStringTemplateContent(
            **{
                "content_block_type": "string_template",
                "string_template": {
                    "template": "Histogram",
                    "tooltip": {"content": "expect_column_js_divergence_to_be_less_than"},
                    "tag": "h6",
                },
            }
        )

        return cls._get_js_divergence_chart(observed_partition_object, header)
