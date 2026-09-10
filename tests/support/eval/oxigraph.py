"""Oxigraph session — an OSS leg of the store matrix.

Oxigraph implements the SPARQL 1.1 protocol directly (query ``POST /query``,
update ``POST /update``, Graph Store Protocol on ``/store``) and needs no
provisioning step: the stock image serves on 7878 within ~1 s. There is no
health endpoint — readiness is a trivial SELECT round trip. The no-``FROM``
default graph is the unnamed graph only (standard SPARQL), unlike the union
contract the in-memory baseline and GraphDB adopt (ADR-0011). The pinned
image does ship the knob — ``oxigraph serve --union-default-graph``, or the
per-request ``?union-default-graph`` param — and its union includes the
unnamed graph, so it would match the contract; stock behavior is deliberate,
the matrix surfacing what a user pointing fastshaql at stock Oxigraph gets.
Affected cases are registered in ``support/eval/divergences.py``.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx

from support.eval.session import (
    StoreSession,
    check,
    gsp_payloads,
    gsp_triple_count,
    poll_until,
    verify_loaded,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rdflib import Graph

OXIGRAPH_IMAGE = "oxigraph/oxigraph:0.5.9"
_TRIVIAL_SELECT = "SELECT * { ?a ?b ?c } LIMIT 1"


@dataclass
class OxigraphSession(StoreSession):
    """Live Oxigraph server; loads graphs one GSP PUT at a time."""

    base_url: str
    query_endpoint: str
    image: str = OXIGRAPH_IMAGE
    _client: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=60.0))

    def load_graph(self, graph: Graph) -> None:
        """Replace the store's contents with *graph* (per-case data reset)."""
        response = self._client.post(
            f"{self.base_url}/update",
            content="CLEAR ALL",
            headers={"Content-Type": "application/sparql-update"},
        )
        check(response)
        for target, turtle, expected in gsp_payloads(graph):
            response = self._client.put(
                f"{self.base_url}/store?{target}",
                content=turtle.encode(),
                headers={"Content-Type": "text/turtle"},
            )
            check(response)
            verify_loaded(
                "oxigraph",
                expected,
                gsp_triple_count(self._client, f"{self.base_url}/store", target),
            )

    def close(self) -> None:
        """Close the long-lived HTTP client (call from the session teardown)."""
        self._client.close()


@contextmanager
def start() -> Iterator[OxigraphSession]:
    """Run Oxigraph in a container until the context exits."""
    from testcontainers.core.container import DockerContainer

    container = DockerContainer(OXIGRAPH_IMAGE).with_exposed_ports(7878)
    # start() inside the try: testcontainers does not stop a container whose
    # start failed (e.g. image pull) — the finally must.
    try:
        container.start()
        client = httpx.Client(timeout=10.0)
        base_url = (
            f"http://{container.get_container_host_ip()}"
            f":{container.get_exposed_port(7878)}"
        )
        query_url = f"{base_url}/query"

        def _ready() -> bool:
            response = client.post(
                query_url,
                content=_TRIVIAL_SELECT.encode(),
                headers={"Content-Type": "application/sparql-query"},
            )
            return response.status_code == 200

        poll_until(_ready, timeout=60, what="oxigraph")
        client.close()
        session = OxigraphSession(base_url=base_url, query_endpoint=query_url)
        try:
            yield session
        finally:
            session.close()
    finally:
        container.stop()
