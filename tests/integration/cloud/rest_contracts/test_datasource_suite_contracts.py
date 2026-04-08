"""Client-driven Pact contract tests for datasource and expectation suite CRUD.

Each test:
1. Registers the GET /data-context-configuration interaction via
   ``setup_data_context_config_interaction()``.
2. Registers resource-specific Pact interaction(s).
3. Constructs a ``CloudDataContext`` and exercises the Python client API
   inside the ``with pact_test.serve() as srv:`` block.
4. Asserts the client correctly parses the response.

URL patterns (V2 with workspace):
  /api/v2/organizations/{org_id}/workspaces/{ws_id}/datasources
  /api/v2/organizations/{org_id}/workspaces/{ws_id}/expectation-suites
"""

from __future__ import annotations

from typing import Final
from unittest.mock import patch

import pytest
from pact import Pact, match

import great_expectations as gx
from great_expectations import __version__ as ge_version
from great_expectations.core.http import create_session
from tests.integration.cloud.rest_contracts.conftest import (
    EXISTING_ORGANIZATION_ID,
    EXISTING_WORKSPACE_ID,
    PACT_DUMMY_ACCESS_TOKEN,
    setup_data_context_config_interaction,
)

# ---------------------------------------------------------------------------
# Shared constants -- datasources
# ---------------------------------------------------------------------------

DATASOURCE_NAME: Final[str] = "my_contract_test_datasource"
EXISTING_DATASOURCE_ID: Final[str] = "bbbbcccc-0001-4abc-8def-aabbccddeeff"

DATASOURCES_PATH: Final[str] = (
    f"/api/v2/organizations/{EXISTING_ORGANIZATION_ID}"
    f"/workspaces/{EXISTING_WORKSPACE_ID}/datasources"
)
DATASOURCE_BY_ID_PATH: Final[str] = f"{DATASOURCES_PATH}/{EXISTING_DATASOURCE_ID}"

# ---------------------------------------------------------------------------
# Shared constants -- expectation suites
# ---------------------------------------------------------------------------

SUITE_NAME: Final[str] = "my_contract_test_suite"
EXISTING_SUITE_ID: Final[str] = "bbbbcccc-0002-4abc-8def-aabbccddeeff"

SUITES_PATH: Final[str] = (
    f"/api/v2/organizations/{EXISTING_ORGANIZATION_ID}"
    f"/workspaces/{EXISTING_WORKSPACE_ID}/expectation-suites"
)
SUITE_BY_ID_PATH: Final[str] = f"{SUITES_PATH}/{EXISTING_SUITE_ID}"

# ---------------------------------------------------------------------------
# Shared response payloads
# ---------------------------------------------------------------------------

# Minimal datasource payload returned by the cloud API.
_DATASOURCE_RESPONSE: Final[dict] = {
    "id": EXISTING_DATASOURCE_ID,
    "type": "pandas",
    "name": DATASOURCE_NAME,
    "assets": [],
}

# Minimal expectation suite payload returned by the cloud API.
# ``meta.great_expectations_version`` MUST match the installed GX version
# exactly -- the freshness check compares the local suite against the
# deserialized cloud response and a mismatch causes
# ``ExpectationSuiteNotFreshError``.
_SUITE_RESPONSE: Final[dict] = {
    "id": EXISTING_SUITE_ID,
    "name": SUITE_NAME,
    "expectations": [],
    "meta": {"great_expectations_version": match.like(ge_version)},
    "notes": None,
}


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _session_headers() -> dict:
    """Return request headers matching what the Python client sends."""
    session = create_session(access_token=PACT_DUMMY_ACCESS_TOKEN)
    return {k: str(v) for k, v in session.headers.items()}


# ---------------------------------------------------------------------------
# Datasource tests
# ---------------------------------------------------------------------------


