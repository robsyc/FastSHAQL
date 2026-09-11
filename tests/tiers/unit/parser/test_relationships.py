"""Relationship property resolution — sh:class/sh:node targeting (ADR-0025).

Tests resolve relationship properties into value shapes: ``sh:class`` and
``sh:node`` target resolution with auto-typing, synthetic shapes for
untargeted classes (and the cache deduplicating them), loud rejections of
unsupported ``sh:node``/``sh:class`` forms, and derived relationships
without a datatype.

Order: relationship resolution → targeting model → synthetic-shape cache → unsupported forms → derived relationships.
"""

from __future__ import annotations

import pytest
from rdflib import Graph, URIRef

from fastshaql.core.ir import ValueType
from fastshaql.core.parser import parse_shapes
from fastshaql.core.parser.errors import UnsupportedShapeError
from support.builders import EX


def _shapes_graph(turtle: str) -> Graph:
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    return graph


# --- Relationships ---


def test_parse_sh_class_resolves_value_shape(relationship_shapes_graph: Graph) -> None:
    registry = parse_shapes(relationship_shapes_graph)
    person = registry.by_type_name["Person"]
    employer = person.property_shapes["employer"]

    assert employer.value_classes == (EX + "Company",)
    assert employer.value_shape_iri == EX + "CompanyShape"
    assert registry.by_iri[EX + "CompanyShape"].graphql_type_name == "Company"
    assert employer.value_type is ValueType.RELATIONSHIP
    assert employer.datatype is None


def test_parse_sh_node_resolves_value_shape_by_iri(
    relationship_shapes_graph: Graph,
) -> None:
    registry = parse_shapes(relationship_shapes_graph)
    person = registry.by_type_name["Person"]
    address = person.property_shapes["address"]

    # Auto-typed (ADR-0025): the class-indexed target's class materializes
    assert address.value_classes == (EX + "Address",)
    assert address.value_shape_iri == EX + "AddressShape"
    assert registry.by_iri[EX + "AddressShape"].graphql_type_name == "Address"


def test_parse_sh_class_creates_synthetic_shape_when_no_target(
    relationship_shapes_graph: Graph,
    caplog: pytest.LogCaptureFixture,
) -> None:
    registry = parse_shapes(relationship_shapes_graph)
    person = registry.by_type_name["Person"]
    department = person.property_shapes["department"]

    assert department.value_classes == (EX + "Department",)
    synthetic_iri = URIRef("urn:fastshaql:synthetic:Department")
    assert department.value_shape_iri == synthetic_iri
    synthetic = registry.by_iri[synthetic_iri]
    assert synthetic.target_class is None
    assert synthetic.property_shapes == {}
    assert registry.by_type_name["Department"] is synthetic
    warnings = [r for r in caplog.records if "No shape targets class" in r.message]
    assert len(warnings) == 1
    # The warning names both the untargeted class and the synthetic shape it
    # produced — the author's pointer from problem to remedy.
    message = warnings[0].getMessage()
    assert message.startswith("No shape targets class ")
    assert f"{EX}Department" in message
    assert "urn:fastshaql:synthetic:Department" in message


# --- Relationship targeting model (ADR-0025) ---


def _targeting_graph(person_prop_body: str, *, address_targeted: bool = True) -> Graph:
    """A Person shape whose ``note`` property carries *person_prop_body*,
    beside an ``AddressShape`` that is ``sh:targetClass``-indexed (or not)."""
    address_target = "sh:targetClass ex:Address ;" if address_targeted else ""
    return _shapes_graph(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:AddressShape a sh:NodeShape ;
            sh:codeIdentifier "Address" ;
            {address_target}
            sh:property [
                sh:path ex:street ;
                sh:datatype xsd:string ;
                sh:minCount 1 ;
                sh:maxCount 1
            ] .
        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:note ;
                {person_prop_body}
            ] .
        """
    )


def _named_props_graph(refs: str, defs: str) -> Graph:
    """A Person shape whose property shapes are named — rejection and warning
    messages carry their IRIs."""
    return _shapes_graph(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property {refs} .
        {defs}
        """
    )


