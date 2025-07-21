from __future__ import annotations

import logging
import warnings
from typing import Callable, Iterator, Sequence

import numpy as np
import pandas as pd

from great_expectations.compatibility import sqlalchemy
from great_expectations.compatibility.not_imported import is_version_less_than

# Additional imports for SQLite-specific implementation
from great_expectations.compatibility.sqlalchemy import (
    Column,
    MetaData,
    Table,
    insert,
    sqltypes,
)
from great_expectations.execution_engine.sqlalchemy_dialect import GXSqlDialect

logger = logging.getLogger(__name__)

# Constants
_BATCH_INSERT_THRESHOLD = 100
_TABLE_ALREADY_EXISTS_MSG = "Table '{name}' already exists."


def _raise_table_exists_error(name: str) -> None:
    """Raise ValueError for table already exists."""
    msg = _TABLE_ALREADY_EXISTS_MSG.format(name=name)
    raise ValueError(msg)


def _is_sqlite_connection(con) -> bool:  # noqa: C901, PLR0911
    """Detect if the connection is to a SQLite database."""
    try:
        # SQLAlchemy 2.0+ engine detection
        if hasattr(con, "url") and hasattr(con.url, "drivername"):
            return con.url.drivername.lower().startswith("sqlite")

        # SQLAlchemy 2.0+ connection detection
        if hasattr(con, "dialect") and hasattr(con.dialect, "name"):
            return con.dialect.name.lower() == "sqlite"

        # Check if it's a connection with an engine
        if hasattr(con, "engine"):
            if hasattr(con.engine, "url") and hasattr(con.engine.url, "drivername"):
                return con.engine.url.drivername.lower().startswith("sqlite")
            elif hasattr(con.engine, "dialect") and hasattr(con.engine.dialect, "name"):
                return con.engine.dialect.name.lower() == "sqlite"

        # Fallback: try to get dialect
        if hasattr(con, "get_dialect") and callable(con.get_dialect):
            dialect = con.get_dialect()
            if hasattr(dialect, "name"):
                return dialect.name.lower() == "sqlite"

        return False
    except (AttributeError, Exception):
        # If we can't determine, fall back to non-SQLite logic
        return False


def _get_sqlite_inferrable_types_lookup():
    """Get type mapping for SQLite columns."""
    return {
        str: sqltypes.VARCHAR,
        int: sqltypes.INTEGER,
        float: sqltypes.REAL,  # SQLite uses REAL for floating point
        bool: sqltypes.BOOLEAN,
        pd.Timestamp: sqltypes.DATETIME,
        object: sqltypes.TEXT,  # Default for mixed types
    }


def _infer_sqlite_column_types(  # noqa: C901, PLR0912
    df: pd.DataFrame, explicit_dtype: dict | None = None
) -> dict[str, sqltypes.TypeEngine]:
    """Infer SQLite column types from DataFrame."""
    type_lookup = _get_sqlite_inferrable_types_lookup()
    column_types = {}

    for col_name in df.columns:
        # Use explicit dtype if provided
        if explicit_dtype and col_name in explicit_dtype:
            if isinstance(explicit_dtype[col_name], str):
                # Handle string type names
                if explicit_dtype[col_name].upper() == "VARCHAR":
                    column_types[col_name] = sqltypes.VARCHAR()
                elif explicit_dtype[col_name].upper() == "INTEGER":
                    column_types[col_name] = sqltypes.INTEGER()
                elif explicit_dtype[col_name].upper() == "REAL":
                    column_types[col_name] = sqltypes.REAL()
                else:
                    column_types[col_name] = sqltypes.TEXT()
            else:
                # Assume it's already a SQLAlchemy type
                column_types[col_name] = explicit_dtype[col_name]
        else:
            # Infer from DataFrame
            col_series = df[col_name]
            if col_series.dtype == "object":
                # Try to infer based on first non-null value
                first_non_null = (
                    col_series.dropna().iloc[0] if not col_series.dropna().empty else None
                )
                if first_non_null is not None:
                    python_type = type(first_non_null)
                    column_types[col_name] = type_lookup.get(python_type, sqltypes.TEXT())
                else:
                    column_types[col_name] = sqltypes.TEXT()
            elif "int" in str(col_series.dtype):
                column_types[col_name] = sqltypes.INTEGER()
            elif "float" in str(col_series.dtype):
                column_types[col_name] = sqltypes.REAL()
            elif "bool" in str(col_series.dtype):
                column_types[col_name] = sqltypes.BOOLEAN()
            elif "datetime" in str(col_series.dtype):
                column_types[col_name] = sqltypes.DATETIME()
            else:
                column_types[col_name] = sqltypes.TEXT()

    return column_types


