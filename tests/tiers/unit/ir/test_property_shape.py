"""Property classification — ``core/ir/property_shape.py``.

Unit tier: the two-axis classification (ADR-0004) —
``ValueType`` precedence (relationship > enum > scalar) on the type axis and
``ValueSource`` (asserted | derived) on the source axis, including overlay
interactions; plus the datatype-axis ``LiteralSpace`` classification.

Order: scalar → relationship → enum → derived → overlays → literal space → regression.
"""

from __future__ import annotations

import dataclasses

import pytest
from rdflib import Literal
from rdflib.namespace import RDF, XSD

from fastshaql.core.ir import (
    FieldKind,
    LiteralSpace,
    ValueSource,
    ValueType,
)
from fastshaql.core.ir.node_expr import ConstantNodeExpr
from fastshaql.core.ir.shacl_path import PredicatePath
from fastshaql.core.kernel.constants import DIR_LANG_STRING
from support.builders import (
    EX,
    defaulted_property,
    derived_property,
    enum_property,
    relationship_property,
    scalar_property,
)

_CONST = ConstantNodeExpr(Literal("FastshaqlEMR"))


# --- Pure type-axis arms ---


def test_scalar_classifies_as_scalar() -> None:
    prop = scalar_property("label", min_count=1, max_count=1)
    assert prop.value_type is ValueType.SCALAR
    assert prop.source is ValueSource.ASSERTED


def test_relationship_classifies_as_relationship() -> None:
    prop = relationship_property("author", EX + "AuthorShape", min_count=1, max_count=1)
    assert prop.value_type is ValueType.RELATIONSHIP
    assert prop.source is ValueSource.ASSERTED


def test_enum_classifies_as_enum() -> None:
    prop = enum_property("status", in_values=(Literal("active"), Literal("closed")))
    assert prop.value_type is ValueType.ENUM
    assert prop.source is ValueSource.ASSERTED


def test_derived_scalar_is_derived_source() -> None:
    """A derived scalar is (SCALAR, DERIVED) — the axes are orthogonal."""
    prop = derived_property(
        "recordSource", values_expr=_CONST, min_count=1, max_count=1
    )
    assert prop.value_type is ValueType.SCALAR
    assert prop.source is ValueSource.DERIVED


# --- Overlay precedence (higher type wins) ---


def test_relationship_overlay_in_values_still_relationship() -> None:
    """``sh:in`` on a relationship is the read-ignored overlay — relationship wins."""
    prop = relationship_property("employer", EX + "OrgShape", min_count=1, max_count=1)
    with_overlay = dataclasses.replace(prop, in_values=(EX + "Acme",))
    assert with_overlay.value_type is ValueType.RELATIONSHIP


def test_derived_enum_overlay_is_derived_enum() -> None:
    """``sh:values`` + ``sh:in`` is a derived enum — (ENUM, DERIVED) — absorbed
    by the two-axis design (ADR-0015)."""
    prop = derived_property(
        "category",
        values_expr=_CONST,
        min_count=1,
        max_count=1,
        datatype=XSD.string,
    )
    with_overlay = dataclasses.replace(prop, in_values=(Literal("a"), Literal("b")))
    assert with_overlay.value_type is ValueType.ENUM
    assert with_overlay.source is ValueSource.DERIVED


def test_defaulted_enum_overlay_is_defaulted_enum() -> None:
    """``sh:defaultValue`` + ``sh:in`` keeps the enum type on the asserted
    source (ENUM, ASSERTED) — the default is orthogonal to both axes; the
    fallback flows through enum serialization (ADR-0015)."""
    prop = defaulted_property("grade", default_expr=_CONST, min_count=0, max_count=1)
    with_overlay = dataclasses.replace(prop, in_values=(Literal("a"), Literal("b")))
    assert with_overlay.value_type is ValueType.ENUM
    assert with_overlay.source is ValueSource.ASSERTED
    assert with_overlay.default_expr is not None


def test_path_is_still_required_field() -> None:
    """Regression: ``values_expr`` is kw_only and optional; existing required
    fields (path) still construct normally."""
    prop = derived_property(
        "uriLength", values_expr=_CONST, min_count=0, max_count=1, datatype=XSD.integer
    )
    assert isinstance(prop.path, PredicatePath)
    assert prop.datatype == XSD.integer


