from abc import ABC
from typing import Annotated, Optional

from great_expectations.compatibility.pydantic import BaseModel, Field, StrictStr

NonEmptyString = Annotated[StrictStr, Field(min_length=1)]


class Domain(ABC, BaseModel):
    """The abstract base class for defining all subsets of data within a dataset."""

    batch_id: NonEmptyString


class Map(Domain, ABC):
    """The generic type for metrics that compute row-level calculations."""

    table: NonEmptyString
    row_condition: Optional[StrictStr] = None


class ColumnMap(Map):
    """The generic type for metrics that compute row-level calculations on a single column."""

    column: NonEmptyString