def _create_sqlite_table(  # noqa: PLR0913
    name: str,
    df: pd.DataFrame,
    metadata: MetaData,
    schema: str | None = None,
    dtype: dict | None = None,
    index: bool = True,
) -> Table:
    """Create SQLite table with appropriate columns."""
    columns = []

    # Handle index column if needed
    if index:
        if df.index.name:
            index_name = df.index.name
        else:
            index_name = "index"
        columns.append(Column(index_name, sqltypes.INTEGER))

    # Infer column types
    column_types = _infer_sqlite_column_types(df, dtype)

    # Add data columns
    for col_name, col_type in column_types.items():
        columns.append(Column(col_name, col_type))

    return Table(name, metadata, *columns, schema=schema)


def _add_dataframe_to_sqlite_db(  # noqa: PLR0913
    df: pd.DataFrame,
    name: str,
    con,
    schema: str | None = None,
    if_exists: str = "fail",
    index: bool = True,
    dtype: dict | None = None,
    method: str | Callable | None = None,
) -> None:
    """SQLite-specific implementation using SqlAlchemy core patterns."""
    metadata = MetaData()

    # Create table
    table = _create_sqlite_table(name, df, metadata, schema, dtype, index)

    # Handle SQLAlchemy 2.0 transaction management
    # Use a simplified approach that works with both engines and connections
    try:
        if hasattr(con, "begin"):
            # This could be an engine or connection - try the engine pattern first
            try:
                with con.begin() as trans_con:
                    _execute_sqlite_operations(
                        df, table, trans_con, if_exists, index, method, name, schema
                    )
                return
            except Exception:
                # If engine pattern fails, try as a connection
                pass

        # Try as a direct connection without explicit transaction management
        # SQLAlchemy 2.0 connections often handle autocommit appropriately
        _execute_sqlite_operations(df, table, con, if_exists, index, method, name, schema)

    except Exception:
        # If all else fails, try to get a connection from the engine
        if hasattr(con, "connect"):
            with con.connect() as conn:
                _execute_sqlite_operations(df, table, conn, if_exists, index, method, name, schema)
        else:
            # Final fallback - direct execution
            _execute_sqlite_operations(df, table, con, if_exists, index, method, name, schema)


