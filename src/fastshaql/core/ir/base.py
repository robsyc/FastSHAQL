"""Common base for parsed SHACL shapes (``sh:Shape``).

See: https://www.w3.org/TR/shacl12-core/#shapes
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rdflib import URIRef


@dataclasses.dataclass(frozen=True, kw_only=True)
class ShapeIR:
    """Fields shared by ``NodeShapeIR`` and ``PropertyShapeIR`` (SHACL §2.1)."""

    iri: URIRef
    """Shape resource IRI. Named shapes use their RDF subject;
    blank-node shapes get a synthesized ``urn:fastshaql:inline:…``."""

    description: str | None = None
    """Human-readable text for GraphQL API documentation.
    Parser resolves (preferred-language > untagged > any chain):
    - ``rdfs:comment`` then ``rdfs:label`` on node shapes;
    - ``sh:description`` then ``sh:name`` on property shapes."""
