from enum import Enum


class DomainNames(str, Enum):
    COLUMN_VALUES = "column_values"


class MetricNames(str, Enum):
    BETWEEN = "between"
