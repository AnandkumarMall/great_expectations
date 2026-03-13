import datetime
import logging
from typing import Any, Dict, List

import pandas as pd
import pytest
from packaging.version import Version
from packaging.version import parse as parse_version

from great_expectations.compatibility import pyspark
from great_expectations.datasource.fluent import SparkDatasource

logger = logging.getLogger(__name__)

try:
    from great_expectations.execution_engine import SparkDFExecutionEngine
    from great_expectations.self_check.util import build_spark_engine
except ImportError:
    SparkDFExecutionEngine = None
    build_spark_engine = None
    # TODO: review logging more detail here
    logger.debug(
        "Unable to load pyspark; install optional spark dependency if you will be working with Spark dataframes."  # noqa: E501 # FIXME CoP
    )

# module level markers
pytestmark = pytest.mark.spark


def test_current_pyspark_version_installed(spark_session):
    pyspark_version: Version = parse_version(pyspark.pyspark.__version__)
    # Spark versions less than 3.0 are not supported.
    assert pyspark_version.major >= 3, "Spark versions less than 3.0 are not supported."


def test_spark_config_datasource(spark_session_v012):
    name = "great_expectations-ds-config"
    spark_config = {
        "spark.app.name": name,
        "spark.sql.catalogImplementation": "hive",
        "spark.executor.memory": "768m",
    }
    spark_datasource = SparkDatasource(
        name="my spark datasource",
        spark_config=spark_config,
    )
    # a warning is raised because passing unmodifiable config options results in restarting spark context  # noqa: E501 # FIXME CoP
    with pytest.warns(RuntimeWarning):
        execution_engine: SparkDFExecutionEngine = spark_datasource.get_execution_engine()
    spark_session: pyspark.SparkSession = execution_engine.spark
    sc_stopped: bool = spark_session.sparkContext._jsc.sc().isStopped()
    assert not sc_stopped

    # Test that our values were set
    conf: List[tuple] = spark_session.sparkContext.getConf().getAll()
    assert ("spark.app.name", name) in conf
    assert ("spark.sql.catalogImplementation", "hive") in conf
    assert ("spark.executor.memory", "768m") in conf
    spark_session.sparkContext.stop()


def test_spark_config_execution_engine_block_config(spark_session):
    new_spark_config: Dict[str, Any] = {
        "spark.app.name": "great_expectations-ee-config",
        "spark.sql.catalogImplementation": "hive",
        "spark.executor.memory": "512m",
    }
    with pytest.warns(RuntimeWarning):
        execution_engine = SparkDFExecutionEngine(spark_config=new_spark_config)
    new_spark_session: pyspark.SparkSession = execution_engine.spark

    # noinspection PyProtectedMember
    sc_stopped: bool = new_spark_session.sparkContext._jsc.sc().isStopped()

    assert not sc_stopped

    current_spark_config: List[tuple] = execution_engine.spark.sparkContext.getConf().getAll()
    assert ("spark.sql.catalogImplementation", "hive") in current_spark_config
    assert (
        "spark.app.name",
        "great_expectations-ee-config",
    ) in current_spark_config
    assert ("spark.executor.memory", "512m") in current_spark_config
    # spark context config values cannot be changed by the builder no matter what
    assert current_spark_config != new_spark_config
    new_spark_session.sparkContext.stop()


def test_spark_timestamp_roundtrip_via_arrow(spark_session):
    """Verify that timestamp data survives the pandas -> Spark -> pandas round-trip.

    This exercises both Arrow-optimized code paths:
      1. build_spark_engine passes the pandas DataFrame directly to
         createDataFrame(pandas_df, schema), which uses Arrow serialization.
      2. engine.head() calls toPandas(), which uses Arrow deserialization.

    Without pyarrow installed and spark.sql.execution.arrow.pyspark.enabled=true,
    this round-trip may silently degrade timestamp types to object dtype or fail
    outright on pandas 3.x due to Pandas4Warning in PySpark's Arrow serializer.
    """
    timestamps = [
        datetime.datetime(2021, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(2021, 6, 15, 12, 30, 0, tzinfo=datetime.timezone.utc),
        datetime.datetime(2021, 12, 31, 23, 59, 59, tzinfo=datetime.timezone.utc),
    ]

    engine = build_spark_engine(
        spark=spark_session,
        df=pd.DataFrame(
            {
                "id": [1, 2, 3],
                "event_time": timestamps,
            }
        ),
        schema=pyspark.types.StructType(
            [
                pyspark.types.StructField("id", pyspark.types.IntegerType(), True),
                pyspark.types.StructField("event_time", pyspark.types.TimestampType(), True),
            ]
        ),
        batch_id="arrow_timestamp_test",
    )

    result = engine.head(n=3)

    assert pd.api.types.is_datetime64_any_dtype(result["event_time"]), (
        f"Expected datetime64 dtype for timestamp column, got {result['event_time'].dtype}. "
        "Ensure pyarrow is installed and spark.sql.execution.arrow.pyspark.enabled is true."
    )
    for original, roundtripped in zip(timestamps, result["event_time"], strict=True):
        assert roundtripped == pd.Timestamp(original)
