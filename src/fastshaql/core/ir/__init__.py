"""Shape IR — frozen dataclasses mirroring SHACL shapes (parser output)."""

from .base import ShapeIR
from .filter_shape import FilterConstraintIR, FilterShapeIR
from .node_expr import (
    ConstantListNodeExpr,
    ConstantNodeExpr,
    ExistsNodeExpr,
    FilterShapeNodeExpr,
    IfNodeExpr,
    NodeExprIR,
    PathValuesNodeExpr,
    SelectNodeExpr,
    SparqlExprNodeExpr,
    is_multivalued_capable,
)
from .node_shape import NodeShapeIR
from .property_shape import (
    FieldKind,
    LiteralSpace,
    PropertyShapeIR,
    ValueSource,
    ValueType,
)
from .shacl_path import ShaclPropertyPath

__all__ = [
    "ConstantListNodeExpr",
    "ConstantNodeExpr",
    "ExistsNodeExpr",
    "FieldKind",
    "FilterConstraintIR",
    "FilterShapeIR",
    "FilterShapeNodeExpr",
    "IfNodeExpr",
    "LiteralSpace",
    "NodeExprIR",
    "NodeShapeIR",
    "PathValuesNodeExpr",
    "PropertyShapeIR",
    "SelectNodeExpr",
    "ShaclPropertyPath",
    "ShapeIR",
    "SparqlExprNodeExpr",
    "ValueSource",
    "ValueType",
    "is_multivalued_capable",
]
