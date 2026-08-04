import datetime

import pytest
from pytest_mock import MockerFixture
from scripts.cleanup.cleanup_big_query import find_stale_dataset_ids

from great_expectations.compatibility.google import NotFound

pytestmark = pytest.mark.unit


def _dataset_item(mocker: MockerFixture, dataset_id: str):
    item = mocker.Mock()
    item.dataset_id = dataset_id
    item.reference = dataset_id
    return item


def _dataset(mocker: MockerFixture, created: datetime.datetime | None):
    dataset = mocker.Mock()
    dataset.created = created
    return dataset


def _ago(**kwargs) -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(**kwargs)


def test_matches_gx_ci_test_pattern_and_is_old_enough(mocker: MockerFixture):
    dataset_id = "gx_ci_test_" + "a" * 10
    client = mocker.Mock()
    client.list_datasets.return_value = [_dataset_item(mocker, dataset_id)]
    client.get_dataset.return_value = _dataset(mocker, _ago(hours=2))

    result = find_stale_dataset_ids(client, max_age=datetime.timedelta(hours=1))

    assert result == [dataset_id]


def test_matches_py_version_pattern(mocker: MockerFixture):
    dataset_id = "py312_i" + "a" * 32
    client = mocker.Mock()
    client.list_datasets.return_value = [_dataset_item(mocker, dataset_id)]
    client.get_dataset.return_value = _dataset(mocker, _ago(hours=2))

    result = find_stale_dataset_ids(client, max_age=datetime.timedelta(hours=1))

    assert result == [dataset_id]


def test_ignores_dataset_that_does_not_match_any_pattern(mocker: MockerFixture):
    client = mocker.Mock()
    client.list_datasets.return_value = [_dataset_item(mocker, "great_expectations_ci")]

    result = find_stale_dataset_ids(client, max_age=datetime.timedelta(hours=1))

    assert result == []
    # A dataset that doesn't match the naming pattern should never even be inspected,
    # since inspecting it is an extra API call this credential may not even have access to.
    client.get_dataset.assert_not_called()


def test_excludes_dataset_younger_than_max_age(mocker: MockerFixture):
    dataset_id = "gx_ci_test_" + "b" * 10
    client = mocker.Mock()
    client.list_datasets.return_value = [_dataset_item(mocker, dataset_id)]
    client.get_dataset.return_value = _dataset(mocker, _ago(minutes=1))

    result = find_stale_dataset_ids(client, max_age=datetime.timedelta(hours=1))

    assert result == []


def test_zero_max_age_includes_freshly_created_dataset(mocker: MockerFixture):
    dataset_id = "gx_ci_test_" + "c" * 10
    client = mocker.Mock()
    client.list_datasets.return_value = [_dataset_item(mocker, dataset_id)]
    client.get_dataset.return_value = _dataset(mocker, _ago(seconds=1))

    result = find_stale_dataset_ids(client, max_age=datetime.timedelta(seconds=0))

    assert result == [dataset_id]


def test_dataset_deleted_between_list_and_get_is_skipped(mocker: MockerFixture):
    client = mocker.Mock()
    client.list_datasets.return_value = [_dataset_item(mocker, "gx_ci_test_" + "d" * 10)]
    client.get_dataset.side_effect = NotFound("gone")

    result = find_stale_dataset_ids(client, max_age=datetime.timedelta(hours=1))

    assert result == []


def test_dataset_with_no_creation_time_is_skipped(mocker: MockerFixture):
    client = mocker.Mock()
    client.list_datasets.return_value = [_dataset_item(mocker, "gx_ci_test_" + "e" * 10)]
    client.get_dataset.return_value = _dataset(mocker, None)

    result = find_stale_dataset_ids(client, max_age=datetime.timedelta(hours=1))

    assert result == []
