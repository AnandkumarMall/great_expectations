from great_expectations.compatibility import pydantic
from great_expectations.compatibility.pydantic import Extra, Field


class Offset(pydantic.BaseModel):
    """
    A threshold in which a metric will be considered passable
    """

    positive: float
    negative: float

    class Config:
        extra = Extra.forbid


class Window(pydantic.BaseModel):
    """
    A definition for a temporal window across <`range`> number of previous invocations
    """

    constraint_fn: str
    parameter_name: str
    range: int | None = Field(
        default=None,
        description="The number of previous invocations to consider. If None, all invocations will be considered.",
    )
    offset: Offset | None = None
    strict: bool = False

    class Config:
        extra = Extra.forbid
