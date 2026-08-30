"""HTTP-contract tests for the FastAPI GraphQL adapter — ``adapters/fastapi.py``.

Exercises ``build_graphql_router`` end-to-end via an ASGI client: successful
queries, GraphQL validation errors, HTTP-level error handling (malformed JSON,
wrong content type), fixture-driven smoke, GraphiQL IDE toggling, and FastAPI
sub-dependency injection into ``context_getter``.

Order: GraphQL responses → HTTP error handling → fixtures & GraphiQL → dependency injection.
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated

import pytest

pytest.importorskip("fastapi")

from fastapi import FastAPI, Header
from httpx import ASGITransport, AsyncClient

from fastshaql.adapters.fastapi import build_graphql_router
from fastshaql.core.execution.store import InMemoryStore, ResolverContext, SparqlStore
from fastshaql.core.kernel.context import lang_tags_from_accept_language
from support.cases import CaseSet
from support.goldens import canonicalize

if TYPE_CHECKING:
    from graphql import GraphQLSchema

    from fastshaql.core.kernel.context import QueryContext


def _make_app(
    schema: GraphQLSchema,
    store: SparqlStore,
    *,
    query_context: QueryContext | None = None,
    ide: bool = True,
) -> FastAPI:
    def context_getter() -> ResolverContext:
        return ResolverContext(store=store, query_context=query_context)

    app = FastAPI()
    app.include_router(build_graphql_router(schema, context_getter, ide=ide))
    return app


@asynccontextmanager
async def _client(app: FastAPI):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client


# --- GraphQL responses ---


async def test_fastapi_graphql_success(minimal_schema, minimal_store) -> None:
    app = _make_app(minimal_schema, minimal_store)

    async with _client(app) as client:
        response = await client.post(
            "/graphql",
            json={"query": "query { things { iri label } }"},
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "data": {
            "things": [
                {"iri": "http://example.org/thing-1", "label": "Alpha"},
                {"iri": "http://example.org/thing-2", "label": "Beta"},
            ]
        }
    }


async def test_fastapi_graphql_validation_error(minimal_schema, minimal_store) -> None:
    app = _make_app(minimal_schema, minimal_store)

    async with _client(app) as client:
        response = await client.post(
            "/graphql",
            json={"query": "query { notAField { foo } }"},
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body.get("data") is None
    assert body.get("errors")
    assert any("notAField" in err.get("message", "") for err in body["errors"])


# --- HTTP error handling ---


async def test_fastapi_graphql_bad_json_returns_400(
    minimal_schema, minimal_store
) -> None:
    app = _make_app(minimal_schema, minimal_store)

    async with _client(app) as client:
        response = await client.post(
            "/graphql",
            content="{not-json",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400


async def test_fastapi_graphql_wrong_content_type_returns_415(
    minimal_schema, minimal_store
) -> None:
    app = _make_app(minimal_schema, minimal_store)

    async with _client(app) as client:
        response = await client.post(
            "/graphql",
            content=json.dumps({"query": "query { things { iri } }"}),
            headers={"Content-Type": "text/plain"},
        )

    assert response.status_code == 415


@pytest.mark.parametrize(
    "body",
    [
        {"query": 123},
        {},
        {"query": "{ things { iri } }", "variables": "nope"},
        {"query": "{ things { iri } }", "operationName": 5},
    ],
)
async def test_fastapi_malformed_body_returns_400(
    minimal_schema, minimal_store, body: dict
) -> None:
    app = _make_app(minimal_schema, minimal_store)

    async with _client(app) as client:
        response = await client.post(
            "/graphql",
            json=body,
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400


async def test_fastapi_list_body_returns_400(minimal_schema, minimal_store) -> None:
    """A JSON-array (batch) body is rejected — batching is deferred (ADR-0019)."""
    app = _make_app(minimal_schema, minimal_store)

    async with _client(app) as client:
        response = await client.post(
            "/graphql",
            content=json.dumps([{"query": "{ things { iri } }"}]),
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400


# --- Fixtures & GraphiQL ---


async def test_fastapi_fixture_through_http(minimal_schema, minimal_store) -> None:
    """Declarative minimal/smoke case via the HTTP envelope."""
    case = CaseSet("minimal").load_case("smoke")
    app = _make_app(minimal_schema, minimal_store, query_context=case.query_context)

    async with _client(app) as client:
        response = await client.post(
            "/graphql",
            json={"query": case.query},
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 200
    assert case.expected_json is not None
    assert canonicalize(response.json()) == canonicalize(case.expected_json)


async def test_fastapi_graphiql_served_when_ide_enabled(
    minimal_schema, minimal_store
) -> None:
    app = _make_app(minimal_schema, minimal_store, ide=True)

    async with _client(app) as client:
        response = await client.get("/graphql")

    assert response.status_code == 200
    assert "graphiql" in response.text.lower()


async def test_fastapi_graphiql_disabled(minimal_schema, minimal_store) -> None:
    app = _make_app(minimal_schema, minimal_store, ide=False)

    async with _client(app) as client:
        response = await client.get("/graphql")

    assert response.status_code == 405


# --- Dependency injection ---


async def test_fastapi_context_getter_supports_header_dependency(
    minimal_schema,
) -> None:
    """context_getter is a real FastAPI dependency: sub-dependencies (headers)
    inject — here Accept-Language resolved into the language chain."""
    captured: dict[tuple[str, ...], None] = {}

    def context_getter(
        accept_language: Annotated[str | None, Header(alias="Accept-Language")] = None,
    ) -> ResolverContext:
        lang_tags = lang_tags_from_accept_language(accept_language)
        captured[lang_tags] = None
        return ResolverContext(store=InMemoryStore(CaseSet("minimal").load_data()))

    app = FastAPI()
    app.include_router(build_graphql_router(minimal_schema, context_getter))

    async with _client(app) as client:
        response = await client.post(
            "/graphql",
            json={"query": "query { things { iri } }"},
            headers={"Content-Type": "application/json", "Accept-Language": "nl"},
        )

    assert response.status_code == 200
    assert ("nl",) in captured
