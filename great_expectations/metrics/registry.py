from great_expectations.metrics.domain import ColumnMap, Domain

METRIC_REGISTRY: dict[type[Domain], tuple[str, ...]] = {
    ColumnMap: ("between",),
}
