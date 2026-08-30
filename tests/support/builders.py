"""Shape IR construction utilities shared across test tiers."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, cast

from rdflib import URIRef
from rdflib.namespace import XSD

from fastshaql.core.ir.node_shape import NodeShapeIR
from fastshaql.core.ir.property_shape import PropertyShapeIR
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.registry import ShapeRegistry

if TYPE_CHECKING:
    from rdflib.term import Node

    from fastshaql.core.ir.node_expr import NodeExprIR

EX = URIRef("http://example.org/")

_UNSET = object()


def _resolve_datatypes(
    datatype: URIRef | None, datatypes: tuple[URIRef, ...] | None
) -> tuple[URIRef, ...]:
    """Merge the single-datatype kwarg with the multi-entry passthrough.

    Both given mirrors parser rule 4 (``sh:datatype`` + ``sh:or``): an
    ambiguous constraint, rejected loudly.
    """
    if datatype is not None and datatypes is not None:
        raise ValueError("pass datatype= or datatypes=, not both")
    if datatypes is not None:
        return datatypes
    return (datatype,) if datatype is not None else ()


def scalar_property(
    name: str,
    *,
    min_count: int | None,
    max_count: int | None,
    datatype: URIRef | None = XSD.string,
    datatypes: tuple[URIRef, ...] | None = None,
) -> PropertyShapeIR:
    """Build a scalar :class:`PropertyShapeIR`.

    ``datatypes=`` builds multi-entry (union/language) literal spaces.
    """
    return PropertyShapeIR(
        iri=EX + f"{name}Prop",
        description=None,
        graphql_field_name=name,
        path=PredicatePath(EX + name),
        datatypes=_resolve_datatypes(datatype, datatypes),
        min_count=min_count,
        max_count=max_count,
    )


def relationship_property(
    name: str,
    value_shape_iri: URIRef,
    *,
    min_count: int | None,
    max_count: int | None,
    value_class: URIRef | None = None,
) -> PropertyShapeIR:
    """Build a relationship :class:`PropertyShapeIR`."""
    return PropertyShapeIR(
        iri=EX + f"{name}Prop",
        description=None,
        graphql_field_name=name,
        path=PredicatePath(EX + name),
        datatypes=(),
        min_count=min_count,
        max_count=max_count,
        value_class=value_class,
        value_shape_iri=value_shape_iri,
    )


def enum_property(
    name: str,
    *,
    in_values: tuple[Node, ...],
    min_count: int | None = 1,
    max_count: int | None = 1,
    datatype: URIRef | None = None,
    datatypes: tuple[URIRef, ...] | None = None,
) -> PropertyShapeIR:
    """Build an enum :class:`PropertyShapeIR`."""
    return PropertyShapeIR(
        iri=EX + f"{name}Prop",
        description=None,
        graphql_field_name=name,
        path=PredicatePath(EX + name),
        datatypes=_resolve_datatypes(datatype, datatypes),
        min_count=min_count,
        max_count=max_count,
        in_values=in_values,
    )


def derived_property(
    name: str,
    *,
    values_expr: NodeExprIR,
    min_count: int | None,
    max_count: int | None,
    datatype: URIRef | None = XSD.string,
    datatypes: tuple[URIRef, ...] | None = None,
) -> PropertyShapeIR:
    """Build a derived :class:`PropertyShapeIR` (``sh:values``; ADR-0015).

    ``datatypes=`` builds multi-entry (union/language) literal spaces.
    """
    return PropertyShapeIR(
        iri=EX + f"{name}Prop",
        description=None,
        graphql_field_name=name,
        path=PredicatePath(EX + name),
        datatypes=_resolve_datatypes(datatype, datatypes),
        min_count=min_count,
        max_count=max_count,
        values_expr=values_expr,
    )


def defaulted_property(
    name: str,
    *,
    default_expr: NodeExprIR,
    min_count: int | None,
    max_count: int | None,
    datatype: URIRef | None = XSD.string,
    datatypes: tuple[URIRef, ...] | None = None,
    values_expr: NodeExprIR | None = None,
) -> PropertyShapeIR:
    """Build a defaulted scalar :class:`PropertyShapeIR` (``sh:defaultValue``)."""
    return dataclasses.replace(
        scalar_property(
            name,
            min_count=min_count,
            max_count=max_count,
            datatype=datatype,
            datatypes=datatypes,
        ),
        values_expr=values_expr,
        default_expr=default_expr,
    )


def node_shape(
    name: str,
    *,
    target_class: URIRef | object | None = _UNSET,
    target_expr: NodeExprIR | None = None,
    implicit_class: bool = False,
    property_shapes: dict[str, PropertyShapeIR] | None = None,
) -> NodeShapeIR:
    """Build a :class:`NodeShapeIR`.

    ``target_class`` defaults to ``EX + name``; pass ``None`` explicitly for
    an untargeted shape (or one targeted by *target_expr*, ADR-0016 — set
    ``implicit_class`` for the §3.1.3.3 form so the shape class-indexes).
    """
    resolved: URIRef | None = (
        cast("URIRef | None", target_class) if target_class is not _UNSET else EX + name
    )
    return NodeShapeIR(
        iri=EX + f"{name}Shape",
        description=None,
        graphql_type_name=name,
        target_class=resolved,
        target_expr=target_expr,
        implicit_class=implicit_class,
        property_shapes=property_shapes or {},
    )


def shape_with(shape: NodeShapeIR, **fields: PropertyShapeIR) -> NodeShapeIR:
    """Return a copy of *shape* with additional or modified properties."""
    return dataclasses.replace(
        shape, property_shapes={**shape.property_shapes, **fields}
    )


def registry_with(registry: ShapeRegistry, shape: NodeShapeIR) -> ShapeRegistry:
    """Return a copy of *registry* with *shape* replacing the matching type."""
    return ShapeRegistry(
        tuple(
            shape if s.graphql_type_name == shape.graphql_type_name else s
            for s in registry.shapes
        )
    )
