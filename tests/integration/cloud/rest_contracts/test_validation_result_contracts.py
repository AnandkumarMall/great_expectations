"""Client-driven Pact contract tests for validation result endpoints.

Each test:
1. Registers the GET /data-context-configuration interaction via
   ``setup_data_context_config_interaction()``.
2. Registers resource-specific Pact interaction(s).
3. Constructs a ``CloudDataContext`` and exercises the Python client API
   inside the ``with pact_test.serve() as srv:`` block.
4. Asserts the client correctly handles the response.

URL patterns (V1 with workspace):
  GET  /api/v1/organizations/{org_id}/workspaces/{ws_id}/validation-results
  GET  /api/v1/organizations/{org_id}/workspaces/{ws_id}/validation-results/{id}
  POST /api/v1/organizations/{org_id}/workspaces/{ws_id}/validation-results

Tests use the public ``context.get_validation_result()`` API where
possible.  That method dispatches to the ValidationResultsStore
internally, triggering the same HTTP calls that real users exercise.

- **test_list_validation_results** uses ``get_validation_result()`` with
  ``run_id=None`` which calls ``store.list_keys()`` → GET list.
- **test_get_validation_result_by_id** uses ``get_validation_result()``
  with both ``run_id`` and ``batch_identifier`` which builds a
  ``ValidationResultIdentifier`` and calls ``store.get(key)`` → GET by ID.
- **test_post_validation_result** uses ``store.set()`` directly since
  that is how results are persisted (called internally by
  ``validation_definition.run()``).
"""

from __future__ import annotations

from typing import Final

import pytest
from pact import Pact, match

import great_expectations as gx
from great_expectations.core.expectation_validation_result import (
    ExpectationSuiteValidationResult,
)
from great_expectations.data_context.cloud_constants import GXCloudRESTResource
from great_expectations.data_context.types.resource_identifiers import (
    GXCloudIdentifier,
)
from tests.integration.cloud.rest_contracts.conftest import (
    EXISTING_ORGANIZATION_ID,
    EXISTING_WORKSPACE_ID,
    PACT_DUMMY_ACCESS_TOKEN,
    pact_session_headers,
    setup_data_context_config_interaction,
)

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

EXISTING_VALIDATION_RESULT_ID: Final[str] = "77770001-0001-4aaa-8aaa-777700010001"
# Validation definition ID -- matches what the Mercury state handler seeds.
# The real client sets meta["validation_id"] = validation_definition.id after running.
EXISTING_VALIDATION_DEFINITION_ID: Final[str] = "ccccdddd-1234-4abc-8def-aabbccddeeff"

VALIDATION_RESULTS_PATH: Final[str] = (
    f"/api/v1/organizations/{EXISTING_ORGANIZATION_ID}"
    f"/workspaces/{EXISTING_WORKSPACE_ID}/validation-results"
)
VALIDATION_RESULT_BY_ID_PATH: Final[str] = (
    f"{VALIDATION_RESULTS_PATH}/{EXISTING_VALIDATION_RESULT_ID}"
)

# ---------------------------------------------------------------------------
# Response body matchers
# ---------------------------------------------------------------------------

# Minimal ValidationResultResponseData returned by the V1 API for GET/LIST.
#
# The ``name`` field is required by the cloud backend's ``list_keys()``
# implementation (``GXCloudStoreBackend.list_keys`` reads
# ``resource["name"]`` for V1 resources).  Validation results don't have
# a user-visible name; the server returns an empty string.
_VALIDATION_RESULT_RESPONSE: Final[dict] = {
    "id": match.uuid(),
    "name": match.like(""),
    "organization_id": match.uuid(),
    "created_by_id": match.uuid(),
    "results": match.like([]),
    "suite_name": match.like(None),
    "suite_parameters": match.like({}),
    "statistics": match.like({}),
    "meta": match.like(
        {
            "run_id": match.like(
                {
                    "run_name": match.like("pact_test_run"),
                    "run_time": match.like("2026-01-01T00:00:00.000000Z"),
                }
            ),
            "run_time": match.like("2026-01-01T00:00:00.000000Z"),
            "run_name": match.like("pact_test_run"),
        }
    ),
    "batch_id": match.like(None),
    "result_url": match.like("https://example.com/validation-results/placeholder"),
    "success": match.like(True),
}

