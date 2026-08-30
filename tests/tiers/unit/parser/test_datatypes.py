"""Datatype-set parsing — ``sh:datatype`` IRI/list forms and datatype-only
``sh:or`` in ``core/parser/property_shape.py``.

Unit tier: rules 1-6 of the union recognition (SHACL Core §7.1.2, §7.7.3) —
both union syntaxes normalize into one ``datatypes`` tuple, non-datatype
``sh:or`` is parse-recognized-and-inert, and ambiguous or non-string-family
declarations reject loudly.

Order: IRI form → list form → sh:or form → inert lane → loud rejections → boundary checks.
"""

from __future__ import annotations

import pytest
from rdflib import Graph
from rdflib.namespace import RDF, XSD

from fastshaql.core.ir import LiteralSpace
from fastshaql.core.kernel.constants import DIR_LANG_STRING
from fastshaql.core.parser import parse_shapes
from fastshaql.core.parser.errors import UnsupportedShapeError

_PREFIXES = """
@prefix ex: <http://example.org/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
"""


def _parse_property(prop_body: str, *, field: str = "note"):
    graph = Graph()
    graph.parse(
        data=f"""{_PREFIXES}
ex:PersonShape a sh:NodeShape ;
    sh:codeIdentifier "Person" ;
    sh:targetClass ex:Person ;
    sh:property [
        sh:path ex:{field} ;
        {prop_body}
    ] .
""",
        format="turtle",
    )
    registry = parse_shapes(graph)
    return registry.by_type_name["Person"].property_shapes[field]


# --- Rule 1: the IRI form (today's behavior) ---


def test_datatype_iri_form_yields_singleton() -> None:
    prop = _parse_property("sh:datatype xsd:string ;")
    assert prop.datatypes == (XSD.string,)
    assert prop.literal_space is LiteralSpace.PLAIN


def test_singleton_outside_string_family_parses_normally() -> None:
    """Rule 6 binds multi-entry sets only — a lone ``xsd:integer`` is a
    normal scalar (any IRI datatype parses)."""
    prop = _parse_property("sh:datatype xsd:date ;")
    assert prop.datatypes == (XSD.date,)
    assert prop.literal_space is LiteralSpace.PLAIN


# --- Rule 2: the SHACL-list form ---


def test_datatype_list_form_yields_union() -> None:
    prop = _parse_property("sh:datatype ( xsd:string rdf:langString ) ;")
    assert prop.datatypes == (XSD.string, RDF.langString)
    assert prop.literal_space is LiteralSpace.UNION


def test_singleton_list_form_parses() -> None:
    """``sh:datatype ( xsd:string )`` — the degenerate list is the plain
    singleton."""
    prop = _parse_property("sh:datatype ( xsd:string ) ;")
    assert prop.datatypes == (XSD.string,)
    assert prop.literal_space is LiteralSpace.PLAIN


def test_triple_datatype_set_is_union() -> None:
    """The spec's triple example — string plus both language-tagged types."""
    prop = _parse_property(
        "sh:datatype ( xsd:string rdf:dirLangString rdf:langString ) ;"
    )
    assert prop.datatypes == (XSD.string, DIR_LANG_STRING, RDF.langString)
    assert prop.literal_space is LiteralSpace.UNION


def test_language_only_list_is_language_space() -> None:
    prop = _parse_property("sh:datatype ( rdf:langString rdf:dirLangString ) ;")
    assert prop.literal_space is LiteralSpace.LANGUAGE


def test_duplicate_list_members_dedupe() -> None:
    prop = _parse_property("sh:datatype ( xsd:string xsd:string rdf:langString ) ;")
    assert prop.datatypes == (XSD.string, RDF.langString)


# --- Rule 3: the sh:or form ---


def test_sh_or_datatype_only_yields_union() -> None:
    prop = _parse_property(
        "sh:or ( [ sh:datatype xsd:string ] [ sh:datatype rdf:langString ] ) ;"
    )
    assert prop.datatypes == (XSD.string, RDF.langString)
    assert prop.literal_space is LiteralSpace.UNION


def test_both_union_syntaxes_normalize_identically() -> None:
    """``sh:datatype ( xsd:string rdf:langString )`` ≡ the ``sh:or`` form —
    one IR, one literal space."""
    list_form = _parse_property("sh:datatype ( xsd:string rdf:langString ) ;")
    or_form = _parse_property(
        "sh:or ( [ sh:datatype xsd:string ] [ sh:datatype rdf:langString ] ) ;"
    )
    assert list_form.datatypes == or_form.datatypes
    assert list_form.literal_space == or_form.literal_space


# --- Rule 3, inert lane: any other sh:or ---


def test_sh_or_with_extra_parameters_warns_and_is_inert(
    caplog: pytest.LogCaptureFixture,
) -> None:
    prop = _parse_property(
        "sh:or ( [ sh:datatype xsd:string ; sh:minCount 1 ] "
        "[ sh:datatype rdf:langString ] ) ;"
    )
    assert prop.datatypes == ()
    assert prop.literal_space is LiteralSpace.PLAIN
    inert = [r for r in caplog.records if "non-datatype constraints" in r.message]
    assert len(inert) == 1


