from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING, Generator

import pandas as pd
import pytest

import great_expectations as gx
import great_expectations.expectations as gxe
from great_expectations.data_context.data_context.cloud_data_context import CloudDataContext
from tests.conftest import random_name
from tests.integration.test_utils.request_tracking import TrackedSession

if TYPE_CHECKING:
    from pytest_mock import MockerFixture

NAME = random_name()
COL_NAME = "col_name"
DATAFRAME = pd.DataFrame({COL_NAME: ["a", "b", "c"]})


@pytest.fixture
def tracked_session(mocker: MockerFixture) -> TrackedSession:
    tracked_session = TrackedSession()
    mocker.patch("requests.Session", return_value=tracked_session)
    return tracked_session


@pytest.fixture
def cloud_context_with_single_validation_definition(
    tracked_session: TrackedSession,
) -> Generator[CloudDataContext, None, None]:
    context = gx.get_context(mode="cloud")
    bd = (
        context.data_sources.add_pandas(name=NAME)
        .add_dataframe_asset(name=NAME)
        .add_batch_definition_whole_dataframe(name=NAME)
    )

    suite = context.suites.add(
        gx.ExpectationSuite(
            name=NAME,
            expectations=[
                gxe.ExpectColumnDistinctValuesToBeInSet(
                    column=COL_NAME,
                    value_set=["a", "b", "c"],
                )
            ],
        )
    )

    vd = context.validation_definitions.add(
        gx.ValidationDefinition(
            name=NAME,
            data=bd,
            suite=suite,
        )
    )

    context.checkpoints.add(gx.Checkpoint(name=NAME, validation_definitions=[vd]))

    # Make sure we clear session tracking before the test
    tracked_session.clear()
    assert tracked_session.get_request_counts() == Counter()

    yield context

    context.checkpoints.delete(name=NAME)
    context.validation_definitions.delete(name=NAME)
    context.data_sources.delete(name=NAME)
    context.suites.delete(name=NAME)


@pytest.mark.xfail(
    reason="This test is currently failing magnificently and should be fixed by GX-793.",
    strict=True,
)
@pytest.mark.cloud
def test_request_counts(
    cloud_context_with_single_validation_definition: CloudDataContext,
    tracked_session: TrackedSession,
) -> None:
    """Test to ensure we only make one request per endpoint during a validation flow"""

    cp = cloud_context_with_single_validation_definition.checkpoints.get(NAME)
    cp.run(batch_parameters={"dataframe": DATAFRAME})

    counts = tracked_session.get_request_counts()
    assert len(counts) > 0
    assert set(counts.values()) == {1}