def test_sh_node_to_classless_shape_stays_untyped() -> None:
    """ADR-0025's class-less exemption: a ``sh:node`` link to a class-less
    shape emits no typing — the target is structural, not class-indexed."""
    registry = parse_shapes(
        _targeting_graph("sh:node ex:AddressShape ;", address_targeted=False)
    )
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_shape_iri == EX + "AddressShape"
    assert note.value_classes == ()


def test_sh_node_with_sh_class_keeps_node_target_and_declared_typing() -> None:
    """ADR-0025: ``sh:node`` names the target; declared classes replace
    the implicit auto-typing."""
    registry = parse_shapes(
        _targeting_graph("sh:node ex:AddressShape ; sh:class ex:Verified ;")
    )
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_shape_iri == EX + "AddressShape"
    assert note.value_classes == (EX + "Verified",)


def test_multiple_sh_classes_with_node_conjoin_iri_sorted() -> None:
    """ADR-0025 conjunction: several ``sh:class`` values beside ``sh:node``
    all bind — IRI-sorted for deterministic emission."""
    registry = parse_shapes(
        _targeting_graph("sh:node ex:AddressShape ; sh:class ex:Zeta , ex:Alpha ;")
    )
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_classes == (EX + "Alpha", EX + "Zeta")


def test_sh_and_class_members_conjoin_with_flat_classes() -> None:
    """Class-only ``sh:and`` members conjoin with flat ``sh:class`` values
    (§7.7.2 as §3.1.1) — merged, deduped, IRI-sorted."""
    registry = parse_shapes(
        _targeting_graph(
            "sh:node ex:AddressShape ;"
            " sh:class ex:Zeta ;"
            " sh:and ( [ sh:class ex:Alpha ] [ sh:class ex:Zeta ] ) ;"
        )
    )
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_classes == (EX + "Alpha", EX + "Zeta")


def test_sh_and_single_class_member_resolves_target() -> None:
    """A lone class-only ``sh:and`` member behaves as a sole ``sh:class`` —
    the target resolves through the class index."""
    registry = parse_shapes(_targeting_graph("sh:and ( [ sh:class ex:Address ] ) ;"))
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_classes == (EX + "Address",)
    assert note.value_shape_iri == EX + "AddressShape"


