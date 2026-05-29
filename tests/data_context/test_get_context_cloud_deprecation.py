"""Tests for the cloud-branch DeprecationWarning emitted by ``get_context()``.

Covers Req 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 1.5, 6.2 (deprecate-gx-cloud spec) and the
design's Testing Strategy -> Unit/behavior items 2 (factory cloud-branch warning),
3 (env-var-only path), 4 (no spurious warning), 5 (exactly-one-per-construction on
the factory path) and 6 (guard reset on error).

This module lives OUTSIDE the ``tests/data_context/cloud_data_context/`` directory,
so the autouse ``_suppress_cloud_deprecation_warnings`` conftest fixture does NOT
apply here. Each test therefore manages warnings explicitly (``pytest.warns`` /
``warnings.catch_warnings(record=True)``). There is deliberately NO module-level
``filterwarnings`` ignore -- a module-wide ignore would weaken the
"no spurious warning" assertions.
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING

import pytest

import great_expectations as gx
from great_expectations.data_context import (
    CloudDataContext,
    EphemeralDataContext,
)
from great_expectations.data_context.cloud_constants import GXCloudEnvironmentVariable

if TYPE_CHECKING:
    import pathlib

    from great_expectations.data_context.types.base import (
        DataContextConfig,
        GXCloudConfig,
    )

# Substrings that uniquely identify the two cloud-deprecation warnings this spec adds.
_FACTORY_DEPRECATION_SUBSTR = "The GX Cloud branch of get_context"
_INIT_DEPRECATION_SUBSTR = "CloudDataContext is deprecated"

# Realistic dummy cloud kwargs (no real backend) used to trigger the kwargs branch.
_CLOUD_KWARGS = {
    "cloud_base_url": "https://app.greatexpectations.io/",
    "cloud_access_token": "i_am_a_token",
    "cloud_organization_id": "bd20fead-2c31-4392-bcd1-f1e87ad5a79c",
}


@pytest.fixture
def _no_cloud_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure no ``GX_CLOUD_*`` env config leaks in from the host environment.

    The cloud-resolution predicate consults ``GX_CLOUD_*`` env vars; clearing them
    makes the explicit kwargs / ``mode`` / ``cloud_mode`` the ONLY trigger, so the
    trigger-form tests are not contaminated by ambient cloud config.
    """
    for var in GXCloudEnvironmentVariable:
        monkeypatch.delenv(var, raising=False)


def _cloud_warnings(record) -> list:
    return [w for w in record if _FACTORY_DEPRECATION_SUBSTR in str(w.message)]


def _init_warnings(record) -> list:
    return [w for w in record if _INIT_DEPRECATION_SUBSTR in str(w.message)]


# ---------------------------------------------------------------------------
# Item 2: factory cloud-branch warning on the three trigger forms
# (Req 2.1, 2.3, 2.4). Each form emits the warning BEFORE the cloud context is
# built; with no real cloud config the call raises AFTER the warning, so we
# capture the warning and assert it fired even though construction failed.
# ---------------------------------------------------------------------------


@pytest.mark.cloud
@pytest.mark.parametrize(
    "call_kwargs",
    [
        pytest.param({"mode": "cloud"}, id="mode-cloud"),
        pytest.param({"cloud_mode": True}, id="cloud-mode-true"),
        pytest.param(dict(_CLOUD_KWARGS), id="cloud-star-kwargs"),
    ],
)
def test_cloud_trigger_forms_emit_branch_deprecation_warning(
    _no_cloud_env: None,
    call_kwargs: dict,
):
    """Req 2.1/2.3: each of the three cloud trigger forms emits a
    ``DeprecationWarning`` identifying the GX Cloud *branch* of ``get_context()``
    (not ``get_context`` itself) and naming v2.0 as the removal target.

    The warning fires BEFORE delegation, so even though the call ultimately
    raises (no real cloud backend), the warning is recorded. This test fails if
    the gate is removed (no warning) or the message stops naming the branch/v2.0.
    """
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        with pytest.raises(Exception):  # noqa: B017 # post-warning failure type varies (config vs connection); the warning, not the raise, is under test
            gx.get_context(**call_kwargs)

    cloud_warnings = _cloud_warnings(record)
    assert len(cloud_warnings) >= 1, (
        "Expected the cloud-branch DeprecationWarning to fire before the cloud "
        f"build failed; got {[str(w.message) for w in record]}"
    )
    message = str(cloud_warnings[0].message)
    assert cloud_warnings[0].category is DeprecationWarning
    # Req 2.3: identifies the branch, names v2.0, and explicitly disclaims that
    # get_context() itself is deprecated.
    assert _FACTORY_DEPRECATION_SUBSTR in message
    assert "v2.0" in message
    assert "get_context() itself is not deprecated" in message


