"""Kernel — shared leaves of the core pipeline (ADR-0001).

Framework-neutral primitives consumed by every core stage: constants,
identifier mangling, the request-scoped :class:`QueryContext`, RDF graph
loading, the GraphQL-over-HTTP envelope, and the filter-operator bridge
table. Leaves are imported directly (``from fastshaql.core.kernel.constants
import IRI_FIELD``) — no package-level re-export surface.
"""
