from typing import Generic, TypeVar, get_args

from great_expectations.compatibility.pydantic import BaseModel, ModelMetaclass
from great_expectations.metrics.domain import Domain, DomainNames
from great_expectations.metrics.registry import METRIC_REGISTRY
from great_expectations.validator.metric_configuration import MetricConfiguration

DomainT = TypeVar("DomainT", bound=Domain)


class MissingGenericTypeError(TypeError):
    def __init__(self, class_name: str, generic_superclass: str) -> None:
        super().__init__(
            f"`{class_name}` must be parametrized by a `{generic_superclass}` subclass."
        )


class UnregisteredMetricTypeError(TypeError):
    def __init__(self, class_name: str, domain_class: type[Domain]) -> None:
        super().__init__(
            f"Metric `{class_name.lower()}` was not mapped to "
            f"domain `{domain_class}`, in the metric registry."
        )


class MetaMetric(ModelMetaclass):
    def __new__(cls, name, bases, attrs):
        # ensure the domain generic is defined
        if "__orig_bases__" not in attrs:
            raise MissingGenericTypeError(name, "Domain")
        # ensure metric is registered
        for base_type in attrs["__orig_bases__"]:
            for arg in get_args(base_type):
                if (
                    isinstance(arg, type)
                    and issubclass(arg, Domain)
                    and name.lower() not in METRIC_REGISTRY[arg]
                ):
                    raise UnregisteredMetricTypeError(name, arg)
        return super().__new__(cls, name, bases, attrs)


class Metric(BaseModel, Generic[DomainT], metaclass=MetaMetric):
    """The base abstract class for defining all metrics."""

    domain: DomainT

    # workaround wrapper to allow domain to be a positional argument
    # pydantic doesn't allow positional args otherwise
    def __init__(self, domain: DomainT, **kwargs) -> None:
        super(Metric, self).__init__(domain=domain, **kwargs)  # noqa: UP008  # instantiate positional arg as kwarg

    @property
    def id(self) -> tuple[str, str, str]:
        return self.to_config().id

    @property
    def name(self) -> str:
        return ".".join([DomainNames[type(self.domain)], str(self.__class__.__name__).lower()])

    def to_config(self) -> MetricConfiguration:
        return MetricConfiguration(
            metric_name=self.name,
            metric_domain_kwargs=self.domain.dict(),
            metric_value_kwargs=self.dict(exclude={"domain"}),
        )
