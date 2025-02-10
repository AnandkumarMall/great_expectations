from great_expectations.compatibility.pydantic import BaseModel, ModelMetaclass
from great_expectations.metrics.domain import AbstractClassInstantiationError, Domain, DomainNames
from great_expectations.metrics.registry import METRIC_REGISTRY
from great_expectations.validator.metric_configuration import MetricConfiguration

ALLOWABLE_METRIC_MIXINS = 1


class MixinTypeError(TypeError):
    def __init__(self, class_name: str, mixin_superclass_name: str) -> None:
        super().__init__(
            f"`{class_name}` must use a single `{mixin_superclass_name}` subclass mixin."
        )


class UnregisteredMetricTypeError(TypeError):
    def __init__(self, class_name: str, domain_class: type[Domain]) -> None:
        super().__init__(
            f"Metric `{class_name.lower()}` was not mapped to "
            f"domain `{domain_class}`, in the metric registry."
        )


class MetaMetric(ModelMetaclass):
    def __new__(cls, name, bases, attrs):
        # ensure the Domain mixin is defined
        if name != "Metric" and len(bases) != ALLOWABLE_METRIC_MIXINS + 1:
            raise MixinTypeError(name, "Domain")
        # ensure metric is registered
        for base_type in bases:
            if (
                # isinstance(base_type, type)
                issubclass(base_type, Domain) and name.lower() not in METRIC_REGISTRY[base_type]
            ):
                raise UnregisteredMetricTypeError(name, base_type)
        return super().__new__(cls, name, bases, attrs)


class Metric(BaseModel, metaclass=MetaMetric):
    """The abstract base class for defining all metrics.

    A Metric represents a measurable property that can be computed over a specific domain
    of data (e.g., a column, table, or column pair). All concrete metric implementations
    must inherit from this class and specify their domain type as a mixin.

    Examples:
        A metric for column nullity values computed on each row:

        >>> class Null(Metric, ColumnMap):
        ...     ...

        A metric for a single table row count value:

        >>> class RowCount(Metric, Table):
        ...     ...

    Notes:
        - The Metric class cannot be instantiated directly - it must be subclassed.
        - Subclasses must specify a Domain type as a mixin.
        - The specified Domain type must be registered in the METRIC_REGISTRY.
        - The MetaMetric metaclass enforces these constraints at class creation time.

    See Also:
        Domain: The base class for all domain types
        MetricConfiguration: Configuration class for metric computation
    """

    def __new__(cls, *args, **kwargs):
        if cls is Metric:
            raise AbstractClassInstantiationError(cls.__name__)
        return super().__new__(cls)

    @property
    def id(self) -> tuple[str, str, str]:
        return self.to_config().id

    @property
    def name(self) -> str:
        for base_type in self.__class__.__bases__:
            if issubclass(base_type, Domain):
                return ".".join([DomainNames[base_type], str(self.__class__.__name__).lower()])

    def to_config(self) -> MetricConfiguration:
        for base_type in self.__class__.__bases__:
            if issubclass(base_type, Domain):
                domain_keys = set(base_type.__fields__.keys())
                metric_domain_kwargs = self.dict(include=domain_keys)
                metric_value_kwargs = self.dict(exclude=domain_keys)

                return MetricConfiguration(
                    metric_name=self.name,
                    metric_domain_kwargs=metric_domain_kwargs,
                    metric_value_kwargs=metric_value_kwargs,
                )