def test_sh_and_with_other_constraints_is_inert_with_warning(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A member beyond ``sh:class`` warns and voids the whole ``sh:and`` —
    consuming its class slice alone would loosen the constraint."""
    registry = parse_shapes(
        _named_props_graph(
            "ex:NoteProp",
            """
            ex:NoteProp a sh:PropertyShape ;
                sh:path ex:note ;
                sh:node ex:AddressShape ;
                sh:and ( [ sh:class ex:Verified ; sh:pattern "^x" ] ) .
            ex:AddressShape a sh:NodeShape ;
                sh:codeIdentifier "Address" ;
                sh:targetClass ex:Address ;
                sh:property [
                    sh:path ex:street ;
                    sh:datatype xsd:string ;
                    sh:minCount 1 ;
                    sh:maxCount 1
                ] .
            """,
        )
    )
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_classes == (EX + "Address",)
    warnings = [r for r in caplog.records if "sh:and" in r.getMessage()]
    assert len(warnings) == 1
    assert warnings[0].getMessage() == (
        f"sh:and on {EX}NoteProp carries members beyond sh:class — "
        "validator-only, ignored for reads"
    )


def test_sh_and_classes_are_scoped_to_the_property() -> None:
    """The ``sh:and`` lane reads only its own members — a neighbouring
    property's ``sh:class`` stays out of the conjunction."""
    registry = parse_shapes(
        _named_props_graph(
            "ex:NoteProp , ex:DeptProp",
            """
            ex:NoteProp a sh:PropertyShape ;
                sh:path ex:note ;
                sh:node ex:AddressShape ;
                sh:and ( [ sh:class ex:Alpha ] ) .
            ex:DeptProp a sh:PropertyShape ;
                sh:path ex:dept ;
                sh:class ex:Department .
            ex:AddressShape a sh:NodeShape ;
                sh:codeIdentifier "Address" ;
                sh:targetClass ex:Address ;
                sh:property [
                    sh:path ex:street ;
                    sh:datatype xsd:string ;
                    sh:minCount 1 ;
                    sh:maxCount 1
                ] .
            """,
        )
    )
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_classes == (EX + "Alpha",)


def test_empty_sh_and_is_a_vacuous_no_op() -> None:
    """``sh:and ()`` is the vacuous conjunction — contributes nothing."""
    registry = parse_shapes(_targeting_graph("sh:node ex:AddressShape ; sh:and () ;"))
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_classes == (EX + "Address",)


def test_parse_nested_value_shape_iri_resolves_through_registry(
    relationship_shapes_graph: Graph,
) -> None:
    """IRI indirection eliminates stale references — registry always holds resolved shapes."""
    registry = parse_shapes(relationship_shapes_graph)
    person = registry.by_type_name["Person"]
    employer = person.property_shapes["employer"]
    assert employer.value_shape_iri is not None

    company = registry.by_iri[employer.value_shape_iri]
    located_in = company.property_shapes["locatedIn"]
    assert located_in.value_shape_iri is not None

    city = registry.by_iri[located_in.value_shape_iri]
    assert city.graphql_type_name == "City"
    assert city.iri == registry.by_type_name["City"].iri


# --- Synthetic-shape cache ---


def test_repeated_sh_class_creates_single_synthetic_shape(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Two properties referencing the same untargeted class share one synthetic."""
    graph = Graph()
    graph.parse(
        data="""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .

        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [ sh:path ex:dept1 ; sh:class ex:Department ] ;
            sh:property [ sh:path ex:dept2 ; sh:class ex:Department ] .

        ex:OrgShape a sh:NodeShape ;
            sh:codeIdentifier "Org" ;
            sh:targetClass ex:Org ;
            sh:property [ sh:path ex:unit ; sh:class ex:Department ] .
        """,
        format="turtle",
    )
    with caplog.at_level("WARNING"):
        registry = parse_shapes(graph)
    synthetic_iri = URIRef("urn:fastshaql:synthetic:Department")
    assert synthetic_iri in registry.by_iri
    warnings = [r for r in caplog.records if "No shape targets class" in r.message]
    assert len(warnings) == 1


# --- Unsupported sh:node/sh:class forms ---


def _person_graph(prop_body: str) -> Graph:
    """A Person shape whose single ``note`` property carries *prop_body*."""
    return _shapes_graph(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:note ;
                {prop_body}
            ] .
        """
    )


def test_blank_node_sh_node_on_property_shape_raises() -> None:
    """An inline (blank-node) ``sh:node`` shape rejects — degrading the field
    to a scalar would misdescribe it."""
    graph = _person_graph("sh:node [] ;")
    with pytest.raises(UnsupportedShapeError, match="Blank-node sh:node"):
        parse_shapes(graph)


@pytest.mark.parametrize(
    ("body", "match"),
    [
        (
            "sh:node ex:AddressShape , ex:LocationShape ;",
            "Multiple sh:node values",
        ),
        (
            "sh:class ex:Company , ex:Org ;",
            (
                r"sh:class on .*: multiple conjoined classes \(sh:class, sh:and\) "
                r"intersect \(SHACL §7\.1\.1\) but name no shape — "
                r"add sh:node to select the target$"
            ),
        ),
        (
            "sh:and ( [ sh:class ex:Company ] [ sh:class ex:Org ] ) ;",
            (
                r"sh:class on .*: multiple conjoined classes \(sh:class, sh:and\) "
                r"intersect \(SHACL §7\.1\.1\) but name no shape — "
                r"add sh:node to select the target$"
            ),
        ),
    ],
    ids=["multiple_sh_node", "classes_without_node", "sh_and_classes_without_node"],
)
def test_multiple_relationship_anchor_values_raise(body: str, match: str) -> None:
    """The targeting model's rejections teach the remedy (ADR-0025):
    conjoined ``sh:node`` values select no single GraphQL type, and
    conjoined classes — flat, or from ``sh:and`` members — name no shape;
    ``sh:node`` must select the target."""
    graph = _person_graph(body)
    with pytest.raises(UnsupportedShapeError, match=match):
        parse_shapes(graph)


def test_literal_sh_node_value_raises() -> None:
    """``sh:node`` values are node shapes — a literal is ill-formed (§7.8.1)."""
    graph = _person_graph('sh:node "Address" ;')
    with pytest.raises(UnsupportedShapeError, match="not a node shape"):
        parse_shapes(graph)


def test_malformed_sh_and_list_raises() -> None:
    """A non-list ``sh:and`` value is ill-formed — the rejection names sh:and."""
    graph = _person_graph("sh:and ex:NotAList ;")
    with pytest.raises(
        UnsupportedShapeError, match=r"sh:and on .* is not a well-formed SHACL list"
    ):
        parse_shapes(graph)


@pytest.mark.parametrize(
    ("prop_def", "match"),
    [
        (
            "ex:BadProp a sh:PropertyShape ; sh:path ex:dept ; sh:class ( ex:Company ex:Org ) .",
            (
                r"sh:class on http://example\.org/BadProp: the sh:class list form "
                r"\(union of target classes, SHACL 1\.2 §7\.1\.1\) is not lowered "
                r"yet — declare one class per property until polymorphic "
                r"relationships land$"
            ),
        ),
        (
            "ex:BadProp a sh:PropertyShape ; sh:path ex:dept ; sh:class () .",
            (
                r"sh:class on http://example\.org/BadProp: the sh:class list form is "
                r"empty — declare at least one class IRI$"
            ),
        ),
        (
            (
                "ex:BadProp a sh:PropertyShape ; sh:path ex:dept ; sh:node ex:Elsewhere ; "
                "sh:class ( ex:Company ex:Org ) ."
            ),
            (
                r"sh:class on http://example\.org/BadProp: the sh:class list form .* "
                r"until polymorphic relationships land \(a list cannot express the "
                r"binding union beside sh:node either\)$"
            ),
        ),
    ],
    ids=["union", "empty_union", "union_with_node"],
)
def test_sh_class_list_form_raises(prop_def: str, match: str) -> None:
    """The 1.2 union syntax (§7.1.1) stays a loud placeholder until polymorphic
    relationships land (ADR-0026) — beside ``sh:node`` too, where the list
    would express a binding union; including the empty (vacuous) union, which
    reaches this branch rather than parsing as an IRI. Named property shapes —
    the rejection names the offender."""
    graph = _named_props_graph("ex:BadProp", prop_def)
    with pytest.raises(UnsupportedShapeError, match=match):
        parse_shapes(graph)


def test_sh_class_scan_ignores_deactivated_siblings() -> None:
    """The ``sh:class`` scan reads only live properties — a literal
    ``sh:class`` on a deactivated sibling is never seen (§3.1.6)."""
    graph = _named_props_graph(
        "ex:FineProp , ex:OffProp",
        """
        ex:FineProp a sh:PropertyShape ; sh:path ex:note ; sh:class ex:Fine .
        ex:OffProp a sh:PropertyShape ; sh:path ex:off ;
            sh:class "not-a-class" ; sh:deactivated true .
        """,
    )
    registry = parse_shapes(graph)
    note = registry.by_type_name["Person"].property_shapes["note"]
    assert note.value_classes == (EX + "Fine",)


def test_literal_sh_class_value_raises() -> None:
    """``sh:class`` values are IRIs or IRI lists — a literal is ill-formed
    (§7.1.1), and the error cites the spec rule."""
    graph = _person_graph('sh:class "Company" ;')
    with pytest.raises(
        UnsupportedShapeError,
        match=r"is not an IRI \(SHACL §7\.1\.1: values are IRIs or lists of IRIs\)$",
    ):
        parse_shapes(graph)


# --- Derived relationships ---


def test_derived_relationship_without_datatype_parses() -> None:
    """A derived relationship anchors on ``sh:class`` alone — the
    ``sh:datatype`` requirement binds only non-relationship derived fields
    (ADR-0015: (RELATIONSHIP, DERIVED) needs no literal space)."""
    graph = _shapes_graph(
        """
        @prefix ex:    <http://example.org/> .
        @prefix sh:    <http://www.w3.org/ns/shacl#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .

        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:friend ;
                sh:class ex:Person ;
                sh:values [ shnex:pathValues ex:knows ] ;
            ] .
        """
    )
    friend = parse_shapes(graph).by_type_name["Person"].property_shapes["friend"]
    assert friend.datatypes == ()
    assert friend.value_classes == (EX + "Person",)
    assert friend.value_type is ValueType.RELATIONSHIP
