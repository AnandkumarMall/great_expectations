from typing import Optional

from great_expectations.core.types import Comparable
from great_expectations.metrics.domain import ColumnValues
from great_expectations.metrics.metric import Metric

MIN_VALUE_DESCRIPTION = "The minimum value for a column entry."
MAX_VALUE_DESCRIPTION = "The maximum value for a column entry."
STRICT_MIN_DESCRIPTION = "If True, values must be strictly larger than min_value."
STRICT_MAX_DESCRIPTION = "If True, values must be strictly smaller than max_value."


class ColumnValuesBetween(Metric, ColumnValues):
    __doc__ = f"""A metric that checks if column values fall within a specified range.

    This metric evaluates whether each value in a column falls between minimum and maximum bounds.
    The bounds can be inclusive (strict_min/strict_max=False)
                   or exclusive (strict_min/strict_max=True)

    Attributes:
        batch_id (str): Unique identifier for the batch being processed.
        table (str): Name of the table containing the column.
        column (str): Name of the column to compute metrics on.
        row_condition (Optional[str]): A condition used to filter rows.
                                       See: https://docs.greatexpectations.io/docs/core/customize_expectations/expectation_conditions/#create-an-expectation-condition
        min_value (Optional[Comparable]): {MIN_VALUE_DESCRIPTION}
                                          If None, no lower bound is enforced.
        max_value (Optional[Comparable]): {MAX_VALUE_DESCRIPTION}
                                          If None, no upper bound is enforced.
        strict_min (bool): {STRICT_MIN_DESCRIPTION} Defaults to False.
        strict_max (bool): {STRICT_MAX_DESCRIPTION} Defaults to False.

    Examples:
        A metric checking if values in column 'age' are between 0 and 100 inclusive:
        >>> ColumnValuesBetween(
        ...     batch_id="my_data_source-my_asset-year_2025",
        ...     table="users",
        ...     column="age",
        ...     min_value=0,
        ...     max_value=100
        ... )

        A metric checking if filtered values for planet 'neptune' in column 'kelvin',
        are strictly greater than 0:
        >>> ColumnValuesBetween(
        ...     batch_id="my_data_source-my_asset-year_2025",
        ...     table="temperature",
        ...     column="kelvin",
        ...     row_condition='col("planet")=="neptune"',
        ...     min_value=0,
        ...     strict_min=True,
        ... )
    """
    min_value: Optional[Comparable] = None
    max_value: Optional[Comparable] = None
    strict_min: bool = False
    strict_max: bool = False
