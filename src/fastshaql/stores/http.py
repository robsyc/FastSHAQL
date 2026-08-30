"""Async SPARQL store over a caller-owned ``httpx.AsyncClient`` (``httpx`` extra).

``HttpxSparqlStore`` implements the ``SparqlStore`` protocol from
``fastshaql.core`` and decodes responses through the shared core wire-decode
seam (``decode_sparql_results``). The caller owns the client lifecycle — create
it once per process (e.g. in a FastAPI lifespan), tune pooling, transports,
time-outs, and any caching on it, and close it on shutdown. See ``demo.server``
for reference wiring.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    import httpx
except ModuleNotFoundError as e:  # pragma: no cover — exercised by `just import-guard`
    raise ImportError(
        "httpx is required to use HttpxSparqlStore; "
        'install it with "pip install fastshaql[httpx]"'
    ) from e

from fastshaql.core import SparqlRow, SparqlStore, decode_sparql_results


@dataclass
class HttpxSparqlStore(SparqlStore):
    """Async ``SparqlStore`` over a caller-owned ``httpx.AsyncClient``.

    Args:
        client: A long-lived async HTTP client (typically one per process) —
            the caller's optimization surface: pooling, transports, caching.
        query_endpoint: Full SPARQL query URL, e.g.
            ``http://localhost:7200/repositories/my-repo``.
    """

    client: httpx.AsyncClient
    query_endpoint: str

    async def query(self, sparql: str) -> list[SparqlRow]:
        """Execute a SPARQL SELECT and return variable bindings."""
        response = await self.client.post(
            self.query_endpoint,
            content=sparql.encode(),
            headers={
                "Accept": "application/sparql-results+json",
                "Content-Type": "application/sparql-query",
            },
        )
        if response.is_error:
            raise httpx.HTTPStatusError(
                f"SPARQL endpoint returned {response.status_code}: {response.text}",
                request=response.request,
                response=response,
            )
        return decode_sparql_results(response.content)
