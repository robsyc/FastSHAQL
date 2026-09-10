"""GraphDB Free session — the proprietary free-tier leg of the store matrix.

Container wiring lives in ``start()``; the session object loads data into a
repository over one long-lived sync client. To plug in another store,
implement ``StoreSession`` in a sibling module and register it in
``support.eval.stores`` — the harness consumes only that interface (ADR-0022).

License-gated leg: GraphDB 11+ requires a license even for the Free edition,
and without the license file the adapter skips itself out of the matrix.
License acquisition, the ``GRAPHDB_LICENSE_FILE`` override, and CI wiring
live in ``tests/README.md``.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
import pytest
from rdflib import ConjunctiveGraph, Dataset, Graph

from support.eval.session import StoreSession, check, triple_total, verify_loaded

if TYPE_CHECKING:
    from collections.abc import Iterator

GRAPHDB_IMAGE = "ontotext/graphdb:11.4.0"
REPO_ID = "fastshaql-eval"

REPO_CONFIG_TTL = f"""\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix graphdb: <http://www.ontotext.com/config/graphdb#>.

# ruleset "empty" — no entailment: every leg runs plain SPARQL 1.1 semantics
# (ADR-0022). An inferencing ruleset materializes extra triples the
# rdflib-validated goldens never see, and inflates the load read-back count.
[] a rep:Repository ;
    rep:repositoryID "{REPO_ID}" ;
    rdfs:label "fastshaql evaluation" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;
            graphdb:repository-type "file-repository" ;
            graphdb:ruleset "empty" ;
            graphdb:storage-folder "storage" ;
            graphdb:base-URL "http://example.org/owlim#" ;
            graphdb:entity-id-size "32" ;
        ] ;
    ] .
"""


@dataclass
class GraphDbSession(StoreSession):
    """Live GraphDB Free instance with a dedicated evaluation repository."""

    base_url: str
    query_endpoint: str
    image: str = GRAPHDB_IMAGE
    _client: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=60.0))

    def clear_repository(self) -> None:
        """Remove all statements from the evaluation repository."""
        response = self._client.delete(
            f"{self.base_url}/repositories/{REPO_ID}/statements"
        )
        if response.status_code not in {200, 204, 404}:
            check(response)

    def load_graph(self, graph: Graph) -> None:
        """Replace repository contents with *graph*.

        A ``Dataset`` (multi-graph) is serialised as TriG so named graphs survive
        the transfer — Turtle would silently drop them (ADR-0011). A
        plain ``Graph`` stays Turtle. GraphDB's RDF4J statements endpoint accepts
        both ``application/x-turtle`` and ``application/x-trig`` — the bulk-TriG
        rejection that rules this out on GSP-backed stores (ADR-0022) does not
        apply to it.
        """
        self.clear_repository()
        if isinstance(graph, ConjunctiveGraph):
            payload = graph.serialize(format="trig")
            content_type = "application/x-trig"
        else:
            payload = graph.serialize(format="turtle")
            content_type = "application/x-turtle"
        response = self._client.post(
            f"{self.base_url}/repositories/{REPO_ID}/statements",
            content=payload.encode(),
            headers={"Content-Type": content_type},
        )
        check(response)
        # Read the repository back and count: the statements endpoint has no
        # per-graph addressing, so the whole-repository TriG round trip is the
        # countable unit. Exact equality — the rdfsplus-optimized ruleset only
        # ever inflates it (entailed triples), and only if a case loads schema
        # triples, which none do today; an inflation failure is the signal.
        readback = self._client.get(
            f"{self.base_url}/repositories/{REPO_ID}/statements",
            headers={"Accept": "application/x-trig"},
        )
        check(readback)
        loaded = Dataset()
        loaded.parse(data=readback.text, format="trig")
        verify_loaded("graphdb", triple_total(graph), triple_total(loaded))

    def close(self) -> None:
        """Close the long-lived HTTP client (call from the session fixture teardown)."""
        self._client.close()


def create_repository(base_url: str) -> None:
    """Create the evaluation repository (idempotent — 409 is OK)."""
    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{base_url}/rest/repositories",
            files={
                "config": ("repo-config.ttl", REPO_CONFIG_TTL.encode(), "text/turtle")
            },
        )
        if response.status_code not in {201, 409}:
            check(response)


@contextmanager
def start() -> Iterator[GraphDbSession]:
    """Run GraphDB in a container until the context exits (skips without license)."""
    from testcontainers.core.container import DockerContainer
    from testcontainers.core.wait_strategies import HttpWaitStrategy

    # A file, not an env string: GraphDB validates the license's formatting
    # strictly. (This module lives at tests/support/eval/; the license at
    # tests/tiers/evaluation/.)
    default_license = (
        Path(__file__).resolve().parents[2] / "tiers" / "evaluation" / "graphdb.license"
    )
    license_file = Path(os.environ.get("GRAPHDB_LICENSE_FILE", default_license))
    if not license_file.is_file() or license_file.stat().st_size == 0:
        pytest.skip(
            f"GraphDB license not found at {license_file}. Drop the verbatim "
            "license file there (or set GRAPHDB_LICENSE_FILE). See tests/README.md."
        )

    container = (
        DockerContainer(GRAPHDB_IMAGE)
        .with_exposed_ports(7200)
        .with_volume_mapping(
            str(license_file.resolve()),
            "/opt/graphdb/home/conf/graphdb.license",
            "ro",
        )
        .waiting_for(
            HttpWaitStrategy(7200, "/rest/repositories")
            .for_status_code(200)
            .with_startup_timeout(180)
        )
    )
    # start() inside the try: testcontainers does not stop a container whose
    # start failed (image pull, wait-strategy timeout) — the finally must.
    try:
        container.start()
        base_url = (
            f"http://{container.get_container_host_ip()}"
            f":{container.get_exposed_port(7200)}"
        )
        create_repository(base_url)
        session = GraphDbSession(
            base_url=base_url,
            query_endpoint=f"{base_url}/repositories/{REPO_ID}",
        )
        try:
            yield session
        finally:
            session.close()
    finally:
        container.stop()
