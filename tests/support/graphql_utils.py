"""GraphQL AST helpers shared by runners and integration tests."""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql import parse as gql_parse
from graphql.language.ast import FieldNode
from graphql.language.parser import OperationDefinitionNode, OperationType

if TYPE_CHECKING:
    from fastshaql.core.ir import NodeShapeIR
    from fastshaql.core.registry import ShapeRegistry


def root_field_node(query: str) -> FieldNode:
    """Return the root selection field from a GraphQL query operation."""
    doc = gql_parse(query)
    op = doc.definitions[0]
    if not isinstance(op, OperationDefinitionNode):
        raise TypeError("expected an operation definition")
    if op.operation != OperationType.QUERY:
        raise TypeError("expected a query operation")
    field = op.selection_set.selections[0]
    if not isinstance(field, FieldNode):
        raise TypeError("expected a field selection")
    return field


def shape_for_root_field(registry: ShapeRegistry, field_name: str) -> NodeShapeIR:
    """Resolve the node shape for a root query field name."""
    from fastshaql.core.schema.build import root_field_name

    for shape in registry.shapes:
        if shape.has_target and root_field_name(shape.graphql_type_name) == field_name:
            return shape
    raise ValueError(f"no shape with root field {field_name!r}")
