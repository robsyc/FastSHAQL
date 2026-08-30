"""Shared filter operator registry for schema generation and SPARQL translation.

Operator names and SPARQL mappings are defined once here and consumed by
:mod:`fastshaql.core.schema.filters` (GraphQL input types) and
:mod:`fastshaql.core.translation.filters` (expression AST emission).

See ADR-0009 and SPARQL 1.2 §17.3-17.4.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal

if TYPE_CHECKING:
    from fastshaql.core.sparql.expressions import ComparisonOp

OperatorInputName = Literal[
    "StringFilter",
    "IntFilter",
    "FloatFilter",
    "BooleanFilter",
    "DateTimeFilter",
    "IriFilter",
]

EQUALITY_OPS: Final = ("eq", "neq")
ORDERING_OPS: Final = ("gt", "gte", "lt", "lte")
MEMBERSHIP_OPS: Final = ("in", "notIn")
STRING_PATTERN_OPS: Final = ("contains", "startsWith", "endsWith", "regex")

COMPARE_OPS: Final[dict[str, ComparisonOp]] = {
    "eq": "=",
    "neq": "!=",
    "gt": ">",
    "gte": ">=",
    "lt": "<",
    "lte": "<=",
}

STRING_FUNCTIONS: Final[dict[str, str]] = {
    "contains": "CONTAINS",
    "startsWith": "STRSTARTS",
    "endsWith": "STRENDS",
    "regex": "REGEX",
}


@dataclass(frozen=True, slots=True)
class OperatorInputSpec:
    """GraphQL operator-input type capabilities."""

    graphql_name: OperatorInputName
    """The GraphQL input type name (e.g. ``StringFilter``)."""
    ordering: bool = False
    """Whether ordering operators (``gt``/``gte``/``lt``/``lte``) are exposed."""
    membership: bool = False
    """Whether membership operators (``in``/``notIn``) are exposed."""
    string_patterns: bool = False
    """Whether string-pattern operators (``contains``/``startsWith``/...) are exposed."""


OPERATOR_INPUT_SPECS: Final[dict[OperatorInputName, OperatorInputSpec]] = {
    "StringFilter": OperatorInputSpec(
        "StringFilter", membership=True, string_patterns=True
    ),
    "IntFilter": OperatorInputSpec("IntFilter", ordering=True, membership=True),
    "FloatFilter": OperatorInputSpec("FloatFilter", ordering=True, membership=True),
    "BooleanFilter": OperatorInputSpec("BooleanFilter"),
    "DateTimeFilter": OperatorInputSpec(
        "DateTimeFilter", ordering=True, membership=True
    ),
    "IriFilter": OperatorInputSpec("IriFilter", membership=True, string_patterns=True),
}


def operator_field_names(spec: OperatorInputSpec) -> frozenset[str]:
    """Return GraphQL field names exposed by an operator input type."""
    names = set(EQUALITY_OPS)
    if spec.ordering:
        names.update(ORDERING_OPS)
    if spec.membership:
        names.update(MEMBERSHIP_OPS)
    if spec.string_patterns:
        names.update(STRING_PATTERN_OPS)
    return frozenset(names)
