"""XSD datatype → graphql-core scalar mapping.

See:
- https://www.w3.org/TR/shacl12-core/#constraints-datatype
- https://spec.graphql.org/October2021/#sec-Scalars
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from rdflib import RDF, XSD, URIRef

from fastshaql.core.ir import LiteralSpace

from ._gql import BOOLEAN, FLOAT, ID, INT, STRING

if TYPE_CHECKING:
    from graphql.type import (
        GraphQLScalarType,
    )

    from fastshaql.core.ir import PropertyShapeIR
    from fastshaql.core.kernel.operators import OperatorInputName

DatatypeCategory = Literal["string", "integer", "decimal", "boolean", "datetime"]

DEFAULT_DATATYPE_CATEGORY: DatatypeCategory = "string"

# Single source of truth: XSD IRI → output scalar + filter operator category (ADR-0009).
_DATATYPE_ENTRIES: list[tuple[URIRef, GraphQLScalarType, DatatypeCategory]] = [
    # String family
    (XSD.string, STRING, "string"),
    (XSD.normalizedString, STRING, "string"),
    (XSD.token, STRING, "string"),
    (XSD.anyURI, STRING, "string"),
    (RDF.langString, STRING, "string"),
    # Boolean
    (XSD.boolean, BOOLEAN, "boolean"),
    # Integer family
    (XSD.integer, INT, "integer"),
    (XSD.int, INT, "integer"),
    (XSD.short, INT, "integer"),
    (XSD.byte, INT, "integer"),
    (XSD.long, INT, "integer"),
    (XSD.unsignedInt, INT, "integer"),
    # Decimal family
    (XSD.decimal, FLOAT, "decimal"),
    (XSD.float, FLOAT, "decimal"),
    (XSD.double, FLOAT, "decimal"),
    # Date/time and duration (filter as DateTimeFilter; output as String)
    (XSD.date, STRING, "datetime"),
    (XSD.dateTime, STRING, "datetime"),
    (XSD.time, STRING, "datetime"),
    (XSD.dateTimeStamp, STRING, "datetime"),
    (XSD.duration, STRING, "datetime"),
    (XSD.dayTimeDuration, STRING, "datetime"),
    (XSD.yearMonthDuration, STRING, "datetime"),
    (XSD.gYear, STRING, "datetime"),
]

DATATYPE_MAP: dict[URIRef, GraphQLScalarType] = {
    iri: scalar for iri, scalar, _ in _DATATYPE_ENTRIES
}
DATATYPE_CATEGORIES: dict[URIRef, DatatypeCategory] = {
    iri: category for iri, _, category in _DATATYPE_ENTRIES
}

FILTER_OPERATOR_BY_CATEGORY: dict[DatatypeCategory, OperatorInputName] = {
    "string": "StringFilter",
    "integer": "IntFilter",
    "decimal": "FloatFilter",
    "boolean": "BooleanFilter",
    "datetime": "DateTimeFilter",
}

_GRAPHQL_SCALAR_BY_FILTER: dict[OperatorInputName, GraphQLScalarType] = {
    "StringFilter": STRING,
    "IntFilter": INT,
    "FloatFilter": FLOAT,
    "BooleanFilter": BOOLEAN,
    "DateTimeFilter": STRING,
    "IriFilter": ID,
}


def filter_operator_for_category(category: DatatypeCategory) -> OperatorInputName:
    """Map a datatype category to its singleton operator input type name."""
    return FILTER_OPERATOR_BY_CATEGORY[category]


def graphql_scalar_for_filter(name: OperatorInputName) -> GraphQLScalarType:
    """Return the GraphQL scalar used for operator fields on *name*."""
    return _GRAPHQL_SCALAR_BY_FILTER[name]


def datatype_category(datatype: URIRef | None) -> DatatypeCategory:
    """Map ``sh:datatype`` to a filter operator category.

    Unknown or missing datatypes fall back to ``string`` (``StringFilter``).
    """
    if datatype is None:
        return DEFAULT_DATATYPE_CATEGORY
    return DATATYPE_CATEGORIES.get(datatype, DEFAULT_DATATYPE_CATEGORY)


def resolve_scalar_type(datatype: URIRef | None) -> GraphQLScalarType:
    """Map ``sh:datatype`` to a GraphQL output scalar.

    Unknown datatypes fall back to ``String``.
    """
    if datatype is None:
        return STRING
    return DATATYPE_MAP.get(datatype, STRING)


def scalar_type_for_space(prop: PropertyShapeIR) -> GraphQLScalarType:
    """Output scalar for a scalar Property, dispatched on the literal space:
    UNION maps to ``String`` by declared branch; PLAIN and LANGUAGE resolve
    via their first datatype (``String`` when none is declared)."""
    if prop.literal_space is LiteralSpace.UNION:
        return STRING
    return resolve_scalar_type(prop.datatypes[0] if prop.datatypes else None)


def filter_category_for_space(prop: PropertyShapeIR) -> DatatypeCategory:
    """Filter operator category for a scalar Property's literal space: the
    string-union space maps to ``"string"`` (``StringFilter``) by declared
    branch — the operators are valid across both lexical forms
    (``STR()``-wrapped left-hand sides, ADR-0009/0017); PLAIN and LANGUAGE
    resolve via their first datatype."""
    if prop.literal_space is LiteralSpace.UNION:
        return "string"
    return datatype_category(prop.datatypes[0] if prop.datatypes else None)