# --- FieldKind (nullability home) ---


def test_defaulted_field_is_required_at_any_min_count() -> None:
    """SD-6 lives here, in ``kind`` — the single nullability home: a
    defaulted field is non-null at any ``minCount`` (the ``COALESCE``
    always binds; the schema build just consumes ``kind``)."""
    prop = defaulted_property("source", default_expr=_CONST, min_count=0, max_count=1)
    assert prop.kind is FieldKind.REQUIRED_SCALAR


# --- LiteralSpace (datatype axis) ---


@pytest.mark.parametrize(
    ("datatypes", "expected_space"),
    [
        ((), LiteralSpace.PLAIN),
        ((XSD.string,), LiteralSpace.PLAIN),
        ((XSD.integer,), LiteralSpace.PLAIN),
        ((RDF.langString,), LiteralSpace.LANGUAGE),
        ((DIR_LANG_STRING,), LiteralSpace.LANGUAGE),
        ((RDF.langString, DIR_LANG_STRING), LiteralSpace.LANGUAGE),
        ((XSD.string, RDF.langString), LiteralSpace.UNION),
        ((RDF.langString, XSD.string), LiteralSpace.UNION),
        ((XSD.string, DIR_LANG_STRING, RDF.langString), LiteralSpace.UNION),
    ],
    ids=[
        "empty",
        "string",
        "integer",
        "lang_string",
        "dir_lang_string",
        "language_only_set",
        "union",
        "union_reversed",
        "triple_set",
    ],
)
def test_literal_space_classification(
    datatypes: tuple, expected_space: LiteralSpace
) -> None:
    prop = scalar_property(
        "note", min_count=0, max_count=1, datatype=None, datatypes=datatypes
    )
    assert prop.literal_space is expected_space


def test_derived_datatype_is_sole_element_or_none() -> None:
    singleton = scalar_property("code", min_count=1, max_count=1, datatype=XSD.date)
    assert singleton.datatype == XSD.date
    empty = scalar_property("code", min_count=1, max_count=1, datatype=None)
    assert empty.datatype is None
    union = scalar_property(
        "note",
        min_count=1,
        max_count=1,
        datatype=None,
        datatypes=(XSD.string, RDF.langString),
    )
    assert union.datatype is None


@pytest.mark.parametrize(
    ("datatypes", "expected"),
    [
        ((), False),
        ((XSD.string,), False),
        ((XSD.integer,), False),
        ((RDF.langString,), True),
        ((RDF.langString, DIR_LANG_STRING), True),
        ((XSD.string, RDF.langString), True),
    ],
    ids=["empty", "string", "integer", "language", "language_set", "union"],
)
def test_is_language_typed_accepts_tagged_values(
    datatypes: tuple, expected: bool
) -> None:
    """The predicate is "the Property accepts language-tagged values" —
    LANGUAGE and UNION qualify, PLAIN never does."""
    prop = scalar_property(
        "note", min_count=0, max_count=1, datatype=None, datatypes=datatypes
    )
    assert prop.is_language_typed is expected


@pytest.mark.parametrize(
    "datatypes",
    [
        (RDF.langString, XSD.integer),
        (RDF.langString, XSD.string, XSD.integer),
    ],
    ids=["language_plus_non_string", "union_plus_non_string"],
)
def test_literal_space_rejects_language_plus_non_string(datatypes: tuple) -> None:
    """A set mixing a language type with a non-string non-language type is
    outside the parser's universe — direct construction fails loudly here
    rather than misclassifying (the union-plus-non-string row pins that
    *every* non-language member must be ``xsd:string``, not just one)."""
    prop = scalar_property(
        "note",
        min_count=0,
        max_count=1,
        datatype=None,
        datatypes=datatypes,
    )
    with pytest.raises(ValueError, match="non-string datatypes"):
        _ = prop.literal_space


def test_builders_reject_datatype_and_datatypes_together() -> None:
    """The builders seam mirrors parser rule 4 — both forms at once is
    ambiguous."""
    with pytest.raises(ValueError, match="not both"):
        scalar_property(
            "note",
            min_count=0,
            max_count=1,
            datatype=XSD.string,
            datatypes=(XSD.string, RDF.langString),
        )