@pytest.mark.cloud
def test_get_datasource_by_name(pact_test: Pact) -> None:
    """context.data_sources.get(name=...) retrieves a datasource from the store.

    ``CacheableDatasourceDict.__getitem__`` calls
    ``DatasourceStore.retrieve_by_name()`` which issues ``has_key`` + ``get``
    -- two identical GET requests served by a single Pact interaction.

    Full interaction sequence:
      1. GET /data-context-configuration           (context init)
      2. GET /datasources?name=...                 (serves has_key + get)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="get-datasource",
    )

    # 2. GET /datasources?name=...
    (
        pact_test.upon_receiving("a request to get a datasource by name (client-driven)")
        .given("a datasource with this name exists")
        .with_request("GET", DATASOURCES_PATH)
        .with_headers(headers)
        .with_query_parameters({"name": DATASOURCE_NAME})
        .will_respond_with(200)
        .with_body(
            {"data": match.each_like(match.like(_DATASOURCE_RESPONSE), min=1)},
            content_type="application/json",
        )
    )

    with pact_test.serve() as srv:
        ctx = gx.get_context(
            mode="cloud",
            cloud_base_url=str(srv.url),
            cloud_organization_id=EXISTING_ORGANIZATION_ID,
            cloud_workspace_id=EXISTING_WORKSPACE_ID,
            cloud_access_token=PACT_DUMMY_ACCESS_TOKEN,
        )
        result = ctx.data_sources.get(name=DATASOURCE_NAME)

    assert result is not None
    assert result.name == DATASOURCE_NAME


@pytest.mark.cloud
def test_delete_datasource(pact_test: Pact) -> None:
    """context.data_sources.delete(name=...) fetches the datasource then DELETEs it.

    ``_delete_fluent_datasource`` calls ``data_sources.all().get(name)`` to
    resolve the datasource (and its cloud id) via the store, then issues
    ``DatasourceStore.delete()`` -> ``remove_key()`` -> HTTP DELETE.

    ``_save_project_config()`` is a no-op in CloudDataContext.

    Full interaction sequence:
      1. GET /data-context-configuration           (context init)
      2. GET /datasources?name=...                 (resolve datasource for deletion)
      3. DELETE /datasources/{id}                  (delete by id)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="delete-datasource",
    )

    # 2. GET /datasources?name=...
    (
        pact_test.upon_receiving(
            "fetch datasource by name to resolve id for delete (client-driven)"
        )
        .given("a datasource with this name exists for deletion")
        .with_request("GET", DATASOURCES_PATH)
        .with_headers(headers)
        .with_query_parameters({"name": DATASOURCE_NAME})
        .will_respond_with(200)
        .with_body(
            {"data": match.each_like(match.like(_DATASOURCE_RESPONSE), min=1)},
            content_type="application/json",
        )
    )

    # 3. DELETE /datasources/{id}
    (
        pact_test.upon_receiving("a request to delete a datasource by id (client-driven)")
        .given("a datasource with this name exists for deletion")
        .with_request("DELETE", DATASOURCE_BY_ID_PATH)
        .with_headers(headers)
        .will_respond_with(200)
    )

    with pact_test.serve() as srv:
        ctx = gx.get_context(
            mode="cloud",
            cloud_base_url=str(srv.url),
            cloud_organization_id=EXISTING_ORGANIZATION_ID,
            cloud_workspace_id=EXISTING_WORKSPACE_ID,
            cloud_access_token=PACT_DUMMY_ACCESS_TOKEN,
        )

        # _delete_fluent_datasource ends with
        # ``del self.config.fluent_datasources[name]``.
        # Seed the config dict so the cleanup line doesn't KeyError.
        from great_expectations.datasource.fluent.pandas_datasource import (
            PandasDatasource,
        )

        placeholder = PandasDatasource(name=DATASOURCE_NAME)
        ctx.config.fluent_datasources[DATASOURCE_NAME] = placeholder

        ctx.data_sources.delete(name=DATASOURCE_NAME)


