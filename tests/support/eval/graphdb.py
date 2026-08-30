"""GraphDB CE session — the reference ``StoreSession`` adapter.

Container wiring lives in ``tests/tiers/evaluation/conftest.py``; this module
holds the session object that loads data into a repository over one long-lived
sync client. To plug in another store, implement ``StoreSession`` in a sibling
module — the harness consumes only that interface. See ADR-0022.

GraphDB 11+ requires a license even for the Free edition. The conftest mounts the
verbatim license FILE at ``tests/tiers/evaluation/graphdb.license`` (path
overridable via ``GRAPHDB_LICENSE_FILE``) into the container — a file, not an env
string, because GraphDB validates the license formatting strictly. In CI the
``GRAPHDB_LICENSE`` secret (the file content) is written to that path. Request a
free license at https://graphdb.ontotext.com/.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
from rdflib import ConjunctiveGraph, Graph

from support.eval.session import StoreSession

GRAPHDB_IMAGE = "ontotext/graphdb:11.4.0"
REPO_ID = "fastshaql-eval"


def _check(response: httpx.Response) -> None:
    """Raise with GraphDB's error body included (the 500 body says why)."""
    if response.status_code >= 400:
        raise httpx.HTTPStatusError(
            f"{response.request.method} {response.url} -> "
            f"{response.status_code}: {response.text}",
            request=response.request,
            response=response,
        )


REPO_CONFIG_TTL = f"""\
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>.
@prefix rep: <http://www.openrdf.org/config/repository#>.
@prefix sr: <http://www.openrdf.org/config/repository/sail#>.
@prefix sail: <http://www.openrdf.org/config/sail#>.
@prefix graphdb: <http://www.ontotext.com/config/graphdb#>.

[] a rep:Repository ;
    rep:repositoryID "{REPO_ID}" ;
    rdfs:label "fastshaql evaluation" ;
    rep:repositoryImpl [
        rep:repositoryType "graphdb:SailRepository" ;
        sr:sailImpl [
            sail:sailType "graphdb:Sail" ;
            graphdb:repository-type "file-repository" ;
            graphdb:ruleset "rdfsplus-optimized" ;
            graphdb:storage-folder "storage" ;
            graphdb:base-URL "http://example.org/owlim#" ;
            graphdb:entity-id-size "32" ;
        ] ;
    ] .
"""


@dataclass
class GraphDbSession(StoreSession):
    """Live GraphDB CE instance with a dedicated evaluation repository."""

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
            _check(response)

    def load_graph(self, graph: Graph) -> None:
        """Replace repository contents with *graph*.

        A ``Dataset`` (multi-graph) is serialised as TriG so named graphs survive
        the transfer — Turtle would silently drop them (ADR-0011). A
        plain ``Graph`` stays Turtle. GraphDB's RDF4J statements endpoint accepts
        both ``application/x-turtle`` and ``application/x-trig``.
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
        _check(response)

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
            _check(response)
