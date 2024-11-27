from __future__ import annotations

import inspect
import logging
from types import ModuleType
from typing import Any

from great_expectations.compatibility.bigquery import BIGQUERY_GEO_SUPPORT
from great_expectations.execution_engine.sqlalchemy_dialect import GXSqlDialect
from packaging import version

logger = logging.getLogger(__name__)


def get_clickhouse_sqlalchemy_potential_type(type_module, type_) -> Any:
    ch_type = type_
    if type(ch_type) is str:
        if type_.lower() in ("decimal", "decimaltype()"):
            ch_type = type_module.types.Decimal
        elif type_.lower() in ("fixedstring"):
            ch_type = type_module.types.String
        else:
            ch_type = type_module.ClickHouseDialect()._get_column_type("", ch_type)

    if hasattr(ch_type, "nested_type"):
        ch_type = type(ch_type.nested_type)
    if not inspect.isclass(ch_type):
        ch_type = type(ch_type)
    return ch_type


def get_pyathena_potential_type(type_module, type_) -> str:
    if version.parse(type_module.pyathena.__version__) >= version.parse("2.5.0"):
        # introduction of new column type mapping in 2.5
        potential_type = type_module.AthenaDialect()._get_column_type(type_)
    else:
        if type_ == "string":
            type_ = "varchar"
        # < 2.5 column type mapping
        potential_type = type_module._TYPE_MAPPINGS.get(type_)

    return potential_type


def get_trino_potential_type(type_module: ModuleType, type_: str) -> object:
    """
    Leverage on Trino Package to return sqlalchemy sql type
    """
    # noinspection PyUnresolvedReferences
    potential_type = type_module.parse_sqltype(type_)
    return potential_type


def get_potential_sqlalchemy_types(execution_engine, expected_type):
    # Avoid circular import
    from great_expectations.execution_engine.sqlalchemy_execution_engine import (
        _get_dialect_type_module,
    )

    # Our goal is to be as explicit as possible. We will match the dialect
    # if that is possible. If there is no dialect available, we *will*
    # match against a top-level SqlAlchemy type.
    #
    # This is intended to be a conservative approach.
    #
    # In particular, we *exclude* types that would be valid under an ORM
    # such as "float" for postgresql with this approach
    types: list[Any] = []
    type_module = _get_dialect_type_module(dialect=execution_engine.dialect_module)
    try:
        # bigquery geography requires installing an extra package
        if (
            expected_type.lower() == "geography"
            and execution_engine.engine.dialect.name.lower() == GXSqlDialect.BIGQUERY
            and not BIGQUERY_GEO_SUPPORT
        ):
            logger.warning(
                "BigQuery GEOGRAPHY type is not supported by default. "
                + "To install support, please run:"
                + "  $ pip install 'sqlalchemy-bigquery[geography]'"
            )
        elif type_module.__name__ == "pyathena.sqlalchemy_athena":
            potential_type = get_pyathena_potential_type(type_module, expected_type)
            # In the case of the PyAthena dialect we need to verify that
            # the type returned is indeed a type and not an instance.
            if not inspect.isclass(potential_type):
                real_type = type(potential_type)
            else:
                real_type = potential_type
            types.append(real_type)
        elif type_module.__name__ == "trino.sqlalchemy.datatype":
            potential_type = get_trino_potential_type(type_module, expected_type)
            types.append(type(potential_type))
        elif type_module.__name__ == "clickhouse_sqlalchemy.drivers.base":
            potential_type = get_clickhouse_sqlalchemy_potential_type(
                type_module, expected_type
            )
            types.append(potential_type)
        else:
            potential_type = getattr(type_module, expected_type)
            types.append(potential_type)
    except AttributeError:
        logger.debug(f"Unrecognized type: {expected_type}")
    if len(types) == 0:
        logger.warning(
            "No recognized sqlalchemy types in type_list for current dialect."
        )
    return types
