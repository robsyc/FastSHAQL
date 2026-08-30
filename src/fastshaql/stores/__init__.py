"""Optional-dependency stores — one module per transport extra.

``fastshaql.stores.http`` ships the async SPARQL store behind the ``httpx``
extra. Import the transport module directly (``from fastshaql.stores.http
import HttpxSparqlStore``): this package stays importable without any extra
installed, so the helpful ``ImportError`` fires only for consumers of that
transport.
"""
