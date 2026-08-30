"""Evaluation-tier fixtures — GraphDB testcontainer session."""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest

from fastshaql.stores.http import HttpxSparqlStore
from support.eval.graphdb import (
    GRAPHDB_IMAGE,
    REPO_ID,
    GraphDbSession,
    create_repository,
)
from support.eval.report import default_report_path, get_report

pytest.importorskip("testcontainers")

from typing import TYPE_CHECKING

from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Iterator

    from fastshaql.core.execution.store import SparqlStore

# GraphDB 11+ requires a license (even Free). Drop the verbatim license FILE at
# the default path (gitignored) or point GRAPHDB_LICENSE_FILE at it — it is
# mounted read-only into the container. A file (not an env string) preserves the
# license's formatting, which GraphDB validates strictly.
LICENSE_FILE = Path(
    os.environ.get(
        "GRAPHDB_LICENSE_FILE",
        Path(__file__).resolve().parent / "graphdb.license",
    )
)


def pytest_sessionfinish(
    session: pytest.Session,  # noqa: ARG001
    exitstatus: int,  # noqa: ARG001
) -> None:
    """Write the evaluation report once per session (pytest hook)."""
    get_report().write_json(default_report_path())


@pytest.fixture(scope="session")
def graphdb_session() -> Iterator[GraphDbSession]:
    """Session-scoped GraphDB CE container with one evaluation repository.

    The license file is mounted before start; readiness is the REST API
    returning 200 (version-agnostic). Repo creation is a post-start provisioning
    step, not a readiness check.
    """
    if not LICENSE_FILE.is_file() or LICENSE_FILE.stat().st_size == 0:
        pytest.skip(
            f"GraphDB license not found at {LICENSE_FILE}. Drop the verbatim "
            "license file there (or set GRAPHDB_LICENSE_FILE). See tests/README.md."
        )

    container = (
        DockerContainer(GRAPHDB_IMAGE)
        .with_exposed_ports(7200)
        .with_volume_mapping(
            str(LICENSE_FILE.resolve()),
            "/opt/graphdb/home/conf/graphdb.license",
            "ro",
        )
        .waiting_for(
            HttpWaitStrategy(7200, "/rest/repositories")
            .for_status_code(200)
            .with_startup_timeout(180)
        )
    )
    container.start()
    try:
        base_url = (
            f"http://{container.get_container_host_ip()}"
            f":{container.get_exposed_port(7200)}"
        )
        create_repository(base_url)

        query_endpoint = f"{base_url}/repositories/{REPO_ID}"
        session = GraphDbSession(
            base_url=base_url,
            query_endpoint=query_endpoint,
        )
        get_report().store_image = session.image
        try:
            yield session
        finally:
            session.close()
    finally:
        container.stop()


@pytest.fixture
async def graphdb_store(graphdb_session: GraphDbSession) -> AsyncIterator[SparqlStore]:
    """Function-scoped ``HttpxSparqlStore`` — fresh async client per test."""
    client = httpx.AsyncClient(timeout=60.0)
    store = HttpxSparqlStore(client, graphdb_session.query_endpoint)
    try:
        yield store
    finally:
        await client.aclose()
        graphdb_session.clear_repository()
