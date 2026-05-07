"""Type definitions for validation result schemas.

Defines the enumeration types and TypedDicts used across the
validation_result_schemas package.
"""
from __future__ import annotations

from enum import Enum
from typing import Dict, List, Optional, TypedDict


class Status(str, Enum):
    PARSED = "parsed"
    FAILED = "failed"


class RuntimeTypeName(str, Enum):
    NONE = "none"
    INT = "int"
    FLOAT = "float"
    STR = "str"
    BOOL = "bool"
    LIST = "list"
    DICT = "dict"
    DATAFRAME_PANDAS = "DataFrame"
    DATAFRAME_SPARK = "SparkDataFrame"
    OTHER = "other"


class CellCoordinates(TypedDict):
    expectation_type: str
    result_format: str  # ResultFormat enum value
    engine: str  # 'pandas' | 'spark' | 'sql'
    datasource_test_id: str


class Finding(TypedDict, total=False):
    expectation_type: str
    result_format: str
    engine: str
    datasource_test_id: str
    status: str  # Status enum value
    raw_field_set: List[str]
    raw_field_types: Dict[str, str]  # field name -> RuntimeTypeName value
    matched_variant: Optional[str]
    schema_required_fields_present: List[str]
    schema_optional_fields_present: List[str]
    schema_extras_rejected: List[str]
    error_summary: Optional[str]
