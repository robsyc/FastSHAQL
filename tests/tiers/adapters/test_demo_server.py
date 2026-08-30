"""Example server smoke tests — decoupled from the declarative fixture harness.

Boots ``demo.server`` from arbitrary shapes/data paths
(not ``tests/fixtures`` registry entries) and asserts
a GraphQL response over HTTP.
"""

from __future__ import annotations

import json

import pytest

pytest.importorskip("fastapi")

from demo.server import ServerConfig, build_app
from httpx import ASGITransport, AsyncClient

from support.cases import CASES_ROOT
from support.goldens import canonicalize

_MINIMAL = CASES_ROOT / "minimal"
_SHAPES = _MINIMAL / "shapes.ttl"
_DATA = _MINIMAL / "data.ttl"
_QUERY_PATH = _MINIMAL / "smoke" / "query.graphql"
_EXPECTED_PATH = _MINIMAL / "smoke" / "expected.json"


@pytest.fixture
def minimal_server_config() -> ServerConfig:
    return ServerConfig(shapes=_SHAPES, data=_DATA)


async def test_example_server_in_memory_graphql(
    minimal_server_config: ServerConfig,
) -> None:
    app = build_app(minimal_server_config)
    query = _QUERY_PATH.read_text(encoding="utf-8")

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/graphql", json={"query": query})

    assert response.status_code == 200
    body = response.json()
    assert body.get("errors") is None
    expected = json.loads(_EXPECTED_PATH.read_text(encoding="utf-8"))
    assert canonicalize(body) == canonicalize(expected)


async def test_example_server_graphiql_enabled(
    minimal_server_config: ServerConfig,
) -> None:
    app = build_app(minimal_server_config)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/graphql", headers={"Accept": "text/html"})

    assert response.status_code == 200
    assert "graphiql" in response.text.lower()


async def test_example_server_accept_language_shapes_chain() -> None:
    """The demo's context getter resolves ``Accept-Language`` into the
    language chain: under ``en, nl;q=0.8`` the English name wins where it
    exists and the Dutch-only entity (Cees) survives via fallback."""
    language = CASES_ROOT / "language"
    config = ServerConfig(shapes=language / "shapes.ttl", data=language / "data.ttl")
    app = build_app(config)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/graphql",
            json={"query": "query { persons { name } }"},
            headers={"Accept-Language": "en, nl;q=0.8"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body.get("errors") is None
    names = {p["name"] for p in body["data"]["persons"]}
    assert names == {"Alice", "Bob", "Cees", "Eva", "Finn", "Gail"}


async def test_example_server_repeated_accept_language_lines_combine() -> None:
    """RFC 9110 §5.3: repeated header lines combine as-if-comma-joined —
    dropping either line changes the resolved set (``en`` alone loses
    Cees; ``nl`` alone loses every en-named entity)."""
    language = CASES_ROOT / "language"
    config = ServerConfig(shapes=language / "shapes.ttl", data=language / "data.ttl")
    app = build_app(config)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/graphql",
            json={"query": "query { persons { name } }"},
            headers=[("Accept-Language", "en"), ("Accept-Language", "nl;q=0.8")],
        )

    assert response.status_code == 200
    body = response.json()
    assert body.get("errors") is None
    names = {p["name"] for p in body["data"]["persons"]}
    assert names == {"Alice", "Bob", "Cees", "Eva", "Finn", "Gail"}
