"""Parse ``shnex:filterShape`` shapes into :class:`FilterShapeIR`
(ADR-0015).

Lowerable subset only: ``sh:hasValue``, ``sh:class`` (IRI or IRI list —
union within one value, conjunction across repetitions, Core §7.1.1),
``sh:rootClass`` (Core §7.9.4, same syntax), ``sh:datatype``,
``sh:pattern`` (+``sh:flags``), the four numeric range bounds,
``sh:minCount 1`` (nested inside ``sh:property``), and nested ``sh:property``
conjunction. Everything else — including ``sh:maxCount`` and
``sh:minCount k>1`` — is rejected loudly, naming the predicate. Inline
blank-node filter shapes only: a named shape reference needs registry
resolution and is rejected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from rdflib import RDF, SH, BNode, Literal, URIRef

from fastshaql.core.ir.filter_shape import (
    FilterClass,
    FilterCompare,
    FilterCompareOp,
    FilterConstraintIR,
    FilterDatatype,
    FilterHasValue,
    FilterMinCountOne,
    FilterProperty,
    FilterRegex,
    FilterRootClass,
    FilterShapeIR,
)

from ..errors import UnsupportedShapeError
from ..shacl_path import parse_shacl_path
from ..util import SH_CLASS, SH_ROOT_CLASS, strict_rdf_list

if TYPE_CHECKING:
    from rdflib import Graph
    from rdflib.term import Node

_LOWERING_HINT = (
    "lowerable subset: sh:hasValue, sh:class (IRI or class list), "
    "sh:rootClass, sh:datatype, sh:pattern, numeric ranges, "
    "sh:minCount 1 (inside sh:property), nested sh:property"
)


def parse_filter_shape(graph: Graph, shape_node: Node) -> FilterShapeIR:
    """Parse an inline ``shnex:filterShape`` value into conjuncts.

    Raises:
        UnsupportedShapeError: On non-blank-node shapes, unknown or
            non-lowerable constraints (naming the predicate), ill-typed
            constraint values, or malformed ``sh:property`` entries.
    """
    return _parse_shape(graph, shape_node, inside_property=False)


_CLASS_CONSTRAINTS: tuple[tuple[URIRef, type], ...] = (
    (SH_CLASS, FilterClass),
    (SH_ROOT_CLASS, FilterRootClass),
)
"""Class constraint predicate → conjunct constructor. Values are IRIs or
SHACL lists of IRIs — union within one value, conjunction across
repetitions (Core §7.1.1/§7.9.4)."""

_RANGE_CONSTRAINTS: tuple[tuple[URIRef, FilterCompareOp], ...] = (
    (SH.minInclusive, ">="),
    (SH.maxInclusive, "<="),
    (SH.minExclusive, ">"),
    (SH.maxExclusive, "<"),
)
"""Range-bound predicate → SPARQL comparison operator (AND over repetitions)."""


def _parse_shape(
    graph: Graph, shape_node: Node, *, inside_property: bool
) -> FilterShapeIR:
    if not isinstance(shape_node, BNode):
        raise UnsupportedShapeError(
            f"shnex:filterShape must be an inline blank-node shape (got {shape_node}) — "
            "named shape references are not supported"
        )
    _reject_unknown_predicates(graph, shape_node, inside_property=inside_property)

    conjuncts: list[FilterConstraintIR] = []
    conjuncts.extend(_has_value_conjuncts(graph, shape_node))
    for predicate, ctor in _CLASS_CONSTRAINTS:
        conjuncts.extend(_class_conjuncts(graph, shape_node, predicate, ctor))
    for value in graph.objects(shape_node, SH.datatype):
        if not isinstance(value, URIRef):
            raise UnsupportedShapeError(
                f"shnex:filterShape sh:datatype {value} — datatype values "
                "must be IRIs (Core §7.1.2)"
            )
        conjuncts.append(FilterDatatype(value))
    for predicate, op in _RANGE_CONSTRAINTS:
        for value in graph.objects(shape_node, predicate):
            if not isinstance(value, Literal):
                raise UnsupportedShapeError(
                    f"shnex:filterShape {predicate} bound {value} is not a literal"
                )
            conjuncts.append(FilterCompare(op, value))
    conjuncts.extend(_pattern_conjuncts(graph, shape_node))

    conjuncts.extend(_min_count_conjuncts(graph, shape_node, inside_property))
    if graph.value(shape_node, SH.maxCount) is not None:
        raise UnsupportedShapeError(
            f"shnex:filterShape sh:maxCount {graph.value(shape_node, SH.maxCount)} "
            "is not supported — cardinality upper bounds need k-variable EXISTS "
            "(implementation narrowing)"
        )

    for property_shape in graph.objects(shape_node, SH.property):
        conjuncts.extend(_parse_property_conjunct(graph, property_shape))
    return FilterShapeIR(conjuncts=tuple(conjuncts))


def _has_value_conjuncts(graph: Graph, shape_node: BNode) -> list[FilterConstraintIR]:
    """Parse ``sh:hasValue`` conjuncts (Core §7.5.1).

    Values are IRIs or literals; a blank node cannot be matched in a
    lowered FILTER and is rejected loudly.
    """
    conjuncts: list[FilterConstraintIR] = []
    for value in graph.objects(shape_node, SH.hasValue):
        if not isinstance(value, (URIRef, Literal)):
            raise UnsupportedShapeError(
                f"shnex:filterShape sh:hasValue {value} — blank nodes cannot "
                "be matched in a filter (IRI or literal required)"
            )
        conjuncts.append(FilterHasValue(value))
    return conjuncts


def _class_conjuncts(
    graph: Graph, shape_node: BNode, predicate: URIRef, ctor: type
) -> list[FilterConstraintIR]:
    """Parse one class-constraint predicate's values (Core §7.1.1/§7.9.4).

    Each value is an IRI, ``rdf:nil`` (the empty list — matches nothing), or
    a well-formed SHACL list of IRIs; repetitions are separate conjuncts
    (conjunction).
    """
    conjuncts: list[FilterConstraintIR] = []
    for value in graph.objects(shape_node, predicate):
        if value == RDF.nil:
            members: tuple[Node, ...] = ()
        elif isinstance(value, URIRef):
            members = (value,)
        elif isinstance(value, BNode):
            members = strict_rdf_list(
                graph, value, what=f"shnex:filterShape {predicate} list"
            )
        else:
            raise UnsupportedShapeError(
                f"shnex:filterShape {predicate} {value} is not an IRI or "
                "SHACL list of IRIs"
            )
        classes: list[URIRef] = []
        for member in members:
            if not isinstance(member, URIRef):
                raise UnsupportedShapeError(
                    f"shnex:filterShape {predicate} list member {member} is not an IRI"
                )
            classes.append(member)
        conjuncts.append(ctor(tuple(classes)))
    return conjuncts


def _reject_unknown_predicates(
    graph: Graph, shape_node: BNode, *, inside_property: bool
) -> None:
    allowed = {
        RDF.type,
        SH.minCount,
        SH.maxCount,
        SH.property,
        SH.pattern,
        SH.flags,
        SH.hasValue,
        SH.datatype,
        *(predicate for predicate, _ in _CLASS_CONSTRAINTS),
        *(predicate for predicate, _ in _RANGE_CONSTRAINTS),
    }
    if inside_property:
        allowed.add(SH.path)
    for predicate in graph.predicates(shape_node):
        if not isinstance(predicate, URIRef) or predicate in allowed:
            continue
        raise UnsupportedShapeError(
            f"shnex:filterShape constraint {predicate} is not supported — "
            f"{_LOWERING_HINT}"
        )


def _pattern_conjuncts(graph: Graph, shape_node: BNode) -> list[FilterConstraintIR]:
    """Parse ``sh:pattern`` (+``sh:flags``) — literal-checked (Core §7.4.3).

    One conjunct per pattern value (AND over repetitions); a single
    ``sh:flags`` value applies to every pattern.
    """
    flags = list(graph.objects(shape_node, SH.flags))
    if len(flags) > 1:
        raise UnsupportedShapeError(
            f"shnex:filterShape declares {len(flags)} sh:flags values — "
            "at most one is supported"
        )
    flag: Literal | None = None
    if flags:
        if not isinstance(flags[0], Literal):
            raise UnsupportedShapeError(
                f"shnex:filterShape sh:flags bound {flags[0]} is not a literal"
            )
        flag = flags[0]
    conjuncts: list[FilterConstraintIR] = []
    for value in graph.objects(shape_node, SH.pattern):
        if not isinstance(value, Literal):
            raise UnsupportedShapeError(
                f"shnex:filterShape sh:pattern bound {value} is not a literal"
            )
        conjuncts.append(FilterRegex(value, flag))
    return conjuncts


def _min_count_conjuncts(
    graph: Graph, shape_node: BNode, inside_property: bool
) -> list[FilterConstraintIR]:
    values = list(graph.objects(shape_node, SH.minCount))
    if not values:
        return []
    if not inside_property:
        raise UnsupportedShapeError(
            f"shnex:filterShape sh:minCount {values[0]} is only supported inside "
            "sh:property (a node-level minCount is vacuous)"
        )
    conjuncts: list[FilterConstraintIR] = []
    for value in values:
        if str(value) != "1":
            raise UnsupportedShapeError(
                f"shnex:filterShape sh:minCount {value} is not supported — "
                "only sh:minCount 1 lowers to flat SPARQL (implementation narrowing)"
            )
        conjuncts.append(FilterMinCountOne())
    return conjuncts


def _parse_property_conjunct(
    graph: Graph, property_shape: Node
) -> list[FilterProperty]:
    """Parse one ``sh:property`` entry into a path-scoped conjunct.

    The property-shape blank node doubles as the nested shape: its non-path
    constraints apply to the path's values, and it may carry further nested
    ``sh:property`` entries.
    """
    if not isinstance(property_shape, BNode):
        raise UnsupportedShapeError(
            f"shnex:filterShape sh:property must be a blank node (got {property_shape})"
        )
    if graph.value(property_shape, SH.path) is None:
        raise UnsupportedShapeError(
            f"shnex:filterShape sh:property without sh:path on {property_shape}"
        )
    path = parse_shacl_path(graph, property_shape)
    nested = _parse_shape(graph, property_shape, inside_property=True)
    return [FilterProperty(path=path, nested=nested)]