@pytest.mark.cloud
def test_branch_warning_surfaces_caller_frame_not_internal_frame(
    _no_cloud_env: None,
):
    """Req 2.4 (stacklevel=2): the recorded warning's ``filename`` is THIS test
    module (the caller's ``get_context(...)`` site), not ``context_factory.py``.

    Fails if the stacklevel is dropped/wrong -- the warning would then point at
    the gx-internal emission frame.
    """
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        with pytest.raises(Exception):  # noqa: B017 # post-warning failure type varies; the warning, not the raise, is under test
            gx.get_context(mode="cloud")

    cloud_warnings = _cloud_warnings(record)
    assert len(cloud_warnings) >= 1
    filename = cloud_warnings[0].filename
    assert filename.endswith("test_get_context_cloud_deprecation.py"), (
        f"Warning should surface the caller frame, got filename={filename!r}"
    )
    assert "context_factory.py" not in filename, (
        f"Warning surfaced an internal great_expectations frame: {filename!r}"
    )


# ---------------------------------------------------------------------------
# Item 3: env-var-only path still warns (Req 2.5). Proves the gate reuses the
# same resolution predicate (is_cloud_config_available) as delegation -- a
# kwarg-only gate would miss this path.
# ---------------------------------------------------------------------------


@pytest.mark.cloud
def test_env_var_only_path_emits_branch_deprecation_warning(
    monkeypatch: pytest.MonkeyPatch,
):
    """Req 2.5: with ``GX_CLOUD_*`` env vars set and NO cloud kwargs,
    ``get_context()`` still resolves to cloud and emits the branch warning.

    This fails if the gate were re-derived from kwargs alone instead of reusing
    the factory's ``is_cloud_config_available`` predicate.
    """
    monkeypatch.setenv(GXCloudEnvironmentVariable.ACCESS_TOKEN, "i_am_a_token")
    monkeypatch.setenv(
        GXCloudEnvironmentVariable.ORGANIZATION_ID,
        "bd20fead-2c31-4392-bcd1-f1e87ad5a79c",
    )
    monkeypatch.setenv(GXCloudEnvironmentVariable.BASE_URL, "https://app.greatexpectations.io/")

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        with pytest.raises(Exception):  # noqa: B017 # post-warning failure type varies; the warning, not the raise, is under test
            gx.get_context()  # no kwargs -- env config is the sole trigger

    cloud_warnings = _cloud_warnings(record)
    assert len(cloud_warnings) >= 1, (
        "Env-var-only cloud config should still trigger the branch warning; got "
        f"{[str(w.message) for w in record]}"
    )
    assert "v2.0" in str(cloud_warnings[0].message)


# ---------------------------------------------------------------------------
# Item 4: no spurious warning (Req 2.2).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_ephemeral_mode_emits_no_cloud_warning_even_with_env_set(
    monkeypatch: pytest.MonkeyPatch,
):
    """Req 2.2: ``mode="ephemeral"`` resolves non-cloud even WITH ``GX_CLOUD_*``
    env vars set, so NO cloud deprecation warning fires (mode short-circuits
    before the env-based predicate). Returns an ``EphemeralDataContext``.

    Fails if the gate fired on the env config regardless of the explicit
    non-cloud mode.
    """
    monkeypatch.setenv(GXCloudEnvironmentVariable.ACCESS_TOKEN, "i_am_a_token")
    monkeypatch.setenv(
        GXCloudEnvironmentVariable.ORGANIZATION_ID,
        "bd20fead-2c31-4392-bcd1-f1e87ad5a79c",
    )
    monkeypatch.setenv(GXCloudEnvironmentVariable.BASE_URL, "https://app.greatexpectations.io/")

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        context = gx.get_context(mode="ephemeral")

    assert isinstance(context, EphemeralDataContext)
    assert _cloud_warnings(record) == [], (
        "mode='ephemeral' must not emit a cloud deprecation warning even with "
        f"GX_CLOUD_* env vars set; got {[str(w.message) for w in record]}"
    )
    # Belt and suspenders: the __init__ warning must not fire either.
    assert _init_warnings(record) == []


@pytest.mark.unit
def test_plain_get_context_with_no_cloud_config_emits_no_cloud_warning(
    _no_cloud_env: None,
    tmp_path: pathlib.Path,
):
    """Req 2.2: a plain ``get_context()`` with no cloud kwargs and no cloud env
    config emits no cloud deprecation warning and returns a non-cloud context.
    """
    project_path = tmp_path / "empty_data_context"
    project_path.mkdir()

    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        context = gx.get_context(context_root_dir=str(project_path))

    assert not isinstance(context, CloudDataContext)
    assert _cloud_warnings(record) == [], (
        "Non-cloud get_context() must not emit a cloud deprecation warning; got "
        f"{[str(w.message) for w in record]}"
    )
    assert _init_warnings(record) == []


