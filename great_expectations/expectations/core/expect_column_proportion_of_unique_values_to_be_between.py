from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Type, Union

from great_expectations.compatibility import pydantic
from great_expectations.core.suite_parameters import (
    SuiteParameterDict,  # noqa: TC001 #  # pydantic isinstance
)
from great_expectations.expectations.expectation import (
    COLUMN_DESCRIPTION,
    ColumnAggregateExpectation,
    render_suite_parameter_string,
)
from great_expectations.expectations.metadata_types import DataQualityIssues, SupportedDataSources
from great_expectations.render import (
    LegacyDescriptiveRendererType,
    LegacyRendererType,
    RenderedStringTemplateContent,
)
from great_expectations.render.renderer.renderer import renderer
from great_expectations.render.renderer_configuration import (
    RendererConfiguration,
    RendererValueType,
)
from great_expectations.render.util import (
    handle_strict_min_max,
    num_to_str,
    parse_row_condition_string_pandas_engine,
    substitute_none_for_missing,
)

if TYPE_CHECKING:
    from great_expectations.core import (
        ExpectationValidationResult,
    )
    from great_expectations.execution_engine import ExecutionEngine
    from great_expectations.expectations.expectation_configuration import (
        ExpectationConfiguration,
    )
    from great_expectations.render.renderer_configuration import AddParamArgs

EXPECTATION_SHORT_DESCRIPTION = (
    "Expect the proportion of unique values to be between a minimum value and a maximum value."
)
MIN_VALUE_DESCRIPTION = (
    "The minimum proportion of unique values (Proportions are on the range 0 to 1)."
)
MAX_VALUE_DESCRIPTION = (
    "The maximum proportion of unique values (Proportions are on the range 0 to 1)."
)
STRICT_MIN_DESCRIPTION = (
    "If True, the minimum proportion of unique values must be strictly larger than min_value."
)
STRICT_MAX_DESCRIPTION = (
    "If True, the maximum proportion of unique values must be strictly smaller than max_value."
)
DATA_QUALITY_ISSUES = [DataQualityIssues.UNIQUENESS.value]
SUPPORTED_DATA_SOURCES = [
    SupportedDataSources.PANDAS.value,
    SupportedDataSources.SPARK.value,
    SupportedDataSources.SQLITE.value,
    SupportedDataSources.POSTGRESQL.value,
    SupportedDataSources.MYSQL.value,
    SupportedDataSources.MSSQL.value,
    SupportedDataSources.BIGQUERY.value,
    SupportedDataSources.SNOWFLAKE.value,
    SupportedDataSources.DATABRICKS.value,
    SupportedDataSources.REDSHIFT.value,
]


