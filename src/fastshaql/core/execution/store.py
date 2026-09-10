"""SPARQL store protocol, wire-result decoding, and resolver context."""

from __future__ import annotations

import asyncio
import threading
import time
from collections.abc import Iterable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast, runtime_checkable

import orjson
from rdflib import BNode, Graph, Literal, URIRef
from rdflib.plugins.sparql.results.jsonresults import parseJsonTerm
from rdflib.query import ResultRow

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rdflib.query import Result

    from fastshaql.core.kernel.context import QueryContext

# The no-``FROM`` default-graph contract for ``Dataset``-backed stores is set by
# ``Dataset.default_union`` (instance), constructed in the test harness
# ``load_data()`` and any deployment data loader. The ``SPARQL_DEFAULT_GRAPH_UNION``
# *global* that used to live here was inert only while ``default_union=False``; it
# actively defeated ``default_union=True`` (the union contract), so it is removed
# — see ADR-0011 and the truth-table evidence in
# ``test_named_graph_isolation.py``.
SparqlTerm = URIRef | Literal | BNode
SparqlRow = dict[str, SparqlTerm]


def decode_sparql_results(raw: bytes) -> list[SparqlRow]:
    """Decode a SPARQL 1.2 SELECT result JSON body into term-typed rows.

    The wire-decode seam for HTTP-backed stores: an ``application/sparql-
    results+json`` SELECT body (``{"results": {"bindings": [...]}}``) becomes a
    list of ``SparqlRow`` with rdflib terms (``URIRef``/``Literal``/``BNode``)
    via rdflib's ``parseJsonTerm``. JSON is parsed with orjson for speed.

    Args:
        raw: The raw SPARQL-results+json SELECT response body.

    Returns:
        One dict per binding, keyed by variable name with rdflib term values.

    Raises:
        orjson.JSONDecodeError: If ``raw`` is not valid JSON (a ``ValueError``
            subclass, so HTTP stores may catch it broadly).
    """
    data: Any = orjson.loads(raw)
    bindings: list[dict[str, Any]] = data["results"]["bindings"]
    rows = [{k: parseJsonTerm(v) for k, v in binding.items()} for binding in bindings]
    return cast(list[SparqlRow], rows)


@runtime_checkable
class SparqlStore(Protocol):
    """Store-protocol SPARQL SELECT execution."""

    async def query(
        self, sparql: str, metrics: ExecutionMetrics | None = None
    ) -> list[SparqlRow]:
        """Execute a SPARQL SELECT and return variable bindings.

        Args:
            sparql: A complete SPARQL SELECT query string.
            metrics: When given (profiling runs only), an HTTP-backed store
                records its transport round trip (``http_ms``) and wire decode
                (``decode_ms``) on it. Implementations may ignore it. A store
                with a one-arg ``query`` keeps working while metrics is absent
                but cannot serve profiling runs — calling it with metrics
                attached fails loudly with ``TypeError``.

        Returns:
            One dict per result row, keyed by variable name (no ``?`` prefix)
            with rdflib terms (``URIRef``, ``Literal``, ``BNode``) as values.
        """
        ...  # pragma: no cover — Protocol stub


class InMemoryStore(SparqlStore):
    """``SparqlStore`` backed by an RDFLib graph (testing and local use).

    Queries are serialized by a lock, taken inside the worker thread (never
    across an ``await`` — that would block the event loop): graphql-core
    resolves sibling root fields concurrently and concurrent requests share
    one store, so ``graph.query`` runs on several threads at once — and
    rdflib's SPARQL parser (pyparsing) is not thread-safe. Unsynchronized,
    concurrent parses intermittently corrupt shared parser state into
    seemingly random ``BadSyntax`` errors on valid queries. Parse and
    execution lock in one scope: rdflib offers no seam between them.
    """

    def __init__(self, graph: Graph) -> None:
        self._graph = graph
        self._lock = threading.Lock()

    async def query(
        self,
        sparql: str,
        metrics: ExecutionMetrics | None = None,  # noqa: ARG002 — protocol slot
    ) -> list[SparqlRow]:
        """Execute via ``rdflib.Graph.query()`` and return row dicts.

        *metrics* is accepted for protocol compatibility and ignored — there
        is no meaningful http/decode split for an in-process store.
        """
        result = await asyncio.to_thread(self._locked_query, sparql)
        rows = cast(Iterable[ResultRow], result)
        return [cast(SparqlRow, row.asdict()) for row in rows]

    def _locked_query(self, sparql: str) -> Result:
        with self._lock:
            return self._graph.query(sparql)


@dataclass(slots=True)
class ExecutionMetrics:
    """Opt-in phase timings for profiling, one object per ResolverContext.

    ``execute_query`` fills ``total_ms`` (its whole wall clock) plus the
    ``translate_ms`` / ``store_ms`` / ``convert_ms`` phases; a store that
    accepts *metrics* splits ``store_ms`` into ``http_ms`` (transport round
    trip) and ``decode_ms`` (results-JSON decode). Phases are recorded when
    they complete — or as an exception unwinds through them — see
    :func:`timed`.

    One ``ResolverContext`` serves an entire operation: each root field's
    ``execute_query`` overwrites the previous values, so the numbers describe
    the last root field resolved. The graphql-core share of a single-field
    operation is the residual: ``graphql()`` wall clock minus ``total_ms``.
    Attach via ``ResolverContext.metrics``; ``None`` in production.
    """

    total_ms: float = 0.0
    translate_ms: float = 0.0
    store_ms: float = 0.0
    convert_ms: float = 0.0
    http_ms: float = 0.0
    decode_ms: float = 0.0


@contextmanager
def timed(metrics: ExecutionMetrics | None, attr: str) -> Iterator[None]:
    """Record a phase's elapsed ms on *metrics* (no-op when metrics is ``None``).

    No ``perf_counter`` calls and no attribute writes happen when metrics is
    absent, so the production path pays only the context-manager entry cost.
    The phase is recorded even when the wrapped body raises.
    """
    if metrics is None:
        yield
        return
    start = time.perf_counter()
    try:
        yield
    finally:
        setattr(metrics, attr, (time.perf_counter() - start) * 1e3)


@dataclass(frozen=True)
class ResolverContext:
    """Per-request state injected by the adapter via ``context_value``."""

    store: SparqlStore
    """SPARQL store used by resolvers to execute translated queries."""
    query_context: QueryContext | None = None
    """Optional language preference and future cross-cutting parameters."""
    metrics: ExecutionMetrics | None = None
    """When set, execute_query records per-phase ms."""