# ---------------------------------------------------------------------------
# Item 5: exactly-one-per-construction on the FACTORY cloud path (Req 1.5).
# Uses the mocked cloud backend so construction SUCCEEDS, then asserts exactly
# one branch warning and ZERO __init__ warnings (the guard suppressed the
# latter).
# ---------------------------------------------------------------------------


@pytest.mark.cloud
def test_factory_cloud_path_emits_exactly_one_cloud_warning(
    cloud_api_fake,
    empty_ge_cloud_data_context_config: DataContextConfig,
    ge_cloud_config: GXCloudConfig,
):
    """Req 1.5: a single factory-path cloud construction emits EXACTLY ONE
    cloud-deprecation warning -- the ``get_context()`` branch warning -- and the
    ``CloudDataContext.__init__`` warning does NOT also fire (the dedupe guard
    suppressed it).

    Fails if the guard were removed (then BOTH warnings would fire) or if the
    branch warning were removed (then zero -- or only the __init__ one -- fire).
    """
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        context = gx.get_context(
            project_config=empty_ge_cloud_data_context_config,
            cloud_base_url=ge_cloud_config.base_url,
            cloud_access_token=ge_cloud_config.access_token,
            cloud_organization_id=ge_cloud_config.organization_id,
            cloud_workspace_id=ge_cloud_config.workspace_id,
            cloud_mode=True,
        )

    assert isinstance(context, CloudDataContext)

    branch_warnings = _cloud_warnings(record)
    init_warnings = _init_warnings(record)
    # Exactly one branch warning fired...
    assert len(branch_warnings) == 1, (
        "Expected exactly one get_context() cloud-branch deprecation warning, got "
        f"{[str(w.message) for w in branch_warnings]}"
    )
    # ...and the CloudDataContext.__init__ warning was suppressed by the guard.
    assert init_warnings == [], (
        "The CloudDataContext.__init__ warning must not fire on the factory path "
        f"(guard should have suppressed it); got {[str(w.message) for w in init_warnings]}"
    )


# ---------------------------------------------------------------------------
# Item 6: guard reset on error (Req 1.5 / Error Handling). After a cloud-branch
# get_context() that RAISES inside delegation, the try/finally must have reset
# the guard so a subsequent DIRECT CloudDataContext(...) still warns.
# ---------------------------------------------------------------------------


@pytest.mark.cloud
def test_guard_is_reset_after_factory_cloud_path_raises(
    _no_cloud_env: None,
    cloud_api_fake,
    tmp_path: pathlib.Path,
    empty_ge_cloud_data_context_config: DataContextConfig,
    ge_cloud_config: GXCloudConfig,
):
    """Req 1.5 / Error Handling: a ``get_context(mode="cloud")`` that raises
    inside the cloud branch must reset the dedupe guard (set in a try/finally),
    so a subsequent DIRECT ``CloudDataContext(...)`` STILL emits its own
    ``CloudDataContext is deprecated`` warning.

    Fails if the guard reset were dropped from the ``finally`` -- the leaked
    ``True`` guard would silently suppress the direct-construction warning.
    """
    # First: a factory cloud call that raises (no real cloud config -> the guard
    # is set True before delegation and must be reset in the finally when the
    # build fails).
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        with pytest.raises(Exception):  # noqa: B017 # post-warning failure type varies; the warning, not the raise, is under test
            gx.get_context(mode="cloud")

    # Now a direct construction (mocked backend so it succeeds). If the guard had
    # leaked True, this warning would be suppressed.
    project_path = tmp_path / "empty_data_context"
    project_path.mkdir()
    with warnings.catch_warnings(record=True) as record:
        warnings.simplefilter("always")
        context = CloudDataContext(
            project_config=empty_ge_cloud_data_context_config,
            context_root_dir=str(project_path),
            cloud_base_url=ge_cloud_config.base_url,
            cloud_access_token=ge_cloud_config.access_token,
            cloud_organization_id=ge_cloud_config.organization_id,
            cloud_workspace_id=ge_cloud_config.workspace_id,
        )

    assert isinstance(context, CloudDataContext)
    init_warnings = _init_warnings(record)
    assert len(init_warnings) == 1, (
        "Direct construction after a raised factory cloud call must still warn "
        "(guard must have been reset in the finally); got "
        f"{[str(w.message) for w in init_warnings]}"
    )
    assert "v2.0" in str(init_warnings[0].message)