# ---------------------------------------------------------------------------
# Expectation suite tests
# ---------------------------------------------------------------------------


@pytest.mark.cloud
def test_get_expectation_suite_by_name(pact_test: Pact) -> None:
    """context.suites.get(name=...) issues has_key then GET.

    ``SuiteFactory.get`` calls ``store.has_key(key)`` then ``store.get(key)``
    -- both issue identical GET requests served by a single Pact interaction.

    Full interaction sequence:
      1. GET /data-context-configuration           (context init)
      2. GET /expectation-suites?name=...          (serves has_key + get)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="get-suite",
    )

    # 2. GET /expectation-suites?name=...
    (
        pact_test.upon_receiving("a request to get an expectation suite by name (client-driven)")
        .given("an expectation suite with this name exists")
        .with_request("GET", SUITES_PATH)
        .with_headers(headers)
        .with_query_parameters({"name": SUITE_NAME})
        .will_respond_with(200)
        .with_body(
            {"data": match.each_like(match.like(_SUITE_RESPONSE), min=1)},
            content_type="application/json",
        )
    )

    with pact_test.serve() as srv:
        ctx = gx.get_context(
            mode="cloud",
            cloud_base_url=str(srv.url),
            cloud_organization_id=EXISTING_ORGANIZATION_ID,
            cloud_workspace_id=EXISTING_WORKSPACE_ID,
            cloud_access_token=PACT_DUMMY_ACCESS_TOKEN,
        )
        result = ctx.suites.get(name=SUITE_NAME)

    assert result is not None
    assert result.name == SUITE_NAME


@pytest.mark.cloud
def test_add_expectation_suite(pact_test: Pact) -> None:
    """context.suites.add(suite) issues has_key probe then POST.

    ``SuiteFactory.add`` checks ``store.has_key()`` (empty list -> suite
    absent), then calls ``store.add()`` which POSTs the suite.  After the
    POST, ``add()`` calls ``self.get(name)`` to re-fetch the persisted suite,
    which would issue the same GET ?name=... but expects a *non-empty*
    response.  The Pact v3 mock server cannot serve different responses for
    the same request criteria, so we patch the re-fetch.

    Full interaction sequence:
      1. GET /data-context-configuration           (context init)
      2. GET /expectation-suites?name=...          (has_key probe -- empty list)
      3. POST /expectation-suites                  (create the suite)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="add-suite",
    )

    # 2. GET /expectation-suites?name=... -- has_key probe (empty -> suite absent)
    (
        pact_test.upon_receiving("has_key probe for suite before add (client-driven)")
        .given("no expectation suite with this name exists")
        .with_request("GET", SUITES_PATH)
        .with_headers(headers)
        .with_query_parameters({"name": SUITE_NAME})
        .will_respond_with(200)
        .with_body({"data": []}, content_type="application/json")
    )

    # 3. POST /expectation-suites
    request_body: match.AbstractMatcher = match.like(
        {
            "data": match.like(
                {
                    "name": match.like(SUITE_NAME),
                    "id": None,
                    "expectations": match.like([]),
                    "meta": match.like({"great_expectations_version": match.like("1.0.0")}),
                    "notes": None,
                }
            )
        }
    )
    response_body = {"data": match.like(_SUITE_RESPONSE)}
    (
        pact_test.upon_receiving("a request to create an expectation suite (client-driven)")
        .given("no expectation suite with this name exists")
        .with_request("POST", SUITES_PATH)
        .with_headers(headers)
        .with_body(request_body, content_type="application/vnd.api+json")
        .will_respond_with(201)
        .with_body(response_body, content_type="application/json")
    )

    # Build a mock suite for the patched SuiteFactory.get() re-fetch.
    from great_expectations.core.expectation_suite import ExpectationSuite

    refetched_suite = ExpectationSuite(name=SUITE_NAME)
    refetched_suite.id = EXISTING_SUITE_ID

    with pact_test.serve() as srv:
        ctx = gx.get_context(
            mode="cloud",
            cloud_base_url=str(srv.url),
            cloud_organization_id=EXISTING_ORGANIZATION_ID,
            cloud_workspace_id=EXISTING_WORKSPACE_ID,
            cloud_access_token=PACT_DUMMY_ACCESS_TOKEN,
        )

        with patch.object(
            type(ctx.suites),
            "get",
            return_value=refetched_suite,
        ):
            result = ctx.suites.add(ExpectationSuite(name=SUITE_NAME))

    assert result is not None
    assert result.name == SUITE_NAME


