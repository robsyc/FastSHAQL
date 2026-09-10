"""QLever session — an OSS leg of the store matrix.

QLever has no always-on server: the image ships the ``qlever-index`` /
``qlever-server`` binaries, and the adapter drives them over ``docker exec``
in a container kept alive by a ``sleep`` entrypoint (the image's own
entrypoint is bypassed — its ``su -c`` quoting mangles plain commands — and
the container runs as the host uid so the mounted data dir is writable).

``load_graph`` is an **index rebuild**, not a live update: QLever's UPDATE/GSP
path is access-token-gated delta bookkeeping, too fragile to serve as the
per-case reset. At evaluation scale a rebuild is sub-second. Data crosses as
N-Quads (Quads keep named graphs; a plain ``Graph`` crosses as N-Triples) —
file transfer, not GSP, so the "never send TriG/N-Quads to a GSP target" rule
does not apply here.

Serving normalizes toward SPARQL 1.1 where QLever offers a knob: the query
timeout is raised and memory defensively capped for shared CI runners
(``_SERVE_ARGS``). Deviations without a knob — numeric literal rewriting to
``xsd:int``, zero-length paths on absent terms — are known-divergence
material (ADR-0022).
"""

from __future__ import annotations

import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import httpx
from rdflib import ConjunctiveGraph

from support.eval.session import (
    StoreSession,
    poll_until,
    sparql_triple_count,
    triple_total,
    verify_loaded,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rdflib import Graph
    from testcontainers.core.container import DockerContainer

QLEVER_IMAGE = "adfreiburg/qlever:commit-cdbe640c71"
_ACCESS_TOKEN = "fastshaql-eval"  # noqa: S105 — guards a container-local server
_INDEX_BASENAME = "eval"
# Query timeout raised from the 30 s default; memory defensively capped for
# shared CI runners (probe-verified flags at the pinned commit).
_SERVE_ARGS = (
    f"-i {_INDEX_BASENAME} -p 7001 -a {_ACCESS_TOKEN} -s 300s -m 2GB -c 1GB -e 256MB"
)
_TRIVIAL_SELECT = "SELECT * { ?a ?b ?c } LIMIT 1"


@dataclass
class QleverSession(StoreSession):
    """QLever server whose data is an index rebuilt on every ``load_graph``."""

    container: DockerContainer
    data_dir: Path
    query_endpoint: str
    image: str = QLEVER_IMAGE
    _client: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=60.0))

    def _run(self, cmd: str) -> None:
        result = self.container.exec(["bash", "-c", cmd])
        if result.exit_code != 0:
            tail = (result.output or b"")[-2000:].decode(errors="replace")
            raise RuntimeError(f"qlever exec failed ({cmd!r}): {tail}")

    def load_graph(self, graph: Graph) -> None:
        """Rebuild the index from *graph* and restart the server on it."""
        if isinstance(graph, ConjunctiveGraph):
            payload, suffix, fmt = graph.serialize(format="nquads"), "nq", "nq"
        else:
            payload, suffix, fmt = graph.serialize(format="nt"), "nt", "nt"
        (self.data_dir / f"data.{suffix}").write_text(payload, encoding="utf-8")
        # The server mmaps the index files; it must be dead before rebuilding.
        # The bracket pattern keeps pkill from matching (and killing) this
        # very shell, whose command line mentions the server's name.
        self._run("pkill -f '[q]lever-server' || true")

        def _server_gone() -> bool:
            # Poll until the port refuses connections — the deterministic death
            # signal. Not a process-table poll: PID 1 is `sleep infinity`, which
            # never reaps, so the dead server lingers as a zombie that pgrep
            # keeps matching; its listener socket closes at exit, though.
            try:
                self._client.post(
                    self.query_endpoint,
                    content=_TRIVIAL_SELECT.encode(),
                    headers={"Content-Type": "application/sparql-query"},
                )
            except httpx.TransportError:
                return True
            return False

        poll_until(_server_gone, timeout=30, what="qlever server shutdown")
        self._run(
            f"qlever-index -i {_INDEX_BASENAME} -s settings.json "
            f"-F {fmt} -f data.{suffix}"
        )
        self._run(f"nohup qlever-server {_SERVE_ARGS} >/dev/null 2>&1 &")
        poll_until(
            lambda: (
                self._client.post(
                    self.query_endpoint,
                    content=_TRIVIAL_SELECT.encode(),
                    headers={"Content-Type": "application/sparql-query"},
                ).status_code
                == 200
            ),
            timeout=60,
            what="qlever server",
        )
        # Union default graph = the whole rebuilt index, so the plain COUNT
        # must equal the quads written (each quad is one index entry).
        verify_loaded(
            "qlever",
            triple_total(graph),
            sparql_triple_count(self._client, self.query_endpoint),
        )

    def close(self) -> None:
        """Close the long-lived HTTP client (call from the session teardown)."""
        self._client.close()


@contextmanager
def start() -> Iterator[QleverSession]:
    """Run the QLever tooling container until the context exits."""
    from testcontainers.core.container import DockerContainer

    with tempfile.TemporaryDirectory(prefix="fastshaql-qlever-") as tmp:
        data_dir = Path(tmp)
        (data_dir / "settings.json").write_text("{}\n", encoding="utf-8")
        container = (
            DockerContainer(QLEVER_IMAGE)
            .with_exposed_ports(7001)
            .with_volume_mapping(tmp, "/data", "rw")
            .with_kwargs(
                working_dir="/data",
                entrypoint=["sleep", "infinity"],
                user=f"{os.getuid()}:{os.getgid()}",
            )
        )
        # start() inside the try: testcontainers does not stop a container
        # whose start failed (e.g. image pull) — the finally must.
        try:
            container.start()
            query_endpoint = (
                f"http://{container.get_container_host_ip()}"
                f":{container.get_exposed_port(7001)}/"
            )
            session = QleverSession(
                container=container,
                data_dir=data_dir,
                query_endpoint=query_endpoint,
            )
            try:
                yield session
            finally:
                session.close()
        finally:
            container.stop()
