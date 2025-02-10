from typing import Final

from great_expectations.metrics.domain import ColumnMap, Domain

DOMAIN_NAMES: Final[dict[type[Domain], str]] = {
    ColumnMap: "column_values",
}

METRIC_REGISTRY: Final[dict[str, tuple[str, ...]]] = {
    DOMAIN_NAMES[ColumnMap]: ("between",),
}
