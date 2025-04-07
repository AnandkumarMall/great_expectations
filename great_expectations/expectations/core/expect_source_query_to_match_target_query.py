from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from great_expectations.compatibility.typing_extensions import override
from great_expectations.expectations.expectation import BatchExpectation
from great_expectations.validator.metric_configuration import MetricConfiguration

if TYPE_CHECKING:
    from great_expectations.validator.validator import ValidationDependencies


class ExpectSourceQueryToMatchTargetQuery(BatchExpectation):
    """Expect that the results of a source query match the results of a target query.

    This expectation allows comparing query results across different data sources.
    """

    target_query: str
    source_data_source_name: str
    source_query: str

    @override
    def get_validation_dependencies(
        self,
        execution_engine: Optional[Any] = None,
        runtime_configuration: Optional[dict] = None,
    ) -> ValidationDependencies:
        """Get validation dependencies for this expectation.

        Args:
            execution_engine: The execution engine to use for validation.
            runtime_configuration: Runtime configuration for validation.

        Returns:
            A ValidationDependencies object containing the metric configurations.
        """
        validation_dependencies: ValidationDependencies = super().get_validation_dependencies(
            execution_engine=execution_engine,
            runtime_configuration=runtime_configuration,
        )

        # Get source query results
        source_metric_configuration = MetricConfiguration(
            metric_name="query.table",
            metric_domain_kwargs={},
            metric_value_kwargs={
                "query": self.source_query,
                "data_source_name": self.source_data_source_name,
            },
        )
        validation_dependencies.set_metric_configuration(
            metric_name="source_query_results",
            metric_configuration=source_metric_configuration,
        )

        # Get target query results
        target_metric_configuration = MetricConfiguration(
            metric_name="query.table",
            metric_domain_kwargs={},
            metric_value_kwargs={
                "query": self.target_query,
                "data_source_name": self.source_data_source_name,
            },
        )
        validation_dependencies.set_metric_configuration(
            metric_name="target_query_results",
            metric_configuration=target_metric_configuration,
        )

        return validation_dependencies

    @override
    def _validate(
        self,
        metrics: Dict[str, Any],
        runtime_configuration: Optional[dict] = None,
        execution_engine: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """Validate that the source and target query results match.

        Args:
            metrics: The metrics computed during validation.
            runtime_configuration: Runtime configuration for validation.
            execution_engine: The execution engine used for validation.

        Returns:
            A dictionary containing the validation result.
        """
        source_results = metrics["source_query_results"]
        target_results = metrics["target_query_results"]

        success = source_results == target_results

        return {
            "success": success,
            "result": {
                "source_query_results": source_results,
                "target_query_results": target_results,
            },
        }