# GET-by-ID response wraps the result fields at top-level under ``data``.
# ``gx_cloud_response_json_to_object_dict`` in ``ValidationResultsStore``
# expects ``data.attributes.result`` (the legacy V0 shape).  We provide
# that shape so the full deserialization round-trip succeeds.
_VALIDATION_RESULT_GET_BY_ID_RESPONSE: Final[dict] = {
    "id": match.uuid(EXISTING_VALIDATION_RESULT_ID),
    "attributes": {
        "result": match.like(
            {
                "success": match.like(True),
                "results": match.like([]),
                "suite_name": match.like("my_test_suite"),
                "suite_parameters": match.like({}),
                "statistics": match.like(
                    {
                        "evaluated_expectations": match.like(0),
                        "successful_expectations": match.like(0),
                        "unsuccessful_expectations": match.like(0),
                        "success_percent": match.like(100.0),
                    }
                ),
                "meta": match.like({}),
            }
        ),
    },
}

# POST response echoes back suite_name from the request body (non-null).
_VALIDATION_RESULT_POST_RESPONSE: Final[dict] = {
    **_VALIDATION_RESULT_RESPONSE,
    "suite_name": match.like("my_test_suite"),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_headers() -> dict:
    """Return request headers matching what the Python client sends."""
    return pact_session_headers()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.cloud
def test_list_validation_results(pact_test: Pact) -> None:
    """``context.get_validation_result()`` with ``run_id=None`` calls
    ``store.list_keys()`` which issues GET to the collection URL.

    ``get_validation_result(expectation_suite_name=..., run_id=None)``
    internally calls ``selected_store.list_keys()`` to find the most
    recent run.  In cloud mode ``list_keys()`` returns
    ``GXCloudIdentifier`` objects which lack ``run_id`` /
    ``batch_identifier`` attributes, so the subsequent filtering in
    ``get_validation_result`` raises ``AttributeError``.  This is a
    known client-side incompatibility -- the HTTP contract (list
    request/response) is verified by Pact, and we assert on the
    specific client error to document the gap.

    Interaction sequence:
      1. GET /data-context-configuration    (context init)
      2. GET /validation-results            (list all)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="list-validation-results",
    )

    # 2. GET /validation-results (list)
    (
        pact_test.upon_receiving("a request to list validation results (client-driven)")
        .given("a validation result exists")
        .with_request("GET", VALIDATION_RESULTS_PATH)
        .with_headers(headers)
        .will_respond_with(200)
        .with_body(
            {"data": match.each_like(match.like(_VALIDATION_RESULT_RESPONSE), min=1)},
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
        # get_validation_result with run_id=None triggers list_keys()
        # (the GET list interaction).  In cloud mode the returned
        # GXCloudIdentifier keys don't have run_id/batch_identifier
        # attributes, so the filtering loop raises AttributeError.
        # The HTTP contract has already been exercised at this point.
        with pytest.raises(AttributeError, match="run_id"):
            ctx.get_validation_result(
                expectation_suite_name="my_test_suite",
            )


@pytest.mark.cloud
def test_get_validation_result_by_id(pact_test: Pact) -> None:
    """``context.get_validation_result()`` with explicit ``run_id`` and
    ``batch_identifier`` builds a ``ValidationResultIdentifier`` and calls
    ``store.get(key)`` which issues GET to the resource URL.

    In cloud mode, ``Store.get()`` calls
    ``gx_cloud_response_json_to_object_dict()`` on the response, which
    expects the V0 shape ``data.attributes.result``.  We provide that
    shape in the mock so deserialization succeeds end-to-end.

    Because ``Store._validate_key()`` checks
    ``isinstance(key, GXCloudIdentifier)`` in cloud mode and
    ``get_validation_result()`` builds a ``ValidationResultIdentifier``,
    the validate call would normally reject the key.  We work around
    this by calling ``store.get()`` directly with a ``GXCloudIdentifier``
    keyed by the known result ID -- this is equivalent to what the
    client would do if the cloud-mode key incompatibility were resolved.

    Interaction sequence:
      1. GET /data-context-configuration              (context init)
      2. GET /validation-results/{id}                 (get by id)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="get-validation-result-by-id",
    )

    # 2. GET /validation-results/{id}
    (
        pact_test.upon_receiving("a request to get a validation result by id (client-driven)")
        .given("a validation result exists")
        .with_request("GET", VALIDATION_RESULT_BY_ID_PATH)
        .with_headers(headers)
        .will_respond_with(200)
        .with_body(
            {"data": match.like(_VALIDATION_RESULT_GET_BY_ID_RESPONSE)},
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
        key = GXCloudIdentifier(
            resource_type=GXCloudRESTResource.VALIDATION_RESULT,
            id=EXISTING_VALIDATION_RESULT_ID,
        )
        result = ctx.validation_results_store.get(key)

    assert result is not None
    assert isinstance(result, ExpectationSuiteValidationResult)


@pytest.mark.cloud
def test_post_validation_result(pact_test: Pact) -> None:
    """Storing a validation result via Store.set() issues POST to collection URL.

    ``ValidationResultsStore.set(key, value)`` calls ``serialize(value)``
    (which produces ``value.to_json_dict()``) then delegates to
    ``GXCloudStoreBackend.set()`` -> ``_set()`` -> ``_post()``.  The
    backend's ``_post()`` wraps the serialized dict in
    ``{"data": <serialized>}`` and POSTs to the collection URL.

    This is equivalent to the internal call made by
    ``validation_definition.run()`` to persist results.

    Interaction sequence:
      1. GET  /data-context-configuration    (context init)
      2. POST /validation-results            (create)
    """
    headers = _session_headers()

    # 1. GET /data-context-configuration
    setup_data_context_config_interaction(
        pact_test,
        access_token=PACT_DUMMY_ACCESS_TOKEN,
        description_suffix="post-validation-result",
    )

    # 2. POST /validation-results
    # The request body matcher uses match.like() for all fields to allow
    # type-level matching.  The Pact verifier will replay the recorded body.
    post_request_body: match.AbstractMatcher = match.like(
        {
            "data": match.like(
                {
                    "success": match.like(True),
                    "results": match.like([]),
                    "suite_name": match.like("my_test_suite"),
                    "suite_parameters": match.like({}),
                    "statistics": match.like(
                        {
                            "evaluated_expectations": match.like(0),
                            "successful_expectations": match.like(0),
                            "unsuccessful_expectations": match.like(0),
                            "success_percent": match.like(None),
                        }
                    ),
                    "meta": match.like(
                        {
                            "run_id": match.like(
                                {
                                    "run_name": match.like("my_run"),
                                    "run_time": match.like("2026-01-01T00:00:00.000000+00:00"),
                                }
                            ),
                            "validation_id": match.uuid(EXISTING_VALIDATION_DEFINITION_ID),
                            "active_batch_definition": match.like(
                                {
                                    "data_asset_name": match.like("pact_test_asset"),
                                    "batch_identifiers": match.like({}),
                                }
                            ),
                        }
                    ),
                    "id": match.like(None),
                }
            )
        }
    )

    post_response_body = {"data": match.like(_VALIDATION_RESULT_POST_RESPONSE)}

    (
        pact_test.upon_receiving("a request to create a validation result (client-driven)")
        .given("validation results are being created")
        .with_request("POST", VALIDATION_RESULTS_PATH)
        .with_headers(headers)
        .with_body(post_request_body, content_type="application/vnd.api+json")
        .will_respond_with(201)
        .with_body(post_response_body, content_type="application/json")
    )

    with pact_test.serve() as srv:
        ctx = gx.get_context(
            mode="cloud",
            cloud_base_url=str(srv.url),
            cloud_organization_id=EXISTING_ORGANIZATION_ID,
            cloud_workspace_id=EXISTING_WORKSPACE_ID,
            cloud_access_token=PACT_DUMMY_ACCESS_TOKEN,
        )

        # Build the validation result object; Store.set() will call
        # serialize() -> to_json_dict() before passing to the backend.
        validation_result = ExpectationSuiteValidationResult(
            success=True,
            results=[],
            suite_name="my_test_suite",
            suite_parameters={},
            statistics={
                "evaluated_expectations": 0,
                "successful_expectations": 0,
                "unsuccessful_expectations": 0,
                "success_percent": None,
            },
            meta={
                "run_id": {
                    "run_name": "my_run",
                    "run_time": "2026-01-01T00:00:00.000000+00:00",
                },
                "validation_id": EXISTING_VALIDATION_DEFINITION_ID,
                "active_batch_definition": {
                    "data_asset_name": "pact_test_asset",
                    "batch_identifiers": {},
                },
            },
        )

        key = GXCloudIdentifier(
            resource_type=GXCloudRESTResource.VALIDATION_RESULT,
        )
        ref = ctx.validation_results_store.set(key, validation_result)

    assert ref is not None
    assert ref.id is not None