class ExpectColumnProportionOfUniqueValuesToBeBetween(ColumnAggregateExpectation):
    __doc__ = f"""{EXPECTATION_SHORT_DESCRIPTION}

    For example, in a column containing [1, 2, 2, 3, 3, 3, 4, 4, 4, 4], there are 4 unique values and 10 total \
    values for a proportion of 0.4.

    ExpectColumnProportionOfUniqueValuesToBeBetween is a \
    Column Aggregate Expectation.

    Column Aggregate Expectations are one of the most common types of Expectation.
    They are evaluated for a single column, and produce an aggregate Metric, such as a mean, standard deviation, number of unique values, column type, etc.
    If that Metric meets the conditions you set, the Expectation considers that data valid.

    Args:
        column (str): \
            {COLUMN_DESCRIPTION}
        min_value (float or None): \
           {MIN_VALUE_DESCRIPTION}
        max_value (float or None): \
            {MAX_VALUE_DESCRIPTION}
        strict_min (boolean): \
            {STRICT_MIN_DESCRIPTION} default=False
        strict_max (boolean): \
            {STRICT_MAX_DESCRIPTION} default=False

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

    Returns:
        An [ExpectationSuiteValidationResult](https://docs.greatexpectations.io/docs/terms/validation_result)

        Exact fields vary depending on the values passed to result_format, catch_exceptions, and meta.

    Notes:
        * min_value and max_value are both inclusive unless strict_min or strict_max are set to True.
        * If min_value is None, then max_value is treated as an upper bound
        * If max_value is None, then min_value is treated as a lower bound
        * observed_value field in the result object is customized for this expectation to be a float \
          representing the proportion of unique values in the column

    See Also:
        [ExpectColumnUniqueValueCountToBeBetween](https://greatexpectations.io/expectations/expect_column_unique_value_count_to_be_between)

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

    Data Quality Issues:
        {DATA_QUALITY_ISSUES[0]}

    Example Data:
                test 	test2
            0 	"aaa"   1
            1 	"abb"   1
            2 	"acc"   1
            3   "aaa"   3

    Code Examples:
        Passing Case:
            Input:
                ExpectColumnProportionOfUniqueValuesToBeBetween(
                    column="test",
                    min_value=0,
                    max_value=0.8
                )

            Output:
                {{
                  "exception_info": {{
                    "raised_exception": false,
                    "exception_traceback": null,
                    "exception_message": null
                  }},
                  "result": {{
                    "observed_value": .75
                  }},
                  "meta": {{}},
                  "success": true
                }}

        Failing Case:
            Input:
                ExpectColumnProportionOfUniqueValuesToBeBetween(
                    column="test2",
                    min_value=0.3,
                    max_value=0.5,
                    strict_min=False,
                    strict_max=True
                )

            Output:
                {{
                  "exception_info": {{
                    "raised_exception": false,
                    "exception_traceback": null,
                    "exception_message": null
                  }},
                  "result": {{
                    "observed_value": .5
                  }},
                  "meta": {{}},
                  "success": false
                }}
    """  # noqa: E501 # FIXME CoP

    min_value: Optional[Union[float, SuiteParameterDict]] = pydantic.Field(
        default=None, description=MIN_VALUE_DESCRIPTION
    )
    max_value: Optional[Union[float, SuiteParameterDict]] = pydantic.Field(
        default=None, description=MAX_VALUE_DESCRIPTION
    )
    strict_min: bool = pydantic.Field(default=False, description=STRICT_MIN_DESCRIPTION)
    strict_max: bool = pydantic.Field(default=False, description=STRICT_MAX_DESCRIPTION)

    # This dictionary contains metadata for display in the public gallery
    library_metadata = {
        "maturity": "production",
        "tags": ["core expectation", "column aggregate expectation"],
        "contributors": ["@great_expectations"],
        "requirements": [],
        "has_full_test_suite": True,
        "manually_reviewed_code": True,
    }

    _library_metadata = library_metadata

    # Setting necessary computation metric dependencies and defining kwargs, as well as assigning kwargs default values\  # noqa: E501 # FIXME CoP
    metric_dependencies = ("column.unique_proportion",)
    success_keys = (
        "min_value",
        "strict_min",
        "max_value",
        "strict_max",
    )

    args_keys = (
        "column",
        "min_value",
        "max_value",
        "strict_min",
        "strict_max",
    )

    """ A Column Aggregate MetricProvider Decorator for the Unique Proportion"""

    class Config:
        title = "Expect column proportion of unique values to be between"

        @staticmethod
        def schema_extra(
            schema: Dict[str, Any], model: Type[ExpectColumnProportionOfUniqueValuesToBeBetween]
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

    @classmethod
    def _convert_renderer_params_to_percentages(
        cls, renderer_configuration: RendererConfiguration
    ) -> None:
        """Convert min_value and max_value from decimal to percentage strings."""
        if (
            renderer_configuration.params.min_value
            and renderer_configuration.params.min_value.value is not None
        ):
            percentage_value = (
                num_to_str(
                    renderer_configuration.params.min_value.value * 100,
                    precision=5,
                    use_locale=True,
                )
                + "%"
            )
            renderer_configuration.add_param(
                name="min_value_pct",
                param_type=RendererValueType.STRING,
                value=percentage_value,
            )
        if (
            renderer_configuration.params.max_value
            and renderer_configuration.params.max_value.value is not None
        ):
            percentage_value = (
                num_to_str(
                    renderer_configuration.params.max_value.value * 100,
                    precision=5,
                    use_locale=True,
                )
                + "%"
            )
            renderer_configuration.add_param(
                name="max_value_pct",
                param_type=RendererValueType.STRING,
                value=percentage_value,
            )

    @classmethod
    def _get_unique_template_string(cls, renderer_configuration: RendererConfiguration) -> str:
        """Generate the template string for unique values proportion."""
        params = renderer_configuration.params

        if not params.min_value and not params.max_value:
            return "may have any proportion of unique values."

        at_least_str = "greater than or equal to"
        if params.strict_min:
            at_least_str = cls._get_strict_min_string(renderer_configuration=renderer_configuration)
        at_most_str = "less than or equal to"
        if params.strict_max:
            at_most_str = cls._get_strict_max_string(renderer_configuration=renderer_configuration)

        if not params.min_value:
            return f"proportion of unique values must be {at_most_str} $max_value_pct."
        elif not params.max_value:
            return f"proportion of unique values must be {at_least_str} $min_value_pct."
        elif params.min_value.value != params.max_value.value:
            return f"proportion of unique values must be {at_least_str} $min_value_pct and {at_most_str} $max_value_pct."  # noqa: E501
        else:
            return "proportion of unique values must be exactly $min_value_pct."

    @classmethod
    def _prescriptive_template(
        cls,
        renderer_configuration: RendererConfiguration,
    ) -> RendererConfiguration:
        add_param_args: AddParamArgs = (
            ("column", RendererValueType.STRING),
            ("min_value", RendererValueType.NUMBER),
            ("max_value", RendererValueType.NUMBER),
            ("strict_min", RendererValueType.BOOLEAN),
            ("strict_max", RendererValueType.BOOLEAN),
        )
        for name, param_type in add_param_args:
            renderer_configuration.add_param(name=name, param_type=param_type)

        cls._convert_renderer_params_to_percentages(renderer_configuration)
        template_str = cls._get_unique_template_string(renderer_configuration)

        if renderer_configuration.include_column_name:
            template_str = f"$column {template_str}"

        renderer_configuration.template_str = template_str
        return renderer_configuration

    @classmethod
    def _convert_params_to_percentages(cls, params: dict) -> None:
        """Convert min_value and max_value from decimal to percentage strings."""
        if params.get("min_value") is not None:
            params["min_value_pct"] = (
                num_to_str(params["min_value"] * 100, precision=5, use_locale=True) + "%"
            )
        if params.get("max_value") is not None:
            params["max_value_pct"] = (
                num_to_str(params["max_value"] * 100, precision=5, use_locale=True) + "%"
            )

    @classmethod
    def _get_unique_template_string_from_params(cls, params: dict) -> str:
        """Generate the template string for unique values proportion from params dict."""
        if params["min_value"] is None and params["max_value"] is None:
            return "may have any proportion of unique values."

        at_least_str, at_most_str = handle_strict_min_max(params)
        if params["min_value"] is None:
            return f"proportion of unique values must be {at_most_str} $max_value_pct."
        elif params["max_value"] is None:
            return f"proportion of unique values must be {at_least_str} $min_value_pct."
        elif params["min_value"] != params["max_value"]:
            return f"proportion of unique values must be {at_least_str} $min_value_pct and {at_most_str} $max_value_pct."  # noqa: E501
        else:
            return "proportion of unique values must be exactly $min_value_pct."

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
        styling = runtime_configuration.get("styling")
        params = substitute_none_for_missing(
            configuration.kwargs,
            [
                "column",
                "min_value",
                "max_value",
                "row_condition",
                "condition_parser",
                "strict_min",
                "strict_max",
            ],
        )

        cls._convert_params_to_percentages(params)
        template_str = cls._get_unique_template_string_from_params(params)

        if include_column_name:
            template_str = f"$column {template_str}"

        if params["row_condition"] is not None:
            (
                conditional_template_str,
                conditional_params,
            ) = parse_row_condition_string_pandas_engine(params["row_condition"])
            template_str = f"{conditional_template_str}, then {template_str}"
            params.update(conditional_params)

        return [
            RenderedStringTemplateContent(
                **{
                    "content_block_type": "string_template",
                    "string_template": {
                        "template": template_str,
                        "params": params,
                        "styling": styling,
                    },
                }
            )
        ]

    @classmethod
    @renderer(
        renderer_type=LegacyDescriptiveRendererType.COLUMN_PROPERTIES_TABLE_DISTINCT_PERCENT_ROW
    )
    def _descriptive_column_properties_table_distinct_percent_row_renderer(
        cls,
        configuration: Optional[ExpectationConfiguration] = None,
        result: Optional[ExpectationValidationResult] = None,
        runtime_configuration: Optional[dict] = None,
        **kwargs,
    ):
        assert result, "Must pass in result."
        observed_value = result.result["observed_value"]
        template_string_object = RenderedStringTemplateContent(
            **{
                "content_block_type": "string_template",
                "string_template": {
                    "template": "Distinct (%)",
                    "tooltip": {
                        "content": "expect_column_proportion_of_unique_values_to_be_between"
                    },
                },
            }
        )
        if not observed_value:
            return [template_string_object, "--"]
        else:
            return [template_string_object, f"{100 * observed_value:.1f}%"]

    def _validate(
        self,
        metrics: Dict,
        runtime_configuration: Optional[dict] = None,
        execution_engine: Optional[ExecutionEngine] = None,
    ):
        return self._validate_metric_value_between(
            metric_name="column.unique_proportion",
            metrics=metrics,
            runtime_configuration=runtime_configuration,
            execution_engine=execution_engine,
        )
