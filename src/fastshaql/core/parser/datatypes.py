"""Parse a property shape's datatype set (SHACL Core §7.1.2, §7.7.3).

``sh:datatype`` in its IRI and SHACL-list forms and datatype-only ``sh:or``
are the union syntaxes — both normalize into one datatype tuple; any other
``sh:or`` is parse-recognized-and-inert.

See: https://www.w3.org/TR/shacl12-core/#datatype
See: https://www.w3.org/TR/shacl12-core/#or
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rdflib import RDF, SH, URIRef

from fastshaql.core.kernel.constants import STRING_FAMILY_DATATYPES

from .errors import UnsupportedShapeError
from .util import strict_rdf_list

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

logger = logging.getLogger(__name__)


def datatypes_from_shape(
    graph: Graph,
    prop_shape: Node,
    *,
    shape_iri: URIRef,
    field_name: str,
) -> tuple[URIRef, ...]:
    """Declared datatype constraints from ``sh:datatype`` / datatype-only
    ``sh:or`` (SHACL 1.2 Core §7.1.2, §7.7.3) — both union syntaxes
    normalize into one tuple.

    Rules: a single ``sh:datatype`` IRI is the classic form; a ``sh:datatype``
    SHACL list and an ``sh:or`` list whose members' only constraint is a
    single ``sh:datatype`` IRI are the union forms. Any other ``sh:or`` is
    parse-recognized-and-inert (warning; datatypes unchanged). Multi-entry
    sets are restricted to the string family
    (:data:`STRING_FAMILY_DATATYPES`) — outside it, loud rejection:
    silently flattening e.g. a numeric/string union to ``String`` would
    misdescribe the field.

    Raises:
        UnsupportedShapeError: On ``sh:datatype`` together with ``sh:or``
            or more than one ``sh:or`` value (legal SHACL, ANDed §7.7.3 —
            fastshaql lowers one datatype constraint); more than one
            ``sh:datatype`` value (ill-formed per the at-most-one rule,
            §7.1.2); an empty ``sh:datatype`` list; a malformed list; a
            non-IRI list member; or a multi-entry set outside the string
            family (message names the supported members).
    """
    at = f"sh:datatype/sh:or on {shape_iri} field {field_name!r}"
    datatypes = _datatype_objects(graph, prop_shape, at=at)
    or_values = list(graph.objects(prop_shape, SH["or"]))
    if datatypes and or_values:
        raise UnsupportedShapeError(
            f"{at}: sh:datatype and sh:or together is unsupported "
            "(SHACL ANDs the constraints, §7.7.3; fastshaql lowers one datatype constraint)"
        )
    if len(or_values) > 1:
        raise UnsupportedShapeError(
            f"{at}: multiple sh:or values are unsupported "
            "(SHACL ANDs the lists, §7.7.3; fastshaql lowers one)"
        )
    if or_values:
        or_datatypes = _or_datatypes(
            graph, or_values[0], shape_iri=shape_iri, field_name=field_name
        )
        if or_datatypes is None:
            return ()
        datatypes = or_datatypes
    if len(datatypes) > 1 and not set(datatypes) <= STRING_FAMILY_DATATYPES:
        raise UnsupportedShapeError(
            f"{at}: multi-entry datatype sets support the string family only "
            f"(xsd:string rdf:langString rdf:dirLangString; got "
            f"{' '.join(str(dt) for dt in datatypes)})"
        )
    return tuple(dict.fromkeys(datatypes))


def _datatype_objects(graph: Graph, prop_shape: Node, *, at: str) -> list[URIRef]:
    """``sh:datatype`` objects — the IRI form directly, the SHACL-list form
    walked (well-formedness and all-IRI members enforced; the empty list
    ``rdf:nil`` rejects — it is an IRI, not a datatype)."""
    values = list(graph.objects(prop_shape, SH.datatype))
    if len(values) > 1:
        raise UnsupportedShapeError(
            f"{at}: multiple sh:datatype values (SHACL 1.2 §7.1.2: "
            "a shape has at most one value for sh:datatype)"
        )
    if not values:
        return []
    value = values[0]
    if value == RDF.nil:
        raise UnsupportedShapeError(
            f"{at}: sh:datatype list is empty — declare at least one datatype IRI"
        )
    if isinstance(value, URIRef):
        return [value]
    members = strict_rdf_list(graph, value, what=f"{at}: sh:datatype")
    iri_members: list[URIRef] = []
    for member in members:
        if not isinstance(member, URIRef):
            raise UnsupportedShapeError(
                f"{at}: sh:datatype list members must be IRIs (got {member!r})"
            )
        iri_members.append(member)
    return iri_members


def _or_datatypes(
    graph: Graph,
    or_head: Node,
    *,
    shape_iri: URIRef,
    field_name: str,
) -> tuple[URIRef, ...] | None:
    """Datatypes of a datatype-only ``sh:or`` list, or ``None`` when any
    member carries another constraint (that ``sh:or`` is inert — warning)."""
    members = strict_rdf_list(
        graph, or_head, what=f"sh:or on {shape_iri} field {field_name!r}"
    )
    datatypes: list[URIRef] = []
    for member in members:
        datatype = _sole_datatype_constraint(graph, member)
        if datatype is None:
            logger.warning(
                "sh:or on %s field %r carries non-datatype constraints — "
                "validator-only, ignored for reads",
                shape_iri,
                field_name,
            )
            return None
        datatypes.append(datatype)
    return tuple(datatypes)


def _sole_datatype_constraint(graph: Graph, member: Node) -> URIRef | None:
    """The member's single ``sh:datatype`` IRI when it is the member's only
    constraint, else ``None``."""
    predicates = set(graph.predicates(member, None))
    if predicates != {SH.datatype}:
        return None
    objects = list(graph.objects(member, SH.datatype))
    if len(objects) != 1 or not isinstance(objects[0], URIRef):
        return None
    return objects[0]
