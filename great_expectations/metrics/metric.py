from abc import ABC, abstractmethod

from great_expectations.compatibility.pydantic import BaseModel
from great_expectations.validator.metric_configuration import MetricConfiguration


class Metric(BaseModel, ABC):
    @property
    def id(self) -> tuple[str, str, str]:
        return self.to_config().id

    @abstractmethod
    def to_config(self) -> MetricConfiguration: ...


class MapMetric(Metric):
    table: str
    row_condition: str

    @abstractmethod
    def to_config(self) -> MetricConfiguration: ...
