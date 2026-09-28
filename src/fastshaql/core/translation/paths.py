"""Map SHACL property paths (SHACL §4) to SPARQL property path AST (SPARQL §9)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, RDFS

import fastshaql.core.ir.shacl_path as shacl
import fastshaql.core.sparql.paths as sparql

if TYPE_CHECKING:
    from fastshaql.core.ir.shacl_path import ShaclPropertyPath
    from fastshaql.core.sparql.paths import SparqlPropertyPath


SHACL_INSTANCE_PATH = sparql.SequencePath(
    (
        sparql.PredicatePath(RDF.type),
        sparql.ZeroOrMorePath(sparql.PredicatePath(RDFS.subClassOf)),
    )
)
"""``rdf:type/rdfs:subClassOf*`` — the SHACL-instance path behind every
typing emission (ADR-0025): ``sh:targetClass`` roots (Core §3.1.3.2),
``sh:class`` bindings (§7.1.1), ``shnex:instancesOf`` (node-expr §4.5.1),
and filter-shape class conjuncts. SHACL instances of a class are nodes
typed with the class or any subclass (§1.1); the closure reads the
queried graphs only — the spec's §6.3 shapes-graph ``rdfs:subClassOf``
lookup is a documented deviation (ADR-0016)."""


def map_shacl_path_to_sparql_path(path: ShaclPropertyPath) -> SparqlPropertyPath:
    """Bridge Shape IR paths to SPARQL emission paths (SHACL §4, SPARQL §9)."""
    if isinstance(path, shacl.PredicatePath):
        return sparql.PredicatePath(path.iri)
    if isinstance(path, shacl.InversePath):
        return sparql.InversePath(map_shacl_path_to_sparql_path(path.path))
    if isinstance(path, shacl.SequencePath):
        return sparql.SequencePath(
            tuple(map_shacl_path_to_sparql_path(element) for element in path.elements)
        )
    if isinstance(path, shacl.AlternativePath):
        return sparql.AlternativePath(
            tuple(
                map_shacl_path_to_sparql_path(alternative)
                for alternative in path.alternatives
            )
        )
    if isinstance(path, shacl.ZeroOrMorePath):
        return sparql.ZeroOrMorePath(map_shacl_path_to_sparql_path(path.path))
    if isinstance(path, shacl.OneOrMorePath):
        return sparql.OneOrMorePath(map_shacl_path_to_sparql_path(path.path))
    if isinstance(path, shacl.ZeroOrOnePath):
        return sparql.ZeroOrOnePath(map_shacl_path_to_sparql_path(path.path))
    raise TypeError(
        f"Unsupported SHACL property path type: {type(path).__name__}"
    )  # pragma: no cover — closed type alias, exhaustive match