def _execute_sqlite_operations(df, table, con, if_exists, index, method, name, schema):  # noqa: C901, PLR0912, PLR0913
    """Execute the actual SQLite operations within a transaction."""
    # Get the appropriate engine for operations
    engine = con if hasattr(con, "dialect") else getattr(con, "engine", con)

    if if_exists == "replace":
        # Drop table if it exists - SQLAlchemy 2.0 compatible
        try:
            table.drop(engine, checkfirst=True)
        except Exception:
            pass  # Table doesn't exist, which is fine
    elif if_exists == "fail":
        # Check if table exists - SQLAlchemy 2.0 compatible
        try:
            from great_expectations.compatibility.sqlalchemy import inspect

            inspector = inspect(engine)
            if inspector.has_table(name, schema=schema):
                _raise_table_exists_error(name)
        except Exception:
            # Fallback - if we can't inspect, let create_all handle it
            pass
    # For "append", we don't need to do anything special

    # Create table if it doesn't exist or we're replacing - SQLAlchemy 2.0 compatible
    if if_exists in ["replace", "fail"]:
        table.metadata.create_all(engine)

    # Prepare data for insertion
    df_copy = df.replace(np.nan, None)  # Replace NaN with None for SQLite

    # Handle datetime columns for Python 3.12+ and SQLAlchemy compatibility
    for col_name in df_copy.columns:
        if pd.api.types.is_datetime64_any_dtype(df_copy[col_name]):
            # Convert pandas Timestamp to Python datetime for SQLAlchemy compatibility
            # Use apply to avoid future deprecation warning
            df_copy[col_name] = df_copy[col_name].apply(
                lambda x: x.to_pydatetime() if pd.notna(x) else None
            )

    if index:
        # Include index in the data
        df_with_index = df_copy.reset_index()
        values = list(df_with_index.to_dict("index").values())
    else:
        values = list(df_copy.to_dict("index").values())

    # Insert data - SQLAlchemy 2.0 compatible
    if values:  # Only insert if we have data
        if method == "multi":
            # Bulk insert - SQLAlchemy 2.0 handles autocommit
            con.execute(insert(table), values)
        # Insert row by row (default behavior)
        # For better performance with many rows, we'll still batch them
        elif len(values) > _BATCH_INSERT_THRESHOLD:
            # Batch insert for better performance
            con.execute(insert(table), values)
        else:
            # Row by row for smaller datasets
            for value_dict in values:
                con.execute(insert(table).values(**value_dict))

        # Ensure changes are committed in SQLAlchemy 2.0
        try:
            if hasattr(con, "commit") and not hasattr(con, "in_transaction"):
                con.commit()
        except Exception:
            # If commit fails or isn't needed, that's fine
            pass


def read_sql_table_as_df(  # noqa: PLR0913 # FIXME CoP
    table_name,
    con,
    dialect: str,
    schema=None,
    index_col: str | Sequence[str] | None = None,
    coerce_float: bool = True,
    parse_dates: list[str] | dict[str, str] | None = None,
    columns: list[str] | None = None,
    chunksize: int | None = None,
) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """Wrapper for `read_sql_table()` method in Pandas. Created as part of the effort to allow GX to be compatible
    with SqlAlchemy 2, and is used to suppress warnings that arise from implicit auto-commits.

    Args:
        table_name (str): name of SQL Table.
        con (sqlalchemy engine or connection): sqlalchemy.engine or sqlite3.Connection
        schema (str | None): Specify the schema (if database flavor supports this). If None, use
            default schema. Defaults to None.
        index_col (str | Sequence[str] | None): Column(s) to set as index(MultiIndex).
        coerce_float (bool): If True, method to convert values of non-string, non-numeric objects (like
            decimal.Decimal) to floating point. Can result in loss of Precision.
        parse_dates (List or Dict): list or dict, default None
            - List of column names to parse as dates.
            - Dict of ``{column_name: format string}`` where format string is
                strftime compatible in case of parsing string times or is one of
                (D, s, ns, ms, us) in case of parsing integer timestamps.
            - Dict of ``{column_name: arg dict}``, where the arg dict corresponds
                to the keyword arguments of :func:`pandas.to_datetime`
                Especially useful with databases without native Datetime support,
                such as SQLite.
        columns: List of column names to select from SQL table.
        chunksize: If specified, returns an iterator where `chunksize` is the number of
            rows to include in each chunk.
        dialect: we need to handle `sqlite` differently, so dialect is now optionally passed in.
    """  # noqa: E501 # FIXME CoP
    if is_version_less_than(pd.__version__, "2.0.0"):
        with warnings.catch_warnings():
            warnings.filterwarnings(action="ignore", category=DeprecationWarning)
            return _read_sql_table_as_df(
                table_name=table_name,
                con=con,
                dialect=dialect,
                schema=schema,
                index_col=index_col,
                coerce_float=coerce_float,
                parse_dates=parse_dates,
                columns=columns,
                chunksize=chunksize,
            )
    else:
        return _read_sql_table_as_df(
            table_name=table_name,
            con=con,
            dialect=dialect,
            schema=schema,
            index_col=index_col,
            coerce_float=coerce_float,
            parse_dates=parse_dates,
            columns=columns,
            chunksize=chunksize,
        )


