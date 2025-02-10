from great_expectations.metrics.domain import ColumnMap, Domain

DOMAIN_NAMES: dict[type[Domain], str] = {
    ColumnMap: "column_values",
}

METRIC_REGISTRY: dict[str, tuple[str, ...]] = {
    DOMAIN_NAMES[ColumnMap]: ("between",),
}
