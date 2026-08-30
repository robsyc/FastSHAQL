"""Operator and IRI filter emission into the expression AST (SPARQL §17.3).

See: https://www.w3.org/TR/sparql12-query/#expressions
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.language.ast import (
    EnumValueNode,
    ListValueNode,
    ObjectFieldNode,
    ObjectValueNode,
    StringValueNode,
    ValueNode,
)
from rdflib import Literal, URIRef, Variable
from rdflib.namespace import XSD

from fastshaql.core.ir import PropertyShapeIR, ValueType
from fastshaql.core.kernel.operators import (
    COMPARE_OPS,
    MEMBERSHIP_OPS,
    STRING_FUNCTIONS,
)
from fastshaql.core.sparql import (
    AndExpr,
    CompareExpr,
    Expression,
    FunctionCall,
    InExpr,
    NotExpr,
    OrExpr,
    TermExpr,
)

from .literals import compare_datatype, list_to_literals, value_to_literal

if TYPE_CHECKING:
    from collections.abc import Callable


def _fold(
    cls: type[AndExpr] | type[OrExpr], parts: list[Expression]
) -> Expression | None:
    """Fold a list of expressions into *cls*, or return the sole child."""
    if not parts:
        return None
    if len(parts) == 1:
        return parts[0]
    return cls(tuple(parts))


def combine_and(parts: list[Expression]) -> Expression | None:
    """Fold a list of expressions into ``AndExpr``, or return the sole child."""
    return _fold(AndExpr, parts)


def combine_or(parts: list[Expression]) -> Expression | None:
    """Fold a list of expressions into ``OrExpr``, or return the sole child."""
    return _fold(OrExpr, parts)


def _compare_op(op_name: str, lhs: Expression, right: TermExpr) -> CompareExpr:
    """Emit a comparison of *lhs* against a resolved right-hand term."""
    return CompareExpr(op=COMPARE_OPS[op_name], left=lhs, right=right)


def _membership_op(
    op_name: str, lhs: Expression, values: tuple[URIRef | Literal, ...]
) -> Expression | None:
    """Emit an ``IN`` test (negated for ``notIn``); ``None`` when *values* is empty."""
    if not values:
        return None
    in_expr = InExpr(lhs, values)
    if op_name == "notIn":
        return NotExpr(in_expr)
    return in_expr


def filter_lhs(prop: PropertyShapeIR, var: Variable) -> Expression:
    """Left-hand side for filter comparisons — the resolved variable
    post-``BIND`` under a chain, ``STR()``-wrapped for language-typed or
    union properties (values that may be tagged; plain values pass through
    ``STR`` unchanged)."""
    if prop.is_language_typed:
        return FunctionCall("STR", (TermExpr(var),))
    return TermExpr(var)


def translate_scalar_ops(
    node: ValueNode,
    prop: PropertyShapeIR,
    var: Variable,
    *,
    lhs: Expression | None = None,
) -> Expression | None:
    """Translate a scalar operator input object into an expression AST node."""
    if not isinstance(node, ObjectValueNode):
        return None
    resolved_lhs = lhs if lhs is not None else filter_lhs(prop, var)
    if prop.value_type is ValueType.ENUM:
        return _translate_operator_fields(
            node.fields,
            lambda op_field: translate_enum_operator_field(
                op_field, prop, resolved_lhs
            ),
        )
    return translate_operator_object(
        node,
        resolved_lhs,
        datatype=prop.datatype,
        iri_values=False,
    )


def translate_enum_operator_field(
    op_field: ObjectFieldNode,
    prop: PropertyShapeIR,
    lhs: Expression,
) -> Expression | None:
    """Translate one operator field on an enum filter object."""
    op_name = op_field.name.value
    if op_name in COMPARE_OPS:
        term = _enum_term(op_field.value, prop)
        if term is None:
            return None
        return _compare_op(op_name, lhs, TermExpr(term))
    if op_name in MEMBERSHIP_OPS:
        return _membership_op(
            op_name, lhs, _enum_membership_values(op_field.value, prop)
        )
    return None  # pragma: no cover — enum filter types carry only eq/neq/in/notIn


def _enum_term(value: ValueNode, prop: PropertyShapeIR) -> URIRef | Literal | None:
    """Recover the rdflib term for an enum value node (NAME → term)."""
    if not isinstance(value, EnumValueNode):
        return None
    term = prop.enum_term_by_name.get(value.value)
    if term is None or not isinstance(term, (URIRef, Literal)):
        return None  # pragma: no cover — validated enum names always resolve to URIRef/Literal
    return term


def _enum_membership_values(
    value: ValueNode,
    prop: PropertyShapeIR,
) -> tuple[URIRef | Literal, ...]:
    if not isinstance(value, ListValueNode):
        return ()
    terms: list[URIRef | Literal] = []
    for item in value.values:
        term = _enum_term(item, prop)
        if (
            term is not None
        ):  # pragma: no branch — NonNull enum list items always resolve to a term
            terms.append(term)
    return tuple(terms)


def translate_iri_filter(node: ValueNode, subject: Variable) -> Expression | None:
    """Translate an ``IriFilter`` object against the subject variable."""
    if not isinstance(node, ObjectValueNode):
        return None
    return translate_operator_object(
        node,
        TermExpr(subject),
        datatype=None,
        iri_values=True,
    )


def translate_operator_object(
    node: ObjectValueNode,
    lhs: Expression,
    *,
    datatype: URIRef | None,
    iri_values: bool,
) -> Expression | None:
    """Translate one operator input object; AND-combine set operator fields."""
    return _translate_operator_fields(
        node.fields,
        lambda op_field: translate_operator_field(
            op_field,
            lhs,
            datatype=datatype,
            iri_values=iri_values,
        ),
    )


def _translate_operator_fields(
    fields: tuple[ObjectFieldNode, ...],
    translate_field: Callable[[ObjectFieldNode], Expression | None],
) -> Expression | None:
    """AND-combine expressions emitted from operator input object fields."""
    parts: list[Expression] = []
    for op_field in fields:
        expr = translate_field(op_field)
        if expr is not None:
            parts.append(expr)
    return combine_and(parts)


def translate_operator_field(
    op_field: ObjectFieldNode,
    lhs: Expression,
    *,
    datatype: URIRef | None,
    iri_values: bool,
) -> Expression | None:
    """Translate one operator field (compare, string function, or membership)."""
    op_name = op_field.name.value
    if op_name in COMPARE_OPS:
        rhs_term = _compare_rhs(op_field.value, datatype, iri_values=iri_values)
        if rhs_term is None:
            return None
        return _compare_op(op_name, lhs, rhs_term)
    if op_name in STRING_FUNCTIONS:
        literal = value_to_literal(op_field.value, XSD.string)
        if literal is None:
            return None
        string_lhs = FunctionCall("STR", (lhs,)) if iri_values else lhs
        return FunctionCall(STRING_FUNCTIONS[op_name], (string_lhs, TermExpr(literal)))
    if op_name in MEMBERSHIP_OPS:
        return _membership_op(
            op_name,
            lhs,
            _membership_values(op_field.value, datatype, iri_values=iri_values),
        )
    return None  # pragma: no cover — schema only emits known operator names


def _compare_rhs(
    value: ValueNode,
    datatype: URIRef | None,
    *,
    iri_values: bool,
) -> TermExpr | None:
    if iri_values:
        if not isinstance(value, StringValueNode):
            return None
        return TermExpr(URIRef(value.value))
    literal = value_to_literal(value, compare_datatype(datatype))
    if literal is None:
        return None
    return TermExpr(literal)


def _membership_values(
    value: ValueNode,
    datatype: URIRef | None,
    *,
    iri_values: bool,
) -> tuple[URIRef | Literal, ...]:
    if not isinstance(value, ListValueNode):
        return ()
    if iri_values:
        return tuple(
            URIRef(item.value)
            for item in value.values
            if isinstance(item, StringValueNode)
        )
    return list_to_literals(value, datatype)