def _read_sql_table_as_df(  # noqa: PLR0913 # FIXME CoP
    table_name,
    con,
    dialect: str,
    schema=None,
    index_col: str | Sequence[str] | None = None,
    coerce_float: bool = True,
    parse_dates: list[str] | dict[str, str] | None = None,
    columns: list[str] | None = None,
    chunksize: int | None = None,
) -> pd.DataFrame | Iterator[pd.DataFrame]:
    """Wrapper for `read_sql_table()` method in Pandas. Created as part of the effort to allow GX to be compatible
    with SqlAlchemy 2, and is used to suppress warnings that arise from implicit auto-commits.

    Args:
        table_name (str): name of SQL Table.
        con (sqlalchemy engine or connection): sqlalchemy.engine or sqlite3.Connection
        schema (str | None): Specify the schema (if database flavor supports this). If None, use
            default schema. Defaults to None.
        index_col (str | Sequence[str] | None): Column(s) to set as index(MultiIndex).
        coerce_float (bool): If True, method to convert values of non-string, non-numeric objects (like
            decimal.Decimal) to floating point. Can result in loss of Precision.
        parse_dates (List or Dict): list or dict, default None
            - List of column names to parse as dates.
            - Dict of ``{column_name: format string}`` where format string is
                strftime compatible in case of parsing string times or is one of
                (D, s, ns, ms, us) in case of parsing integer timestamps.
            - Dict of ``{column_name: arg dict}``, where the arg dict corresponds
                to the keyword arguments of :func:`pandas.to_datetime`
                Especially useful with databases without native Datetime support,
                such as SQLite.
        columns: List of column names to select from SQL table.
        chunksize: If specified, returns an iterator where `chunksize` is the number of
            rows to include in each chunk.
        dialect: we need to handle `sqlite` differently, so dialect is now optionally passed in.
    """  # noqa: E501 # FIXME CoP
    if dialect == GXSqlDialect.TRINO:
        return pd.read_sql_table(
            table_name=table_name,
            con=con,
            schema=schema,
            index_col=index_col,  # type: ignore[arg-type] # FIXME CoP
            coerce_float=coerce_float,
            parse_dates=parse_dates,
            columns=columns,
            chunksize=chunksize,  # type: ignore[arg-type] # FIXME CoP
        )
    else:
        sql_str: str
        if schema:
            sql_str = f"""SELECT * FROM {schema}.{table_name}"""
        else:
            sql_str = f"""SELECT * FROM {table_name}"""
        return pd.read_sql_query(
            sql=sql_str,
            con=con,
            index_col=index_col,  # type: ignore[arg-type] # FIXME CoP
            coerce_float=coerce_float,
            parse_dates=parse_dates,
            chunksize=chunksize,  # type: ignore[arg-type] # FIXME CoP
        )


