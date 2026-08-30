"""Literal coercion for filter operator operands."""

from __future__ import annotations

from graphql.language.ast import (
    BooleanValueNode,
    FloatValueNode,
    IntValueNode,
    ListValueNode,
    NullValueNode,
    StringValueNode,
    ValueNode,
)
from rdflib import Literal, URIRef
from rdflib.namespace import XSD

from fastshaql.core.kernel.constants import LANGUAGE_DATATYPES


def compare_datatype(datatype: URIRef | None) -> URIRef | None:
    """Return the XSD datatype used for filter comparisons on *datatype* —
    the language-tagged types compare as plain strings (their ``STR()``-
    wrapped left-hand sides are untagged)."""
    if datatype in LANGUAGE_DATATYPES:
        return XSD.string
    return datatype


def value_to_literal(value: ValueNode, datatype: URIRef | None) -> Literal | None:
    """Coerce a GraphQL value node to an RDFLib ``Literal``, or ``None``."""
    match value:
        case StringValueNode():
            return _literal_value(value.value, datatype or XSD.string)
        case IntValueNode():
            return Literal(int(value.value), datatype=datatype or XSD.integer)
        case FloatValueNode():
            return Literal(float(value.value), datatype=datatype or XSD.float)
        case BooleanValueNode():
            return Literal(bool(value.value), datatype=datatype or XSD.boolean)
        case NullValueNode():
            return None
        case _:  # pragma: no cover — List/Object/Variable unreachable (GraphQL coerces)
            return None


def list_to_literals(
    node: ListValueNode,
    datatype: URIRef | None,
) -> tuple[Literal, ...]:
    """Coerce each element of a GraphQL list value to ``Literal``."""
    literals: list[Literal] = []
    for item in node.values:
        lit = value_to_literal(item, datatype)
        if lit is not None:  # pragma: no branch — NonNull list items never yield None
            literals.append(lit)
    return tuple(literals)


def _literal_value(value: str, datatype: URIRef | None) -> Literal:
    if datatype is None or datatype == XSD.string:
        return Literal(value)
    return Literal(value, datatype=datatype)
