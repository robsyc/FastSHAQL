"""``sh:NodeShape`` — structure and targeting for a class of focus nodes.

See: https://www.w3.org/TR/shacl12-core/#node-shapes
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .base import ShapeIR

if TYPE_CHECKING:
    from rdflib import URIRef

    from .node_expr import NodeExprIR
    from .property_shape import PropertyShapeIR


@dataclasses.dataclass(frozen=True, kw_only=True)
class NodeShapeIR(ShapeIR):
    """Parsed ``sh:NodeShape``. Must not carry ``sh:path`` (SHACL §3.2)."""

    graphql_type_name: str
    """Adapter-facing GraphQL type name. Resolution: ``sh:codeIdentifier``, else
    local name of ``iri`` (SHACL 1.2 §8.4). Not a SHACL term."""

    property_shapes: dict[str, PropertyShapeIR]
    """Nested property shapes keyed by ``graphql_field_name``."""

    target_class: URIRef | None = None
    """Focus-node class target. Parser: ``sh:targetClass`` (SHACL §3.1.3.2).
    Shapes with a target class become root query types;
    shapes without are reachable only via traversal."""

    target_expr: NodeExprIR | None = None
    """Derived target (ADR-0016). Parser: the single ``sh:targetNode``
    expression (SHACL §3.1.3.1), evaluated with the shape as focus node —
    or the implicit class target (§3.1.3.3) as ``shnex:instancesOf`` at the
    shape's own IRI. Mutually exclusive with ``target_class`` at parse time
    — an optional field pair, not a sum type."""

    implicit_class: bool = False
    """Whether *target_expr* is the implicit class target (Core §3.1.3.3)
    rather than an explicit ``sh:targetNode`` declaration. Recorded at parse
    time so :attr:`indexed_class` never re-derives it: an explicit
    ``sh:targetNode`` shape is not class-indexed even when its expression
    happens to enumerate the shape's own instances (ADR-0016)."""

    inherited_shape_iris: tuple[URIRef, ...] = ()
    """Parent shapes referenced by ``sh:node`` on this node shape (ADR-0005).
    IRI-sorted for deterministic diagnostics; property shapes are flattened into
    ``property_shapes`` at parse time."""

    @property
    def has_target(self) -> bool:
        """Whether the shape carries a supported target declaration —
        ``sh:targetClass``, ``sh:targetNode``, or an implicit class target
        (ADR-0016). Gates root-field publication and the visibility
        demotion warning."""
        return self.target_class is not None or self.target_expr is not None

    @property
    def indexed_class(self) -> URIRef | None:
        """The class this shape is class-indexed under: the ``sh:targetClass``
        value or, for an implicit class target (Core §3.1.3.3), the shape's
        own IRI — there ``shnex:instancesOf`` targets exactly the shape IRI,
        so the shape *is* the class. An explicit ``sh:targetNode`` expression
        is never class-indexed, whatever node set it computes (ADR-0016)."""
        if self.target_class is not None:
            return self.target_class
        if self.implicit_class:
            return self.iri
        return None
