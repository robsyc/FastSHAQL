"""Fuseki (Jena) session — an OSS leg of the store matrix.

The ``secoresearch/fuseki`` image's entrypoint ``exec``s its command argument,
so the adapter overrides the whole command: a ``--mem --update`` server on
dataset ``/mem`` (the name must differ from the image's bundled read-only
``/ds``). Endpoints carry the dataset in the URL (``/mem/query``,
``/mem/data``, ``/mem/update``); health is ``GET /$/ping``. The no-``FROM``
default graph is the unnamed graph only (standard Jena), unlike the union
contract the in-memory baseline and GraphDB adopt (ADR-0011) — and Jena's
union default graph option cannot close the gap either: its union excludes
the stored unnamed graph (reachable only as ``urn:x-arq:DefaultGraph``),
while the goldens include unnamed-graph data. That is why this leg is a
registered divergence rather than a configuration issue
(``support/eval/divergences.py``).
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import httpx

from support.eval.session import StoreSession, check, gsp_payloads

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rdflib import Graph

FUSEKI_IMAGE = "secoresearch/fuseki:6.2.0"
FUSEKI_COMMAND = (
    "java -cp /jena-fuseki/fuseki-server.jar:/javalibs/* "
    "org.apache.jena.fuseki.main.cmds.FusekiServerCmd --mem --update /mem"
)


@dataclass
class FusekiSession(StoreSession):
    """Live in-memory Fuseki server; loads graphs one GSP PUT at a time."""

    base_url: str
    query_endpoint: str
    image: str = FUSEKI_IMAGE
    _client: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=60.0))

    def load_graph(self, graph: Graph) -> None:
        """Replace the dataset's contents with *graph* (per-case data reset)."""
        response = self._client.post(
            f"{self.base_url}/mem/update", data={"update": "DROP SILENT ALL"}
        )
        check(response)
        for target, turtle in gsp_payloads(graph):
            response = self._client.put(
                f"{self.base_url}/mem/data?{target}",
                content=turtle.encode(),
                headers={"Content-Type": "text/turtle"},
            )
            check(response)

    def close(self) -> None:
        """Close the long-lived HTTP client (call from the session teardown)."""
        self._client.close()


@contextmanager
def start() -> Iterator[FusekiSession]:
    """Run Fuseki in a container until the context exits."""
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.wait_strategies import HttpWaitStrategy

    container = (
        DockerContainer(FUSEKI_IMAGE)
        .with_exposed_ports(3030)
        .with_command(FUSEKI_COMMAND)
        .waiting_for(HttpWaitStrategy(3030, "/$/ping").with_startup_timeout(180))
    )
    # start() inside the try: testcontainers does not stop a container whose
    # start failed (image pull, wait-strategy timeout) — the finally must.
    try:
        container.start()
        base_url = (
            f"http://{container.get_container_host_ip()}"
            f":{container.get_exposed_port(3030)}"
        )
        yield FusekiSession(base_url=base_url, query_endpoint=f"{base_url}/mem/query")
    finally:
        container.stop()
