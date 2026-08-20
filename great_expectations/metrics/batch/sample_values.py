
from great_expectations.metrics.batch.batch import BatchMetric
from great_expectations.metrics.metric_results import MetricResult


class SampleValuesResult(MetricResult["pd.DataFrame"]): ...


# Only resolvable (and only needed) when pandas is installed -- table.head is a
# PandasExecutionEngine-only metric. Without this, pydantic leaves the "pd.DataFrame"
# forward ref unresolved and raises ConfigError the first time a result is validated.
from great_expectations.compatibility.pandas import pandas as _pd

if _pd:
    SampleValuesResult.update_forward_refs(pd=_pd)


class SampleValues(BatchMetric[SampleValuesResult]):
    """Sample rows from a table"""

    name = "table.head"
    n_rows: int = 10
