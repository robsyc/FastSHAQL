"""Parse named ``sh:NodeShape`` resources into :class:`NodeShapeIR`.

See: https://www.w3.org/TR/shacl12-core/#node-shapes
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from rdflib import RDFS, SH, URIRef

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR

from .errors import UnsupportedShapeError
from .property_shape import parse_property_shape
from .targets import parse_target
from .util import (
    first_localized_str,
    graphql_type_name,
    is_deactivated,
    read_code_identifier,
)

if TYPE_CHECKING:
    from rdflib import Graph

log = logging.getLogger(__name__)


def _parse_inherited_shape_iris(graph: Graph, shape_iri: URIRef) -> tuple[URIRef, ...]:
    """Read ``sh:node`` parent shape IRIs from a node shape (ADR-0005)."""
    iris: list[URIRef] = []
    for node_ref in graph.objects(shape_iri, SH.node):
        if not isinstance(node_ref, URIRef):
            raise UnsupportedShapeError(
                f"Blank-node sh:node on {shape_iri} — inline node shapes are not supported"
            )
        iris.append(node_ref)
    return tuple(sorted(iris, key=str))


def parse_node_shape(
    graph: Graph,
    shape_iri: URIRef,
    *,
    description_language: str = "en",
) -> NodeShapeIR:
    """Parse a single named ``sh:NodeShape`` into :class:`NodeShapeIR`.

    Iterates ``sh:property`` blank nodes, delegates to
    :func:`parse_property_shape`, and deduplicates by ``graphql_field_name``.

    Args:
        graph: An RDFLib graph containing the node shape definition.
        shape_iri: The IRI of the ``sh:NodeShape`` resource.
        description_language: BCP 47 tag for selecting ``description`` text. Defaults to ``"en"``.

    Returns:
        A parsed node shape with property shapes and metadata.
    """
    type_name = graphql_type_name(
        code_identifier=read_code_identifier(graph, shape_iri),
        iri=shape_iri,
    )
    property_shapes: dict[str, PropertyShapeIR] = {}
    for prop_node in graph.objects(shape_iri, SH.property):
        if is_deactivated(graph, prop_node):
            continue  # SHACL Core §3.1.6: not evaluated → no GraphQL field
        prop = parse_property_shape(
            graph,
            prop_node,
            parent_graphql_type_name=type_name,
            description_language=description_language,
        )
        if prop is None:
            continue  # can never hold values (§7.2.2/§7.9.3) → no GraphQL field
        if prop.graphql_field_name in property_shapes:
            log.warning(
                "Duplicate graphql field name %s in %s — skipping",
                prop.graphql_field_name,
                shape_iri,
            )
            continue
        property_shapes[prop.graphql_field_name] = prop

    target_class, target_expr, implicit_class = parse_target(graph, shape_iri)

    return NodeShapeIR(
        iri=shape_iri,
        description=first_localized_str(
            graph,
            shape_iri,
            RDFS.comment,
            RDFS.label,
            lang=description_language,
        ),
        graphql_type_name=type_name,
        target_class=target_class,
        target_expr=target_expr,
        implicit_class=implicit_class,
        property_shapes=property_shapes,
        inherited_shape_iris=_parse_inherited_shape_iris(graph, shape_iri),
    )
