"""HTTP-contract tests for the Django GraphQL adapter — ``adapters/django.py``.

Mirrors ``tests/tiers/adapters/test_fastapi.py``: successful queries, GraphQL validation
errors, HTTP-level error handling, fixture-driven smoke, GraphiQL IDE handling, and
request-scoped context via ``get_context``.

Order: GraphQL responses → HTTP error handling → fixtures & GraphiQL → context injection.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("django")

from typing import TYPE_CHECKING

from django.test import Client
from django.urls import clear_url_caches, path

from fastshaql.adapters.django import build_graphql_view
from fastshaql.core.execution.store import InMemoryStore, ResolverContext, SparqlStore
from fastshaql.core.kernel.context import lang_tags_from_accept_language
from support.cases import CaseSet
from support.goldens import canonicalize

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.views import View
    from graphql import GraphQLSchema

    from fastshaql.core.kernel.context import QueryContext


def _mount(view_cls: type[View]) -> Client:
    """Install ``view_cls`` at ``/graphql/`` on the test urlconf; return a ``Client``."""
    import support.django_conf.urls as urlconf

    urlconf.urlpatterns = [path("graphql/", view_cls.as_view())]
    clear_url_caches()
    return Client()


def _wire_view(
    schema: GraphQLSchema,
    store: SparqlStore,
    *,
    query_context: QueryContext | None = None,
    ide: bool = True,
) -> Client:
    def get_context(_request: HttpRequest) -> ResolverContext:
        return ResolverContext(store=store, query_context=query_context)

    return _mount(build_graphql_view(schema, get_context, ide=ide))


def test_django_graphql_success(minimal_schema, minimal_store) -> None:
    client = _wire_view(minimal_schema, minimal_store)

    response = client.post(
        "/graphql/",
        data=json.dumps({"query": "query { thing { iri label } }"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "data": {
            "thing": [
                {"iri": "http://example.org/thing-1", "label": "Alpha"},
                {"iri": "http://example.org/thing-2", "label": "Beta"},
            ]
        }
    }


def test_django_graphql_validation_error(minimal_schema, minimal_store) -> None:
    client = _wire_view(minimal_schema, minimal_store)

    response = client.post(
        "/graphql/",
        data=json.dumps({"query": "query { notAField { foo } }"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    body = response.json()
    assert body.get("data") is None
    assert body.get("errors")
    assert any("notAField" in err.get("message", "") for err in body["errors"])


def test_django_graphql_bad_json_returns_400(minimal_schema, minimal_store) -> None:
    client = _wire_view(minimal_schema, minimal_store)

    response = client.post(
        "/graphql/",
        data="{not-json",
        content_type="application/json",
    )

    assert response.status_code == 400


def test_django_graphql_wrong_content_type_returns_415(
    minimal_schema, minimal_store
) -> None:
    client = _wire_view(minimal_schema, minimal_store)

    response = client.post(
        "/graphql/",
        data=json.dumps({"query": "query { thing { iri } }"}),
        content_type="text/plain",
    )

    assert response.status_code == 415


@pytest.mark.parametrize(
    "body",
    [
        {"query": 123},
        {},
        {"query": "{ thing { iri } }", "variables": "nope"},
        {"query": "{ thing { iri } }", "operationName": 5},
    ],
)
def test_django_malformed_body_returns_400(
    minimal_schema, minimal_store, body: dict
) -> None:
    client = _wire_view(minimal_schema, minimal_store)

    response = client.post(
        "/graphql/",
        data=json.dumps(body),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_django_list_body_returns_400(minimal_schema, minimal_store) -> None:
    """A JSON-array (batch) body is rejected — batching is deferred (ADR-0019)."""
    client = _wire_view(minimal_schema, minimal_store)

    response = client.post(
        "/graphql/",
        data=json.dumps([{"query": "{ thing { iri } }"}]),
        content_type="application/json",
    )

    assert response.status_code == 400


def test_django_fixture_through_http(minimal_schema, minimal_store) -> None:
    """Declarative minimal/smoke case via the HTTP envelope."""
    case = CaseSet("minimal").load_case("smoke")
    client = _wire_view(minimal_schema, minimal_store, query_context=case.query_context)

    response = client.post(
        "/graphql/",
        data=json.dumps({"query": case.query}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert case.expected_json is not None
    assert canonicalize(response.json()) == canonicalize(case.expected_json)


def test_django_graphiql_served_when_ide_enabled(minimal_schema, minimal_store) -> None:
    client = _wire_view(minimal_schema, minimal_store, ide=True)

    response = client.get("/graphql/")

    assert response.status_code == 200
    assert "graphiql" in response.content.decode().lower()


def test_django_graphiql_disabled(minimal_schema, minimal_store) -> None:
    client = _wire_view(minimal_schema, minimal_store, ide=False)

    response = client.get("/graphql/")

    assert response.status_code == 405


def test_django_get_context_reads_request_headers(minimal_schema) -> None:
    """get_context receives the request: headers are readable for per-request
    context — here Accept-Language resolved into the language chain."""
    captured: dict[tuple[str, ...], None] = {}

    def get_context(request: HttpRequest) -> ResolverContext:
        lang_tags = lang_tags_from_accept_language(
            request.headers.get("Accept-Language")
        )
        captured[lang_tags] = None
        return ResolverContext(store=InMemoryStore(CaseSet("minimal").load_data()))

    client = _mount(build_graphql_view(minimal_schema, get_context, ide=True))

    response = client.post(
        "/graphql/",
        data=json.dumps({"query": "query { thing { iri } }"}),
        content_type="application/json",
        headers={"Accept-Language": "nl"},
    )

    assert response.status_code == 200
    assert ("nl",) in captured


def test_django_missing_get_context_raises_not_implemented(minimal_schema) -> None:
    """get_context=None leaves the subclass-override hook, which raises if used as-is."""
    client = _mount(build_graphql_view(minimal_schema, get_context=None, ide=True))

    with pytest.raises(NotImplementedError):
        client.post(
            "/graphql/",
            data=json.dumps({"query": "{ thing { iri } }"}),
            content_type="application/json",
        )


def test_django_async_get_context_is_awaited(minimal_schema) -> None:
    """An async get_context is awaited — its coroutine is not passed raw as context."""
    store = InMemoryStore(CaseSet("minimal").load_data())

    async def get_context(_request: HttpRequest) -> ResolverContext:
        return ResolverContext(store=store)

    client = _mount(build_graphql_view(minimal_schema, get_context, ide=True))

    response = client.post(
        "/graphql/",
        data=json.dumps({"query": "{ thing { iri label } }"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["data"]["thing"]
