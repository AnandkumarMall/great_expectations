from abc import ABC
from typing import Annotated, Optional

from great_expectations.compatibility.pydantic import BaseModel, Field, StrictStr

NonEmptyString = Annotated[StrictStr, Field(min_length=1)]


class AbstractClassInstantiationError(TypeError):
    def __init__(self, class_name: str) -> None:
        super().__init__(f"Cannot instantiate abstract class `{class_name}`.")


class Domain(BaseModel, ABC):
    """The abstract base class for defining all types of domains over which metrics are computed."""

    batch_id: NonEmptyString

    def __new__(cls, *args, **kwargs):
        if cls is Domain:
            raise AbstractClassInstantiationError(cls.__name__)
        return super().__new__(cls)


class Map(Domain, ABC):
    """The abstract base class for metric domain types that compute row-level calculations."""

    table: NonEmptyString
    row_condition: Optional[StrictStr] = None

    def __new__(cls, *args, **kwargs):
        if cls is Map:
            raise AbstractClassInstantiationError(cls.__name__)
        return super().__new__(cls)


class ColumnMap(Map):
    """The generic type for metrics that compute row-level calculations on a single column."""

    column: NonEmptyString

    def __init__(
        self,
        batch_id: NonEmptyString,
        table: NonEmptyString,
        column: NonEmptyString,
    ):
        self.batch_id = batch_id
        self.table = table
        self.column = column
        super().__init__(batch_id=batch_id, table=table)


DomainNames: dict[type[Domain], str] = {
    ColumnMap: "column_values",
}
