"""Per-expectation schema overrides.

Some expectations emit result dicts that do not fit the generic map or
aggregate families.  Each override here is a standalone Pydantic model with
``extra = Extra.forbid`` so unexpected fields surface as validation errors.

Import rules (enforced by ruff banned-api):
- Pydantic symbols come exclusively from ``great_expectations.compatibility.pydantic``.
- No PEP 604 unions (``X | Y``); use ``Optional[X]`` or ``Union[X, Y]``.
- No direct ``import pydantic``.
"""
from __future__ import annotations

from great_expectations.compatibility import pydantic
from great_expectations.compatibility.pydantic import BaseModel


class ExpectColumnValuesToBeOfTypeSqlSparkResult(BaseModel):
    """ExpectColumnValuesToBeOfType bypasses _format_map_output on SQL/Spark
    and emits {observed_value: <type-name>} only."""

    class Config:
        extra = pydantic.Extra.forbid

    observed_value: str
