"""Tests for the direct-construction DeprecationWarning on ``CloudDataContext``.

Verifies that constructing a ``CloudDataContext`` directly emits exactly one
``DeprecationWarning`` stating that GX Cloud has been shut down and naming the
2.0 removal target, that the warning surfaces the caller's frame, and that it is
purely additive -- the
constructor's signature, return shape, observable behavior, and cloud-specific
public-API surface are all unchanged when the warning is suppressed.

The autouse ``_suppress_cloud_deprecation_warnings`` fixture in this directory's
``conftest.py`` ignores the cloud-deprecation warnings by message prefix.
``pytest.warns(...)`` overrides that suppression for its assertion block, which
is exactly what these tests rely on to observe the warning.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import pytest

from great_expectations.data_context import CloudDataContext

if TYPE_CHECKING:
    import pathlib

    from great_expectations.data_context.types.base import (
        DataContextConfig,
        GXCloudConfig,
    )

# module level markers
pytestmark = pytest.mark.cloud

# The substring that uniquely identifies the cloud-deprecation warning.
_CLOUD_DEPRECATION_SUBSTR = "GX Cloud has been shut down"


def _construct_cloud_data_context(
    *,
    tmp_path: pathlib.Path,
    project_config: DataContextConfig,
    cloud_config: GXCloudConfig,
) -> CloudDataContext:
    """Directly construct a ``CloudDataContext`` using the standard test mocks.

    ``cloud_api_fake`` (mocked HTTP backend) plus an explicit ``project_config`` and
    explicit ``cloud_*`` arguments make direct construction succeed without real
    network access. The caller is responsible for warning capture/suppression.

    Note: ``CloudDataContext.__init__`` does NOT accept ``cloud_mode`` (that is a
    ``get_context()`` parameter); we pass ``cloud_base_url`` / ``cloud_access_token`` /
    ``cloud_organization_id`` / ``cloud_workspace_id`` instead.
    """
    project_path = tmp_path / "empty_data_context"
    project_path.mkdir()
    return CloudDataContext(
        project_config=project_config,
        context_root_dir=str(project_path),
        cloud_base_url=cloud_config.base_url,
        cloud_access_token=cloud_config.access_token,
        cloud_organization_id=cloud_config.organization_id,
        cloud_workspace_id=cloud_config.workspace_id,
    )


def test_direct_construction_emits_exactly_one_deprecation_warning(
    cloud_api_fake,
    tmp_path: pathlib.Path,
    empty_ge_cloud_data_context_config: DataContextConfig,
    ge_cloud_config: GXCloudConfig,
):
    """Direct construction emits exactly one DeprecationWarning whose message
    states that GX Cloud has been shut down and names 2.0 as the removal target.

    ``pytest.warns(DeprecationWarning)`` overrides the autouse suppression so the
    warning is observable. The count assertion filters to the cloud-deprecation
    warning specifically so unrelated DeprecationWarnings cannot mask a regression.
    """
    with pytest.warns(DeprecationWarning) as record:
        context = _construct_cloud_data_context(
            tmp_path=tmp_path,
            project_config=empty_ge_cloud_data_context_config,
            cloud_config=ge_cloud_config,
        )

    assert isinstance(context, CloudDataContext)

    cloud_warnings = [w for w in record if _CLOUD_DEPRECATION_SUBSTR in str(w.message)]
    # Exactly one per instance: the dedupe guard must not let it double-fire, and the
    # warning must actually be emitted.
    assert len(cloud_warnings) == 1, (
        "Expected exactly one CloudDataContext deprecation warning, got "
        f"{[str(w.message) for w in cloud_warnings]}"
    )

    message = str(cloud_warnings[0].message)
    # States that GX Cloud no longer functions and names the 2.0 removal target.
    assert _CLOUD_DEPRECATION_SUBSTR in message
    assert "2.0" in message
    assert cloud_warnings[0].category is DeprecationWarning


def test_warning_surfaces_caller_frame_not_internal_frame(
    cloud_api_fake,
    tmp_path: pathlib.Path,
    empty_ge_cloud_data_context_config: DataContextConfig,
    ge_cloud_config: GXCloudConfig,
):
    """The warning is emitted with a stacklevel that surfaces the caller's
    frame (this test module), not an internal great_expectations frame.

    With ``stacklevel=2`` the recorded warning's ``filename`` must be THIS test
    module and must NOT be ``cloud_data_context.py``. This fails if the stacklevel
    is dropped/wrong (warning would then point at the gx-internal frame).
    """
    with pytest.warns(DeprecationWarning) as record:
        _construct_cloud_data_context(
            tmp_path=tmp_path,
            project_config=empty_ge_cloud_data_context_config,
            cloud_config=ge_cloud_config,
        )

    cloud_warnings = [w for w in record if _CLOUD_DEPRECATION_SUBSTR in str(w.message)]
    assert len(cloud_warnings) == 1
    filename = cloud_warnings[0].filename

    # Caller frame == this test module (the CloudDataContext(...) invocation site).
    assert filename.endswith("test_cloud_deprecation.py"), (
        f"Warning should surface the caller frame, got filename={filename!r}"
    )
    # Must NOT point at the internal definition site.
    assert "cloud_data_context.py" not in filename, (
        f"Warning surfaced an internal great_expectations frame: {filename!r}"
    )


def test_suppressed_warning_yields_identical_observable_behavior(
    cloud_api_fake,
    tmp_path: pathlib.Path,
    empty_ge_cloud_data_context_config: DataContextConfig,
    ge_cloud_config: GXCloudConfig,
):
    """The warning is additive only. With the warning suppressed, construction
    yields the same observable result (same type, same key attributes,
    ``mode == "cloud"``) as without the warning -- the warning changes nothing but
    emission.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=_CLOUD_DEPRECATION_SUBSTR,
            category=DeprecationWarning,
        )
        context = _construct_cloud_data_context(
            tmp_path=tmp_path,
            project_config=empty_ge_cloud_data_context_config,
            cloud_config=ge_cloud_config,
        )

    # Observable behavior unchanged by the (suppressed) warning.
    assert isinstance(context, CloudDataContext)
    assert context.mode == "cloud"
    # Cloud config is wired through exactly as the inputs specified (return shape intact).
    assert context.ge_cloud_config.base_url == ge_cloud_config.base_url
    assert context.ge_cloud_config.organization_id == ge_cloud_config.organization_id
    assert context.ge_cloud_config.access_token == ge_cloud_config.access_token


def test_cloud_public_api_surface_intact(
    cloud_api_fake,
    tmp_path: pathlib.Path,
    empty_ge_cloud_data_context_config: DataContextConfig,
    ge_cloud_config: GXCloudConfig,
):
    """The cloud-specific ``@public_api`` surface is unchanged by the deprecation.
    ``cloud_user_info``, ``ge_cloud_config``, ``mode`` and ``prepare_checkpoint_run``
    must all still be present, and ``mode`` returns ``"cloud"``.
    """
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=_CLOUD_DEPRECATION_SUBSTR,
            category=DeprecationWarning,
        )
        context = _construct_cloud_data_context(
            tmp_path=tmp_path,
            project_config=empty_ge_cloud_data_context_config,
            cloud_config=ge_cloud_config,
        )

    for attr in ("cloud_user_info", "ge_cloud_config", "mode", "prepare_checkpoint_run"):
        assert hasattr(context, attr), f"Cloud public-API surface lost attribute: {attr}"

    # cloud_user_info / prepare_checkpoint_run remain callable methods.
    assert callable(context.cloud_user_info)
    assert callable(context.prepare_checkpoint_run)
    # mode is the cloud literal (cheap to check, no network).
    assert context.mode == "cloud"
