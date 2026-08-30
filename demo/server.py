"""fastshaql example server — SHACL shapes to GraphQL over your data or store.

Run from repo root (no flags serves the bundled quickstart fixture)::

    uv sync --all-extras --all-groups --all-packages
    uv run --package fastshaql-demo python -m demo.server
    # GraphiQL: http://127.0.0.1:8000/graphql

Bring your own data, or point at a real triple store::

    uv run --package fastshaql-demo python -m demo.server \\
        --shapes path/to/shapes.ttl --data path/to/data.ttl
    uv run --package fastshaql-demo python -m demo.server \\
        --shapes path/to/shapes.ttl --endpoint http://localhost:7200/repositories/my-repo
"""

from __future__ import annotations

import argparse
import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import httpx
from fastapi import FastAPI, Header
from rdflib import Dataset

from fastshaql import build_executable_schema, load_shapes, parse_shapes
from fastshaql.adapters.fastapi import build_graphql_router
from fastshaql.core import (
    InMemoryStore,
    QueryContext,
    ResolverContext,
    SparqlRow,
    SparqlStore,
    lang_tags_from_accept_language,
)
from fastshaql.stores.http import HttpxSparqlStore

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

QUICKSTART = Path(__file__).resolve().parent / "quickstart"


@dataclass(frozen=True)
class ServerConfig:
    """Inputs for ``build_app`` — shapes are required; data or endpoint, not both.

    Raises ``SystemExit`` on invalid input at construction, so
    ``demo.server`` and ``demo.throughput`` fail with the same messages.
    """

    shapes: Path
    data: Path | None = None
    endpoint: str | None = None
    fake_latency: float = 0.0

    def __post_init__(self) -> None:
        if not self.shapes.exists():
            raise SystemExit(f"shapes path not found: {self.shapes}")
        if self.data is not None and self.endpoint is not None:
            raise SystemExit("pass --data or --endpoint, not both")
        if self.data is None and self.endpoint is None:
            raise SystemExit("one of --data or --endpoint is required")
        if self.data is not None and not self.data.exists():
            raise SystemExit(f"data path not found: {self.data}")


@dataclass
class LatencyStore:
    """Wrap a store with an artificial sleep for async-concurrency load tests."""

    inner: SparqlStore
    delay: float

    async def query(self, sparql: str) -> list[SparqlRow]:
        if self.delay:
            await asyncio.sleep(self.delay)
        return await self.inner.query(sparql)


def load_data_graph(path: Path) -> Dataset:
    """Load RDF data from a file or every ``*.ttl``/``*.trig`` in a directory.

    Data keeps its own directory walk: it parses into a
    ``Dataset(default_union=True)`` (quads preserved — ``load_shapes`` merges
    into a plain ``Graph``, which would drop TriG named graphs) so the bare
    no-``FROM`` default graph is the union of all graphs — matching GraphDB
    and the test-harness contract (ADR-0011). Explicit ``FROM`` isolates regardless.
    """
    ds = Dataset(default_union=True)
    if path.is_dir():
        rdf_files = sorted(f for f in path.iterdir() if f.suffix in {".ttl", ".trig"})
        if not rdf_files:
            raise SystemExit(f"no *.ttl/*.trig files under {path}")
        for rdf_file in rdf_files:
            ds.parse(rdf_file)
    else:
        ds.parse(path)
    return ds


def build_app(config: ServerConfig) -> FastAPI:
    """Build a FastAPI app from ``ServerConfig``."""
    schema = build_executable_schema(parse_shapes(load_shapes(config.shapes)))
    client: httpx.AsyncClient | None = None
    store: SparqlStore
    if config.endpoint is not None:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        )
        store = HttpxSparqlStore(client, config.endpoint)
    else:
        assert config.data is not None
        store = InMemoryStore(load_data_graph(config.data))

    if config.fake_latency:
        store = LatencyStore(store, config.fake_latency)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        if client is not None:
            await client.aclose()

    def get_context(
        x_default_graph: Annotated[
            list[str] | None, Header(alias="X-Default-Graph")
        ] = None,
        accept_language: Annotated[
            list[str] | None, Header(alias="Accept-Language")
        ] = None,
    ) -> ResolverContext:
        # Accept the header repeated (one graph per line) or comma-joined —
        # a JSON Headers pane cannot repeat keys, so comma-joining is the
        # in-browser form.
        read_graphs = tuple(
            iri.strip()
            for value in x_default_graph or ()
            for iri in value.split(",")
            if iri.strip()
        )
        # Repeated lines combine as-if-comma-joined (RFC 9110 §5.3) —
        # same acceptance shape as X-Default-Graph above.
        lang_tags = lang_tags_from_accept_language(
            ", ".join(accept_language) if accept_language else None
        )
        query_context = QueryContext(lang_tags=lang_tags, read_graphs=read_graphs)
        if not query_context.lang_tags and not query_context.read_graphs:
            query_context = None
        return ResolverContext(store=store, query_context=query_context)

    app = FastAPI(
        title="fastshaql example",
        description="SHACL → GraphQL → SPARQL",
        lifespan=lifespan,
    )
    app.include_router(
        build_graphql_router(schema, get_context, ide=True, path="/graphql")
    )
    return app


def main() -> None:
    import uvicorn

    parser = argparse.ArgumentParser(description="fastshaql example server")
    parser.add_argument(
        "--shapes",
        type=Path,
        help="SHACL shapes file or directory of *.ttl (default: bundled quickstart)",
    )
    parser.add_argument(
        "--data",
        type=Path,
        help="RDF data file (*.ttl/*.trig) or directory of them (in-memory store)",
    )
    parser.add_argument(
        "--endpoint",
        help="SPARQL query endpoint URL (httpx store, e.g. GraphDB repository URL)",
    )
    parser.add_argument(
        "--fake-latency",
        type=float,
        default=0.0,
        help="Artificial store delay in seconds per query",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    shapes = args.shapes or QUICKSTART / "shapes.ttl"
    data = args.data
    if data is None and args.endpoint is None:
        data = QUICKSTART / "data.trig"
    config = ServerConfig(
        shapes=shapes,
        data=data,
        endpoint=args.endpoint,
        fake_latency=args.fake_latency,
    )
    uvicorn.run(build_app(config), host=args.host, port=args.port)


if __name__ == "__main__":
    main()