def add_dataframe_to_db(  # noqa: PLR0913 # FIXME CoP
    df: pd.DataFrame,
    name: str,
    con,
    schema=None,
    if_exists: str = "fail",
    index: bool = True,
    index_label: str | None = None,
    chunksize: int | None = None,
    dtype: dict | None = None,
    method: str | Callable | None = None,
) -> None:
    """Write records stored in a DataFrame to a SQL database.

    Wrapper for `to_sql()` method in Pandas. Created as part of the effort to allow GX to be compatible
    with SqlAlchemy 2, and is used to suppress warnings that arise from implicit auto-commits.

    The need for this function will eventually go away once we migrate to Pandas 1.4.0.

    Args:
        df (pd.DataFrame): DataFrame to load into the SQL Table.
        name (str): name of SQL Table.
        con (sqlalchemy engine or connection): sqlalchemy.engine or sqlite3.Connection
        schema (str | None): Specify the schema (if database flavor supports this). If None, use
            default schema. Defaults to None.
        if_exists (str | None): Can be either 'fail', 'replace', or 'append'. Defaults to `fail`.
            * fail: Raise a ValueError.
            * replace: Drop the table before inserting new values.
            * append: Insert new values to the existing table.
        index (bool): Write DataFrame index as a column. Uses `index_label` as the column
            name in the table. Defaults to True.
        index_label (str | None):
            Column label for index column(s). If None is given (default) and
            `index` is True, then the index names are used.
        chunksize (int | None):
            Specify the number of rows in each batch to be written at a time.
            By default, all rows will be written at once.
        dtype (dict | int | float | bool | None):
            Specifying the datatype for columns. If a dictionary is used, the
            keys should be the column names and the values should be the
            SQLAlchemy types or strings for the sqlite3 legacy mode. If a
            scalar is provided, it will be applied to all columns.
        method (str | Callable | None):
            Controls the SQL insertion clause used:
                * None : Uses standard SQL ``INSERT`` clause (one per row).
                * 'multi': Pass multiple values in a single ``INSERT`` clause.
                * callable with signature ``(pd_table, conn, keys, data_iter)``.
    """  # noqa: E501 # FIXME CoP

    # Check if this is a SQLite connection and use SQLite-specific implementation
    # This is especially important for SQLAlchemy 2.0+ where pandas.to_sql has compatibility issues
    # Skip unsupported parameters for SQLite implementation (index_label, chunksize)
    # Also prioritize for certain if_exists values where pandas.to_sql commonly fails
    is_sqlite = _is_sqlite_connection(con)
    use_sqlite_impl = (
        is_sqlite
        and index_label is None
        and chunksize is None
        and (
            if_exists != "fail"
            or (
                sqlalchemy.sqlalchemy
                and not is_version_less_than(sqlalchemy.sqlalchemy.__version__, "2.0.0")
            )
        )
    )

    if use_sqlite_impl:
        try:
            _add_dataframe_to_sqlite_db(
                df=df,
                name=name,
                con=con,
                schema=schema,
                if_exists=if_exists,
                index=index,
                dtype=dtype,
                method=method,
            )
            return
        except Exception as e:
            # If SQLite-specific implementation fails, fall back to pandas.to_sql
            # Note: This fallback may fail with SQLAlchemy 2.0+ and pandas 2.2+
            logger.warning(
                f"SQLite-specific implementation failed: {e}. Falling back to pandas.to_sql."
            )

    # Fall back to original pandas.to_sql implementation for non-SQLite or unsupported parameters
    if sqlalchemy.sqlalchemy and is_version_less_than(sqlalchemy.sqlalchemy.__version__, "2.0.0"):
        with warnings.catch_warnings():
            # Note that RemovedIn20Warning is the warning class that we see from sqlalchemy
            # but using the base class here since sqlalchemy is an optional dependency and this
            # warning type only exists in sqlalchemy < 2.0.
            warnings.filterwarnings(action="ignore", category=DeprecationWarning)
            df.to_sql(
                name=name,
                con=con,
                schema=schema,
                if_exists=if_exists,  # type: ignore[arg-type] # FIXME CoP
                index=index,
                index_label=index_label,
                chunksize=chunksize,
                dtype=dtype,
                method=method,  # type: ignore[arg-type] # FIXME CoP
            )
    else:
        df.to_sql(
            name=name,
            con=con,
            schema=schema,
            if_exists=if_exists,  # type: ignore[arg-type] # FIXME CoP
            index=index,
            index_label=index_label,
            chunksize=chunksize,
            dtype=dtype,
            method=method,  # type: ignore[arg-type] # FIXME CoP
        )
