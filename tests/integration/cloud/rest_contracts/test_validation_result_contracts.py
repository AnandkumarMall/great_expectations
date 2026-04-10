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

These tests exercise the ``GXCloudStoreBackend`` for validation results
directly, since validation results are stored through the store backend
rather than a high-level factory like datasources or checkpoints.
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
from great_expectations.data_context.store.gx_cloud_store_backend import (
    GXCloudStoreBackend,
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

# Minimal ValidationResultResponseData returned by the V1 API.
_VALIDATION_RESULT_RESPONSE: Final[dict] = {
    "id": match.uuid(),
    "organization_id": match.uuid(),
    "created_by_id": match.uuid(),
    "results": match.like([]),
    "suite_name": match.like(None),
    "suite_parameters": match.like(None),
    "statistics": match.like({}),
    "meta": match.like(
        {
            "run_id": match.like(None),
            "run_time": match.like("2026-01-01T00:00:00.000000Z"),
            "run_name": match.like(None),
        }
    ),
    "batch_id": match.like(None),
    "result_url": match.like(None),
    "success": match.like(True),
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _session_headers() -> dict:
    """Return request headers matching what the Python client sends."""
    return pact_session_headers()


def _get_validation_results_backend(ctx: gx.DataContext) -> GXCloudStoreBackend:
    """Extract the GXCloudStoreBackend for validation results from the context.

    We access the store backend directly rather than going through the
    ``ValidationResultsStore`` wrapper because the store's
    ``gx_cloud_response_json_to_object_dict`` expects the legacy V0 response
    format while the V1 endpoint returns a different shape.  Testing at the
    backend level exercises the actual HTTP contract (request path, headers,
    body) without coupling to the deserialization layer.
    """
    backend: GXCloudStoreBackend = ctx.validation_results_store.store_backend  # type: ignore[assignment]
    return backend


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.cloud
def test_list_validation_results(pact_test: Pact) -> None:
    """Listing validation results via _get_all() issues GET to collection URL.

    The ``GXCloudStoreBackend._get_all()`` method calls
    ``_send_get_request_to_api`` on the collection URL.  The response
    contains ``{"data": [<ValidationResultResponseData>, ...]}``.

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
        backend = _get_validation_results_backend(ctx)
        response = backend._get_all()

    assert "data" in response
    assert len(response["data"]) >= 1


@pytest.mark.cloud
def test_get_validation_result_by_id(pact_test: Pact) -> None:
    """Retrieving a validation result by ID issues GET to the resource URL.

    The ``GXCloudStoreBackend._get()`` method builds a URL with the
    resource ID and calls ``_send_get_request_to_api``.  The response
    contains ``{"data": <ValidationResultResponseData>}``.

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
        pact_test.upon_receiving(
            "a request to get a validation result by id (client-driven)"
        )
        .given("a validation result exists")
        .with_request("GET", VALIDATION_RESULT_BY_ID_PATH)
        .with_headers(headers)
        .will_respond_with(200)
        .with_body(
            {"data": match.like(_VALIDATION_RESULT_RESPONSE)},
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
        backend = _get_validation_results_backend(ctx)
        key = (
            GXCloudRESTResource.VALIDATION_RESULT,
            EXISTING_VALIDATION_RESULT_ID,
            None,
        )
        response = backend._get(key)

    assert "data" in response
    assert response["data"]["id"] is not None


@pytest.mark.cloud
def test_post_validation_result(pact_test: Pact) -> None:
    """Storing a validation result via store.set() issues POST to collection URL.

    The ``GXCloudStoreBackend._post()`` method constructs the V1 payload
    (``{"data": <serialized_result>}``) and POSTs to the collection URL.
    The store's ``serialize()`` method calls ``value.to_json_dict()`` which
    produces the fields the V1 API expects.

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
                                    "run_time": match.like(
                                        "2026-01-01T00:00:00.000000+00:00"
                                    ),
                                }
                            ),
                        }
                    ),
                    "id": match.like(None),
                }
            )
        }
    )

    post_response_body = {"data": match.like(_VALIDATION_RESULT_RESPONSE)}

    (
        pact_test.upon_receiving(
            "a request to create a validation result (client-driven)"
        )
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

        backend = _get_validation_results_backend(ctx)

        # Build the serialized validation result (what store.serialize() produces)
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
            },
        )

        # The store serializes via to_json_dict() before calling _set/_post.
        serialized = validation_result.to_json_dict()

        key = (GXCloudRESTResource.VALIDATION_RESULT, None, None)
        ref = backend._set(key, serialized)

    assert ref is not None
    assert ref.id is not None
