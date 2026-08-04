import datetime
import logging
import re
import sys

from great_expectations.compatibility.google import NotFound, python_bigquery
from great_expectations.compatibility.pydantic import BaseSettings

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler(sys.stdout))


class BigQueryConnectionConfig(BaseSettings):
    """Environment variables for BigQuery access.
    These are injected in via CI, but when running locally, you may use your own credentials.
    GOOGLE_APPLICATION_CREDENTIALS must be kept secret. It is not read directly by this script;
    Application Default Credentials picks it up automatically.
    """

    GE_TEST_GCP_PROJECT: str
    GOOGLE_APPLICATION_CREDENTIALS: str


# Schema patterns for different test types
SCHEMA_PATTERN_TEST = "^gx_ci_test_[a-f0-9]{10}$"  # General SQL testing framework
SCHEMA_PATTERN_PY_VERSION = "^py3[0-9]{1,2}_i[a-f0-9]{32}$"  # Python version-specific test schemas
SCHEMA_FORMAT = re.compile(f"{SCHEMA_PATTERN_TEST}|{SCHEMA_PATTERN_PY_VERSION}")

# Only sweep datasets older than this. Kept small enough that a dataset from a run that is
# still in progress is never deleted out from under it.
DEFAULT_MAX_AGE = datetime.timedelta(hours=1)


def find_stale_dataset_ids(
    client: python_bigquery.Client, max_age: datetime.timedelta = DEFAULT_MAX_AGE
) -> list[str]:
    """Find test dataset ids old enough to be cleaned up.

    Uses the `datasets.list` API rather than querying `INFORMATION_SCHEMA.SCHEMATA`:
    - `datasets.list` only returns datasets the caller can already see, so a credential scoped
      to just the CI dataset namespace can run this sweep. A project-level
      `INFORMATION_SCHEMA.SCHEMATA` query requires permission to read dataset metadata across
      the whole project, which is more access than a CI credential should need.
    - `INFORMATION_SCHEMA` is region-scoped: it only sees datasets in the region the query runs
      in, so a dataset created in a different location would be silently invisible to it.
      `datasets.list` is not region-scoped.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    stale_ids = []
    for dataset_item in client.list_datasets():
        dataset_id = dataset_item.dataset_id
        if not SCHEMA_FORMAT.match(dataset_id):
            continue

        try:
            # `list_datasets` results don't include creation time; `get_dataset` does.
            dataset = client.get_dataset(dataset_item.reference)
        except NotFound:
            # Dataset was deleted between listing and inspecting it.
            continue

        created = dataset.created
        if created is not None and now - created > max_age:
            stale_ids.append(dataset_id)

    return stale_ids


def cleanup_big_query(
    config: BigQueryConnectionConfig, max_age: datetime.timedelta = DEFAULT_MAX_AGE
) -> None:
    client = python_bigquery.Client(project=config.GE_TEST_GCP_PROJECT)

    stale_ids = find_stale_dataset_ids(client, max_age=max_age)
    if not stale_ids:
        logger.info("No BigQuery datasets to clean up!")
        return

    cleaned_up = 0
    for dataset_id in stale_ids:
        try:
            client.delete_dataset(dataset_id, delete_contents=True)
            cleaned_up += 1
        except NotFound:
            # Dataset was deleted (e.g. by a concurrent sweep) between listing and deleting it.
            logger.info(f"Dataset {dataset_id} was already deleted")

    logger.info(f"Cleaned up {cleaned_up} BigQuery dataset(s)")


if __name__ == "__main__":
    config = BigQueryConnectionConfig()  # type: ignore[call-arg]  # pydantic populates from env vars
    cleanup_big_query(config)