def test_sh_or_with_literal_member_is_inert() -> None:
    prop = _parse_property('sh:or ( "plain" [ sh:datatype rdf:langString ] ) ;')
    assert prop.datatypes == ()


def test_sh_or_member_with_type_annotation_is_inert() -> None:
    """The recognized member's predicate set is exactly ``{sh:datatype}`` —
    even an ``a sh:NodeShape`` annotation routes to the inert lane."""
    prop = _parse_property("sh:or ( [ a sh:NodeShape ; sh:datatype xsd:string ] ) ;")
    assert prop.datatypes == ()


def test_empty_sh_or_list_is_inert() -> None:
    prop = _parse_property("sh:or ( ) ;")
    assert prop.datatypes == ()


def test_sh_or_member_with_two_datatypes_is_inert() -> None:
    """A member carrying two ``sh:datatype`` values is not "a single
    ``sh:datatype`` IRI" — inert lane."""
    prop = _parse_property("sh:or ( [ sh:datatype xsd:string, rdf:langString ] ) ;")
    assert prop.datatypes == ()


def test_sh_or_member_with_literal_datatype_is_inert() -> None:
    """A member whose sole ``sh:datatype`` object is not an IRI — inert lane."""
    prop = _parse_property('sh:or ( [ sh:datatype "plain" ] ) ;')
    assert prop.datatypes == ()


# --- Rules 4/5: ambiguity rejects loudly ---


def test_datatype_and_sh_or_together_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="sh:datatype and sh:or together"):
        _parse_property(
            "sh:datatype xsd:string ; sh:or ( [ sh:datatype rdf:langString ] ) ;"
        )


def test_multiple_sh_or_values_raise() -> None:
    with pytest.raises(UnsupportedShapeError, match="multiple sh:or values"):
        _parse_property(
            "sh:or ( [ sh:datatype xsd:string ] ) ;"
            " sh:or ( [ sh:datatype rdf:langString ] ) ;"
        )


def test_multiple_sh_datatype_values_raise() -> None:
    with pytest.raises(UnsupportedShapeError, match="multiple sh:datatype values"):
        _parse_property("sh:datatype xsd:string, rdf:langString ;")


# --- Rule 6: the recognition universe for multi-entry sets ---


def test_non_string_family_list_raises_naming_supported_members() -> None:
    with pytest.raises(UnsupportedShapeError) as excinfo:
        _parse_property("sh:datatype ( xsd:string xsd:integer ) ;")
    message = str(excinfo.value)
    assert "string family" in message
    assert "xsd:string" in message
    assert "rdf:langString" in message
    assert "rdf:dirLangString" in message
    assert str(XSD.integer) in message  # the offending member, by full IRI


def test_non_string_family_sh_or_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="string family"):
        _parse_property(
            "sh:or ( [ sh:datatype xsd:string ] [ sh:datatype xsd:integer ] ) ;"
        )


# --- Malformed declarations ---


def test_malformed_datatype_list_raises() -> None:
    """The strict-RDF-list walk rejects a cons cell with two ``rdf:first``."""
    graph = Graph()
    graph.parse(
        data=f"""{_PREFIXES}
ex:PersonShape a sh:NodeShape ;
    sh:codeIdentifier "Person" ;
    sh:targetClass ex:Person ;
    sh:property [
        sh:path ex:note ;
        sh:datatype _:head
    ] .
_:head rdf:first xsd:string, rdf:langString ;
    rdf:rest rdf:nil .
""",
        format="turtle",
    )
    with pytest.raises(UnsupportedShapeError, match="well-formed SHACL list"):
        parse_shapes(graph)


def test_datatype_list_with_non_iri_member_raises() -> None:
    with pytest.raises(UnsupportedShapeError, match="must be IRIs"):
        _parse_property('sh:datatype ( xsd:string "plain" ) ;')


def test_empty_datatype_list_raises() -> None:
    """``sh:datatype ( )`` — Turtle's empty list *is* the IRI ``rdf.nil``,
    which would otherwise flow into the IR as a nonsense datatype."""
    with pytest.raises(UnsupportedShapeError, match="sh:datatype list is empty"):
        _parse_property("sh:datatype ( ) ;")


# --- Derived/default boundary checks accept union sets ---


def test_derived_field_with_union_datatypes_parses() -> None:
    """A union satisfies the ``sh:values`` boundary — a derived field may
    carry tagged values (the chain lowering covers it)."""
    prop = _parse_property(
        "sh:datatype ( xsd:string rdf:langString ) ;"
        " sh:values [ shnex:pathValues ( ex:source ) ] ;",
    )
    assert prop.datatypes == (XSD.string, RDF.langString)
    assert prop.source is not None


def test_defaulted_field_with_union_datatypes_parses() -> None:
    prop = _parse_property(
        "sh:datatype ( xsd:string rdf:langString ) ;"
        ' sh:defaultValue "n/a" ; sh:maxCount 1 ;'
    )
    assert prop.datatypes == (XSD.string, RDF.langString)
    assert prop.default_expr is not None
