"""Shared helpers for converter unit tests."""

from __future__ import annotations

from rdflib import URIRef, Variable

from fastshaql.core.registry import ShapeRegistry
from fastshaql.core.translation.variables import VariableMap

ALICE = URIRef("http://example.org/alice")
BOB = URIRef("http://example.org/bob")
CAROL = URIRef("http://example.org/carol")
ACME = URIRef("http://example.org/acme")
GLOBEX = URIRef("http://example.org/globex")
AMSTERDAM = URIRef("http://example.org/amsterdam")
BERLIN = URIRef("http://example.org/berlin")


def empty_registry() -> ShapeRegistry:
    return ShapeRegistry(())


def flat_var_map(**fields: str) -> VariableMap:
    return VariableMap(
        subject_var=Variable("iri"),
        fields={name: Variable(var) for name, var in fields.items()},
        relationships={},
    )


def nested_converter_case(
    *,
    relationship: str,
    child_fields: tuple[str, ...] = ("name",),
    nested: str | None = None,
    nested_fields: tuple[str, ...] = ("name",),
    root_fields: tuple[str, ...] = ("name",),
) -> VariableMap:
    """Build a nested ``VariableMap`` for converter relationship tests.

    Constructs the common ``root{root_fields} → relationship → child{child_fields}``
    variable map shared across the converter-relationship unit tests, with an
    optional second nesting level (``nested``). Variable names follow the
    ``VariableAllocator`` prefix convention: the root subject is ``iri`` and each
    relationship level prefixes its variables with the accumulated name chain
    (e.g. ``employer_iri``, ``employer_locatedIn_name``), so the returned map is
    interchangeable with one produced by ``translate_query``.

    The keyword-only parameters mirror the parts that vary between tests: which
    relationship name is traversed, which scalar fields each level projects, and
    whether a second relationship is nested below the first.
    """
    if nested is None:
        child = VariableMap(
            subject_var=Variable(f"{relationship}_iri"),
            fields={name: Variable(f"{relationship}_{name}") for name in child_fields},
            relationships={},
        )
    else:
        grand_prefix = f"{relationship}_{nested}"
        child = VariableMap(
            subject_var=Variable(f"{relationship}_iri"),
            fields={name: Variable(f"{relationship}_{name}") for name in child_fields},
            relationships={
                nested: (
                    Variable(f"{grand_prefix}_iri"),
                    VariableMap(
                        subject_var=Variable(f"{grand_prefix}_iri"),
                        fields={
                            name: Variable(f"{grand_prefix}_{name}")
                            for name in nested_fields
                        },
                        relationships={},
                    ),
                ),
            },
        )
    return VariableMap(
        subject_var=Variable("iri"),
        fields={name: Variable(name) for name in root_fields},
        relationships={
            relationship: (Variable(f"{relationship}_iri"), child),
        },
    )
