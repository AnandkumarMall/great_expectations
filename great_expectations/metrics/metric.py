from typing import ClassVar, Generic, TypeVar

from great_expectations.compatibility.pydantic import BaseModel, ModelMetaclass
from great_expectations.metrics.domain import Domain
from great_expectations.validator.metric_configuration import MetricConfiguration

DomainT = TypeVar("DomainT", bound=Domain)


class MissingGenericTypeError(TypeError):
    def __init__(self, class_name: str, generic_superclass) -> None:
        super().__init__(
            f"`{class_name}` must be parametrized by a `{generic_superclass}` subclass."
        )


class MissingAttributeError(AttributeError):
    def __init__(self, attribute_name: str, class_name: str) -> None:
        super().__init__(f"`{attribute_name}` must be defined on class `{class_name}`.")


class MetricValueError(ValueError):
    def __init__(self, attribute_name: str, expected_type_description: str) -> None:
        super().__init__(f"`{attribute_name}` must be a {expected_type_description}.")


class MetaMetric(ModelMetaclass):
    def __new__(cls, name, bases, attrs):
        # ensure the domain generic is defined
        if "__orig_bases__" not in attrs:
            raise MissingGenericTypeError(name, "Domain")
        # ensure class definitions include a metric_name
        if "metric_name" not in attrs and "metric_name" not in attrs["__annotations__"]:
            raise MissingAttributeError("metric_name", name)
        # pydantic does not validate ClassVar types, so we are doing it here
        if "metric_name" in attrs and not attrs["metric_name"]:
            raise MetricValueError("metric_name", "non-empty string")
        return super().__new__(cls, name, bases, attrs)


class Metric(BaseModel, Generic[DomainT], metaclass=MetaMetric):
    """The base abstract class for defining all metrics."""

    domain: DomainT

    metric_name: ClassVar[str]

    def __init__(self, domain: DomainT, **kwargs) -> None:
        super(Metric, self).__init__(domain=domain, **kwargs)  # noqa: UP008  # workaround to allow domain as a positional argument even though pydantic doesn't lke it

    @property
    def id(self) -> tuple[str, str, str]:
        return self.to_config().id

    def to_config(self) -> MetricConfiguration:
        """All concrete Metric implementations must:
        1. Define a metric name
        2. Define which class attributes are MetricConfiguration "value" attributes.
           Value attributes specify the conditions against which metrics should be evaluated.
        """

        return MetricConfiguration(
            metric_name=self.metric_name,
            metric_domain_kwargs=self.domain.dict(),
            metric_value_kwargs=self.dict(exclude={"domain"}),
        )
