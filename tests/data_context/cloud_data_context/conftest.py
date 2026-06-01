import warnings

import pytest


@pytest.fixture(autouse=True)
def _suppress_cloud_deprecation_warnings():
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="GX Cloud has been shut down",
            category=DeprecationWarning,
        )
        yield
