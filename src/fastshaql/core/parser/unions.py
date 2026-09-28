"""Parse the ``sh:or`` member lane into polymorphic-relationship members.

SHACL Core §7.7.3 ``sh:or`` over members whose sole value constraint is one
of ``sh:class``/``sh:node`` is the polymorphic-relationship syntax
(ADR-0026); the datatype-member lane and the inert reading stay in
:mod:`datatypes`. Heterogeneous members reject loudly — GraphQL unions
cannot contain scalars; a member carrying any other constraint leaves the
whole ``sh:or`` inert, the same reading as the datatype lane. Ill-formed
values on the recognized predicates reject loudly — the malformations the
single-target lane rejects (§7.1.1/§7.8.1) never silently void a declared
union. Non-validating §8 metadata on a member is not a value constraint and
never blocks recognition. An empty ``sh:or ()`` is spec-legal but memberless
— a zero-member disjunction fails every value (§7.7.3) — so the lane warns
and ignores it: the field resolves from its direct constraints (an untyped
scalar when it has none), and the beside-anchor rejection never fires.

See: https://www.w3.org/TR/shacl12-core/#or
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rdflib import RDF, RDFS, SH, Literal, URIRef

from fastshaql.core.ir.property_shape import UnionMember

from .errors import UnsupportedShapeError
from .util import SH_CODE_IDENTIFIER, SH_NS, strict_rdf_list

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

logger = logging.getLogger(__name__)

_DATATYPE = "datatype"
"""Classifier sentinel for a sole-``sh:datatype`` member (the lane :mod:`datatypes` owns)."""

NON_VALIDATING_MEMBER_PREDICATES = frozenset(
    {
        SH.name,
        SH.description,
        SH["order"],
        SH["group"],
        URIRef(f"{SH_NS}intent"),
        URIRef(f"{SH_NS}agentInstruction"),
        URIRef(f"{SH_NS}unit"),
        SH_CODE_IDENTIFIER,
        RDF.type,
        RDFS.label,
        RDFS.comment,
    }
)
"""Member characteristics that add no value constraint — the full §8
non-validating set plus ``rdf:type`` and the §8.1-recommended node-shape
``rdfs:label``/``rdfs:comment``; recognition ignores them (ADR-0026 counts
constraints)."""


def sh_or_members(
    graph: Graph,
    prop_shape: Node,
    *,
    shape_iri: URIRef,
    field_name: str,
) -> tuple[UnionMember, ...] | None:
    """Members of an ``sh:or`` whose entries each carry exactly one
    ``sh:class`` or ``sh:node`` value constraint (ADR-0026), ``()`` for an
    empty ``sh:or`` (the warn-and-ignore lane — unsatisfiable per §7.7.3,
    so the field resolves from its direct constraints), or ``None`` when
    the ``sh:or`` is absent, belongs to the datatype lane, or is inert —
    those readings stay with
    :func:`~fastshaql.core.parser.datatypes.datatypes_from_shape`.
    Raw members carry one side per ``sh:or`` member; pass 2 resolves both.

    Raises:
        UnsupportedShapeError: On members mixing ``sh:datatype`` with
            ``sh:class``/``sh:node`` — GraphQL unions cannot contain scalars —
            or on an ill-formed value for a recognized predicate (multiple
            values, a literal, or a blank node where an IRI is required).
    """
    or_values = list(graph.objects(prop_shape, SH["or"]))
    if len(or_values) != 1:
        return None  # absent, or a multiple-values rejection owned by the datatype lane
    at = f"sh:or on {shape_iri} field {field_name!r}"
    members = strict_rdf_list(graph, or_values[0], what=at)
    if not members:
        logger.warning(
            "sh:or on %s field %r is empty — a memberless disjunction fails "
            "every value per the spec (SHACL 1.2 §7.7.3); ignored as "
            "unsatisfiable noise, the field resolves from its direct constraints",
            shape_iri,
            field_name,
        )
        return ()
    constraints = [_sole_value_constraint(graph, member, at=at) for member in members]
    parsed = [c for c in constraints if isinstance(c, UnionMember)]
    if _DATATYPE in constraints and parsed:
        raise UnsupportedShapeError(
            f"{at} mixes datatype and class/node members — GraphQL unions "
            "cannot contain scalars; declare the scalar and relationship "
            "constraints separately"
        )
    if None in constraints or not parsed:
        return None  # inert or datatype lane — the datatype lane owns both readings
    return tuple(parsed)


def _sole_value_constraint(
    graph: Graph,
    member: Node,
    *,
    at: str,
) -> UnionMember | str | None:
    """The member's single value constraint when it is the member's only
    one: an :class:`UnionMember` for ``sh:class``/``sh:node``, the
    ``"datatype"`` sentinel for ``sh:datatype``, else ``None`` (inert — the
    member carries another constraint).

    Raises:
        UnsupportedShapeError: On an ill-formed value for the recognized
            predicate — multiple values, a literal, or a blank node.
    """
    predicates = set(graph.predicates(member, None)) - NON_VALIDATING_MEMBER_PREDICATES
    for predicate, label in ((SH["class"], "sh:class"), (SH.node, "sh:node")):
        if predicates != {predicate}:
            continue
        objects = list(graph.objects(member, predicate))
        if len(objects) != 1 or isinstance(objects[0], Literal):
            raise UnsupportedShapeError(
                f"{at}: {label} in an sh:or member must be exactly one IRI "
                f"(got {', '.join(repr(o) for o in objects) or 'no value'})"
            )
        if not isinstance(objects[0], URIRef):
            raise UnsupportedShapeError(
                f"{at}: blank-node {label} in an sh:or member — inline shapes "
                "and the sh:class list form are not supported inside members"
            )
        if predicate == SH.node:
            return UnionMember(shape_iri=objects[0], class_iri=None)
        return UnionMember(shape_iri=None, class_iri=objects[0])
    if predicates == {SH.datatype}:
        objects = list(graph.objects(member, SH.datatype))
        if len(objects) == 1 and isinstance(objects[0], URIRef):
            return _DATATYPE
    return None
