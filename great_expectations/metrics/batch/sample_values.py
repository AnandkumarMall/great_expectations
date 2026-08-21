from typing import Any

from great_expectations.compatibility.pandas import pandas as pd
from great_expectations.metrics.batch.batch import BatchMetric
from great_expectations.metrics.metric_results import MetricResult

# table.head is a PandasExecutionEngine-only metric, so this is only resolvable (and
# only needed) when pandas is installed. Parametrizing with the real class (or `Any`
# when pandas is absent) sidesteps pydantic's forward-ref resolution entirely, since
# how eagerly a bare string generic parameter gets resolved varies across pydantic v1
# versions and isn't reliable at class-definition time.
_SampleValueType = pd.DataFrame if pd else Any


class SampleValuesResult(MetricResult[_SampleValueType]): ...  # type: ignore[valid-type] # FIXME CoP


class SampleValues(BatchMetric[SampleValuesResult]):
    """Sample rows from a table"""

    name = "table.head"
    n_rows: int = 10