@pytest.mark.cloud
def test_delete_expectation_suite(pact_test: Pact) -> None:
    """context.suites.delete(name=...) fetches the suite then DELETE /{id}.

    ``SuiteFactory.delete`` calls ``self.get(name)`` to resolve the cloud id
    (which issues has_key + get -- two identical GETs served by one
    interaction), then issues ``store.remove_key(key)`` -> HTTP DELETE.

    Full interaction sequence:
      1. GET /data-context-configuration           (context init)
      2. GET /expectation-suites?name=...          (serves has_key + get)
      3. DELETE /expectation-suites/{id}           (delete by id)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="delete-suite",
    )

    # 2. GET /expectation-suites?name=... -- serves has_key + get
    (
        pact_test.upon_receiving("fetch suite by name to resolve id for delete (client-driven)")
        .given("an expectation suite with this name exists for deletion")
        .with_request("GET", SUITES_PATH)
        .with_headers(headers)
        .with_query_parameters({"name": SUITE_NAME})
        .will_respond_with(200)
        .with_body(
            {"data": match.each_like(match.like(_SUITE_RESPONSE), min=1)},
            content_type="application/json",
        )
    )

    # 3. DELETE /expectation-suites/{id}
    (
        pact_test.upon_receiving("a request to delete an expectation suite by id (client-driven)")
        .given("an expectation suite with this name exists for deletion")
        .with_request("DELETE", SUITE_BY_ID_PATH)
        .with_headers(headers)
        .will_respond_with(200)
    )

    with pact_test.serve() as srv:
        ctx = gx.get_context(
            mode="cloud",
            cloud_base_url=str(srv.url),
            cloud_organization_id=EXISTING_ORGANIZATION_ID,
            cloud_workspace_id=EXISTING_WORKSPACE_ID,
            cloud_access_token=PACT_DUMMY_ACCESS_TOKEN,
        )
        ctx.suites.delete(name=SUITE_NAME)


@pytest.mark.cloud
def test_get_all_expectation_suites(pact_test: Pact) -> None:
    """context.suites.all() retrieves all suites from the store.

    ``SuiteFactory.all`` calls ``store.get_all()`` which issues a single GET
    to the collection endpoint without query parameters.

    Full interaction sequence:
      1. GET /data-context-configuration           (context init)
      2. GET /expectation-suites                   (get all)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="get-all-suites",
    )

    # 2. GET /expectation-suites (no query params)
    (
        pact_test.upon_receiving("a request to get all expectation suites (client-driven)")
        .given("expectation suites exist")
        .with_request("GET", SUITES_PATH)
        .with_headers(headers)
        .will_respond_with(200)
        .with_body(
            {"data": match.each_like(match.like(_SUITE_RESPONSE), min=1)},
            content_type="application/json",
        )
    )

    with pact_test.serve() as srv:
        ctx = gx.get_context(
            mode="cloud",
            cloud_base_url=str(srv.url),
            cloud_organization_id=EXISTING_ORGANIZATION_ID,
            cloud_workspace_id=EXISTING_WORKSPACE_ID,
            cloud_access_token=PACT_DUMMY_ACCESS_TOKEN,
        )
        result = list(ctx.suites.all())

    assert len(result) >= 1
    assert result[0].name == SUITE_NAME
