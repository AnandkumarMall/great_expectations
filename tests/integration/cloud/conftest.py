import warnings

import pytest


@pytest.fixture(autouse=True)
def _suppress_cloud_deprecation_warnings():
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="CloudDataContext is deprecated",
            category=DeprecationWarning,
        )
        warnings.filterwarnings(
            "ignore",
            message="The GX Cloud branch of get_context",
            category=DeprecationWarning,
        )
        yield
