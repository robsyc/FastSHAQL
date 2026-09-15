"""The ``sh:or`` member lane and the ``sh:class`` list form —
``core/parser/unions.py`` (ADR-0026).

Pass 1 recognition: heterogeneous members reject loudly, members with other
constraints stay inert, an empty ``sh:or`` is warn-and-ignored (a direct
anchor resolves the field), an ``sh:or`` beside a direct anchor rejects,
ill-formed member values never silently void a declared union, and
non-validating §8 member metadata never blocks recognition. The list-form
syntax rules: malformed lists and flat-beside-list reject. Pass 2 checks:
member targets must be class-indexed, duplicates and GraphQL-name collisions
reject, a sole member collapses to the plain single-target binding, a child
shape inherits the field with members resolved, and visibility is
strictest-wins over member targets.

Order: recognition rules → list-form rules → pass-2 member checks.
"""

from __future__ import annotations

import logging

import pytest
from rdflib import Graph, Literal, URIRef
from rdflib.namespace import RDF, RDFS, SH, XSD

from fastshaql.core.ir import ValueType
from fastshaql.core.ir.property_shape import UnionMember
from fastshaql.core.parser import parse_shapes
from fastshaql.core.parser.errors import UnsupportedShapeError
from fastshaql.core.parser.unions import NON_VALIDATING_MEMBER_PREDICATES
from fastshaql.core.parser.util import SH_CODE_IDENTIFIER
from fastshaql.core.parser.visibility import VisibilityError
from support.builders import EX


def _shapes_graph(turtle: str) -> Graph:
    graph = Graph()
    graph.parse(data=turtle, format="turtle")
    return graph


_ORG_SHAPE = """
ex:OrgShape a sh:NodeShape ; sh:codeIdentifier "Org" ;
    sh:targetClass ex:Org .
"""


def _person_graph(prop_def: str, shapes: str = "") -> Graph:
    """A Person shape whose inline ``dept`` property carries *prop_def*,
    beside any extra node *shapes* (member targets and the like)."""
    inner = prop_def.strip().removesuffix(".").strip()
    return _shapes_graph(
        f"""
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        @prefix shnex: <http://www.w3.org/ns/shacl-node-expr#> .
        {shapes}
        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [
                {inner}
            ] .
        """
    )


# --- Recognition rules ---


@pytest.mark.parametrize(
    "prop_def",
    [
        "sh:path ex:dept ; sh:or ( [ sh:class ex:Company ] [ sh:datatype xsd:string ] ) .",
        "sh:path ex:dept ; sh:or ( [ sh:node ex:OrgShape ] [ sh:datatype xsd:string ] ) .",
    ],
    ids=["class_and_datatype", "node_and_datatype"],
)
def test_heterogeneous_sh_or_members_reject(prop_def: str) -> None:
    """Datatype members mixed with class/node members reject loudly —
    GraphQL unions cannot contain scalars (ADR-0026)."""
    with pytest.raises(
        UnsupportedShapeError,
        match=r"sh:or on .* field 'dept' mixes datatype and class/node members",
    ):
        parse_shapes(_person_graph(prop_def, shapes=_ORG_SHAPE))


def test_sibling_datatype_property_does_not_mask_heterogeneous_reject() -> None:
    """The datatype-member probe reads the member, not the whole shapes
    graph — a sibling scalar property elsewhere must not dilute it into
    silence."""
    graph = _shapes_graph(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
        ex:PersonShape a sh:NodeShape ;
            sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [ sh:path ex:note ; sh:datatype xsd:string ] ;
            sh:property [
                sh:path ex:dept ;
                sh:or ( [ sh:class ex:Company ] [ sh:datatype xsd:string ] )
            ] .
        """
    )
    with pytest.raises(
        UnsupportedShapeError,
        match=r"sh:or on .* field 'dept' mixes datatype and class/node members",
    ):
        parse_shapes(graph)


def test_metadata_on_datatype_member_keeps_heterogeneous_reject() -> None:
    """§8 metadata on a datatype member is not a second value — the member
    stays the datatype lane's and heterogeneity still rejects."""
    with pytest.raises(
        UnsupportedShapeError,
        match=r"sh:or on .* field 'dept' mixes datatype and class/node members",
    ):
        parse_shapes(
            _person_graph(
                "sh:path ex:dept ; "
                'sh:or ( [ sh:class ex:Company ] [ sh:datatype xsd:string ; sh:name "note" ] ) .'
            )
        )


def test_ill_formed_datatype_member_value_stays_inert() -> None:
    """A literal ``sh:datatype`` value is ill-formed, not a datatype member
    — the whole ``sh:or`` goes inert (the datatype lane's reading); it never
    fabricates a heterogeneous rejection."""
    registry = parse_shapes(
        _person_graph(
            'sh:path ex:dept ; sh:or ( [ sh:class ex:Company ] [ sh:datatype "plain" ] ) .'
        )
    )
    prop = registry.by_type_name["Person"].property_shapes["dept"]
    assert prop.value_type is ValueType.SCALAR
    assert not prop.is_polymorphic


@pytest.mark.parametrize(
    ("prop_def", "anchor"),
    [
        (
            "sh:path ex:dept ; sh:node ex:OrgShape ; sh:or ( [ sh:class ex:Company ] ) .",
            "sh:node",
        ),
        (
            "sh:path ex:dept ; sh:class ex:Company ; sh:or ( [ sh:class ex:Org ] ) .",
            "sh:class",
        ),
        (
            "sh:path ex:dept ; sh:datatype xsd:string ; sh:or ( [ sh:class ex:Company ] ) .",
            "sh:datatype",
        ),
    ],
    ids=["beside_node", "beside_class", "beside_datatype"],
)
def test_sh_or_beside_direct_anchor_rejects(prop_def: str, anchor: str) -> None:
    """The spec conjoins ``sh:or`` with direct anchors (§3.1.1) — the
    intersection has no GraphQL lowering; the union declares alone. The
    rejection names the anchor(s) actually co-present (ADR-0026)."""
    with pytest.raises(
        UnsupportedShapeError,
        match=rf"sh:or on .* field 'dept' beside a direct {anchor} constraint",
    ):
        parse_shapes(_person_graph(prop_def, shapes=_ORG_SHAPE))


@pytest.mark.parametrize(
    ("prop_def", "match"),
    [
        (
            'sh:path ex:dept ; sh:or ( [ sh:node "not-a-shape" ] ) .',
            (
                r"sh:or on .* field 'dept': sh:node in an sh:or member must be "
                r"exactly one IRI \(got .*'not-a-shape'\)"
            ),
        ),
        (
            "sh:path ex:dept ; sh:or ( [ sh:node [] ] ) .",
            (
                r"sh:or on .* field 'dept': blank-node sh:node in an sh:or "
                r"member — inline shapes and the sh:class list form are not "
                r"supported inside members"
            ),
        ),
        (
            'sh:path ex:dept ; sh:or ( [ sh:class "not-a-class" ] ) .',
            (
                r"sh:or on .* field 'dept': sh:class in an sh:or member must be "
                r"exactly one IRI \(got .*'not-a-class'\)"
            ),
        ),
        (
            "sh:path ex:dept ; sh:or ( [ sh:class ex:Company, ex:Org ] ) .",
            (
                r"sh:or on .* field 'dept': sh:class in an sh:or member must be "
                r"exactly one IRI"
            ),
        ),
    ],
    ids=["literal_node", "blank_node", "literal_class", "two_values"],
)
def test_ill_formed_member_values_reject(prop_def: str, match: str) -> None:
    """Ill-formed values on the recognized predicates reject loudly — the
    same malformations the single-target lane rejects (multiples, literals,
    blank nodes); they never silently void a declared union into an untyped
    scalar."""
    with pytest.raises(UnsupportedShapeError, match=match):
        parse_shapes(_person_graph(prop_def))


def test_sh_or_member_with_other_constraints_stays_inert(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A member carrying any other constraint (``sh:pattern``) leaves the
    whole ``sh:or`` inert — the datatype lane's reading, minus the
    member-consumption warning (that lane is not entered)."""
    caplog.set_level(logging.WARNING, logger="fastshaql.core.parser.datatypes")
    registry = parse_shapes(
        _person_graph(
            'sh:path ex:dept ; sh:or ( [ sh:class ex:Company ] [ sh:pattern "^x" ] ) .'
        )
    )
    prop = registry.by_type_name["Person"].property_shapes["dept"]
    assert prop.value_type is ValueType.SCALAR
    assert any(
        "carries non-datatype constraints" in record.message
        for record in caplog.records
    )


_MEMBER_METADATA: dict[URIRef, str] = {
    SH.name: 'sh:name "the org"',
    SH.description: 'sh:description "the org"',
    SH["order"]: "sh:order 1",
    SH["group"]: "sh:group ex:SomeGroup",
    URIRef("http://www.w3.org/ns/shacl#intent"): 'sh:intent "selects the owning org"',
    URIRef(
        "http://www.w3.org/ns/shacl#agentInstruction"
    ): 'sh:agentInstruction "ask an editor"',
    URIRef("http://www.w3.org/ns/shacl#unit"): "sh:unit ex:SomeUnit",
    SH_CODE_IDENTIFIER: 'sh:codeIdentifier "primary"',
    RDF.type: "a ex:Tagged",
    RDFS.label: 'rdfs:label "the org"',
    RDFS.comment: 'rdfs:comment "the org"',
}


@pytest.mark.parametrize(
    "metadata",
    _MEMBER_METADATA.values(),
    ids=[str(p).rsplit("#", 1)[-1].rsplit("/", 1)[-1] for p in _MEMBER_METADATA],
)
def test_member_metadata_does_not_block_recognition(metadata: str) -> None:
    """Every §8 non-validating member predicate adds no value constraint —
    the member stays recognized (ADR-0026 counts constraints only); the
    second member keeps the field polymorphic past the sole-member collapse.
    The parametrize set is pinned to the parser's frozenset, so a newly
    tolerated predicate must land here to stay covered."""
    assert set(_MEMBER_METADATA) == NON_VALIDATING_MEMBER_PREDICATES
    registry = parse_shapes(
        _person_graph(
            f"sh:path ex:dept ; sh:or ( [ sh:class ex:Org ; {metadata} ] [ sh:node ex:UnitShape ] ) .",
            shapes="@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> ."
            + _ORG_SHAPE
            + """
            ex:UnitShape a sh:NodeShape ; sh:codeIdentifier "Unit" ;
                sh:targetClass ex:Unit .
            """,
        )
    )
    prop = registry.by_type_name["Person"].property_shapes["dept"]
    assert prop.is_polymorphic
    assert prop.union_members == (
        UnionMember(shape_iri=EX + "OrgShape", class_iri=EX + "Org"),
        UnionMember(shape_iri=EX + "UnitShape", class_iri=EX + "Unit"),
    )


@pytest.mark.parametrize(
    (
        "prop_def",
        "value_type",
        "datatypes",
        "in_values",
        "value_shape_iri",
        "value_classes",
        "union_members",
    ),
    [
        ("sh:path ex:dept ; sh:or () .", ValueType.SCALAR, (), None, None, (), ()),
        (
            "sh:path ex:dept ; sh:or () ; sh:datatype xsd:integer .",
            ValueType.SCALAR,
            (XSD.integer,),
            None,
            None,
            (),
            (),
        ),
        (
            'sh:path ex:dept ; sh:or () ; sh:in ( "active" "retired" ) .',
            ValueType.ENUM,
            (),
            (Literal("active"), Literal("retired")),
            None,
            (),
            (),
        ),
        (
            "sh:path ex:dept ; sh:or () ; sh:node ex:OrgShape .",
            ValueType.RELATIONSHIP,
            (),
            None,
            EX + "OrgShape",
            (EX + "Org",),
            (),
        ),
        (
            "sh:path ex:dept ; sh:or () ; sh:class ex:Org .",
            ValueType.RELATIONSHIP,
            (),
            None,
            EX + "OrgShape",
            (EX + "Org",),
            (),
        ),
        (
            "sh:path ex:dept ; sh:or () ; sh:class ( ex:Org ex:Unit ) .",
            ValueType.RELATIONSHIP,
            (),
            None,
            None,
            (),
            (
                UnionMember(shape_iri=EX + "OrgShape", class_iri=EX + "Org"),
                UnionMember(
                    shape_iri=URIRef("urn:fastshaql:synthetic:Unit"),
                    class_iri=EX + "Unit",
                ),
            ),
        ),
    ],
    ids=[
        "alone_untyped_scalar",
        "beside_datatype",
        "beside_in",
        "beside_node",
        "beside_class",
        "beside_class_list_form",
    ],
)
def test_empty_sh_or_warns_and_the_anchor_resolves(
    prop_def: str,
    value_type: ValueType,
    datatypes: tuple[URIRef, ...],
    in_values: tuple[Literal, ...] | None,
    value_shape_iri: URIRef | None,
    value_classes: tuple[URIRef, ...],
    union_members: tuple[UnionMember, ...],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """An empty ``sh:or ()`` is spec-legal but memberless — a zero-member
    disjunction fails every value (§7.7.3), so the lane warns once and
    ignores it as unsatisfiable noise: a direct anchor (``sh:datatype``,
    ``sh:in``, ``sh:node``, ``sh:class`` — flat or list form) resolves the
    field, and alone the field stays the untyped String scalar."""
    caplog.set_level(logging.WARNING, logger="fastshaql.core.parser.unions")
    registry = parse_shapes(_person_graph(prop_def, shapes=_ORG_SHAPE))
    prop = registry.by_type_name["Person"].property_shapes["dept"]
    assert prop.value_type is value_type
    assert prop.datatypes == datatypes
    assert prop.in_values == in_values
    assert prop.value_shape_iri == value_shape_iri
    assert prop.value_classes == value_classes
    assert prop.union_members == union_members
    # One consistent teaching warning — never a second walk from the
    # datatype lane, never the beside-anchor rejection.
    (warning,) = [r for r in caplog.records if "is empty" in r.getMessage()]
    assert warning.getMessage() == (
        "sh:or on urn:fastshaql:inline:PersonDept field 'dept' is empty — "
        "a memberless disjunction fails every value per the spec "
        "(SHACL 1.2 §7.7.3); ignored as unsatisfiable noise, the field "
        "resolves from its direct constraints"
    )


# --- List-form rules ---


@pytest.mark.parametrize(
    ("prop_def", "match"),
    [
        (
            "sh:path ex:dept ; sh:class ( ex:Company ex:Org ) , ( ex:Unit ) .",
            r"multiple sh:class list forms",
        ),
        (
            'sh:path ex:dept ; sh:class ( ex:Company "Org" ) .',
            r"sh:class on .* list form members must be IRIs",
        ),
        (
            "sh:path ex:dept ; sh:class ex:Unit , ( ex:Company ex:Org ) .",
            r"flat values \(sh:class, sh:and\) beside the list form",
        ),
    ],
    ids=["multiple_lists", "literal_member", "flat_beside_list"],
)
def test_list_form_malformed_syntax_rejects(prop_def: str, match: str) -> None:
    """The list form's syntax rules reject loudly (§7.1.1): one list per
    property, IRIs only as members, and no flat ``sh:class`` beside the
    list (the intersection has no union reading)."""
    with pytest.raises(UnsupportedShapeError, match=match):
        parse_shapes(_person_graph(prop_def))


# --- Pass-2 member checks ---


def test_member_referencing_unknown_shape_rejects() -> None:
    graph = _person_graph("sh:path ex:dept ; sh:or ( [ sh:node ex:MissingShape ] ) .")
    with pytest.raises(
        UnsupportedShapeError,
        match=(
            r"sh:or member on .* field 'dept' references unknown shape "
            r".*sh:deactivated shape parses to nothing"
        ),
    ):
        parse_shapes(graph)


@pytest.mark.parametrize(
    ("member_shape", "shape_def"),
    [
        (
            "ex:NoteShape",
            """
            ex:NoteShape a sh:NodeShape ; sh:codeIdentifier "Note" ;
                sh:property [ sh:path ex:text ; sh:datatype xsd:string ] .
            """,
        ),
        (
            "ex:DerivedShape",
            """
            ex:DerivedShape a sh:NodeShape ; sh:codeIdentifier "Derived" ;
                sh:targetNode [ shnex:instancesOf ex:Thing ] .
            """,
        ),
    ],
    ids=["classless_target", "derived_target"],
)
def test_member_target_without_class_discriminator_rejects(
    member_shape: str, shape_def: str
) -> None:
    """The member discriminator needs a class-indexed target — class-less
    and derived targets do not discriminate (ADR-0026)."""
    graph = _person_graph(
        f"sh:path ex:dept ; sh:or ( [ sh:node {member_shape} ] ) .",
        shapes=shape_def,
    )
    with pytest.raises(
        UnsupportedShapeError,
        match=r"sh:or member target .* has no class discriminator",
    ):
        parse_shapes(graph)


@pytest.mark.parametrize(
    ("prop_def", "shapes", "match"),
    [
        (
            (
                "sh:path ex:dept ; "
                "sh:or ( [ sh:class ex:Company ] [ sh:class ex:Company ] ) ."
            ),
            "",
            (
                r"duplicate union member on .* field 'dept' — two members "
                r"resolve to the same class"
            ),
        ),
        (
            "sh:path ex:dept ; sh:or ( [ sh:node ex:OrgShape ] [ sh:class ex:Org ] ) .",
            _ORG_SHAPE,
            (
                r"duplicate union member on .* field 'dept' — two members "
                r"resolve to the same class"
            ),
        ),
        (
            "sh:path ex:dept ; sh:node ex:OrgShape ; sh:class ( ex:Org ex:Org ) .",
            _ORG_SHAPE,
            r"duplicate union member on .* field 'dept'",
        ),
        (
            "sh:path ex:dept ; sh:class ( ex:Org ex:Org ) .",
            "",
            r"duplicate union member on .* field 'dept'",
        ),
    ],
    ids=["sh_or_classes", "node_beside_class", "binding_union_list_form", "list_form"],
)
def test_duplicate_union_members_reject(prop_def: str, shapes: str, match: str) -> None:
    """Two members resolving to the same class reject, whatever the
    spelling — two ``sh:class`` members; a ``sh:node`` member beside a
    ``sh:class`` member of the same shape (the check fires on the resolved
    class, the shape reading subsumed); a repeated class in the
    binding-union list form beside ``sh:node`` (every member past the first
    is checked); and a repeated list-form entry (the list form normalises
    into the member lane, rejecting uniformly with ``sh:or``). A value
    matching two lanes under one discriminator is ambiguous."""
    with pytest.raises(UnsupportedShapeError, match=match):
        parse_shapes(_person_graph(prop_def, shapes=shapes))


@pytest.mark.parametrize(
    ("prop_def", "shapes", "type_name"),
    [
        (
            (
                "sh:path ex:dept ; sh:or ( [ sh:class ex:Company ] "
                "[ sh:class <http://xmlns.com/foaf/0.1/Company> ] ) ."
            ),
            """
            ex:CompanyShape a sh:NodeShape ; sh:codeIdentifier "Company" ;
                sh:targetClass ex:Company .
            """,
            "Company",
        ),
        (
            "sh:path ex:dept ; sh:or ( [ sh:node ex:HomeShape ] [ sh:node ex:WorkShape ] ) .",
            """
            ex:HomeShape a sh:NodeShape ; sh:codeIdentifier "Dept" ;
                sh:targetClass ex:Home .
            ex:WorkShape a sh:NodeShape ; sh:codeIdentifier "Dept" ;
                sh:targetClass ex:Work .
            """,
            "Dept",
        ),
    ],
    ids=["same_local_name", "same_code_identifier"],
)
def test_colliding_member_type_names_reject(
    prop_def: str, shapes: str, type_name: str
) -> None:
    """Member shapes deriving the same GraphQL type name reject — the union
    would repeat an object type. The check reads each member *shape's*
    GraphQL name and falls back to the class-derived name only for
    shape-less members: a local-name collision across namespaces, and
    colliding ``sh:codeIdentifier`` values beside distinct class local
    names, both reject."""
    with pytest.raises(
        UnsupportedShapeError,
        match=(
            rf"union members on .* field 'dept' .* derive the same GraphQL "
            rf"type name '{type_name}' — disambiguate"
        ),
    ):
        parse_shapes(_person_graph(prop_def, shapes=shapes))


@pytest.mark.parametrize(
    "prop_def",
    [
        "sh:path ex:dept ; sh:or ( [ sh:node ex:OrgShape ] ) .",
        "sh:path ex:dept ; sh:class ( ex:Org ) .",
        "sh:path ex:dept ; sh:node ex:OrgShape ; sh:class ( ex:Org ) .",
    ],
    ids=["sh_or_member", "list_form_entry", "list_form_beside_node"],
)
def test_sole_member_collapses_to_single_target(prop_def: str) -> None:
    """A sole member names one target and one binding class — the plain
    rows 2/3 of the targeting model, no union artifact for a monomorphic
    field, whatever the spelling: a lone ``sh:or`` member, a one-entry
    list form, or a one-entry list form beside ``sh:node`` (row 2 exactly
    — ``sh:node`` names the target, the one class types it, ADR-0025)."""
    registry = parse_shapes(_person_graph(prop_def, shapes=_ORG_SHAPE))
    prop = registry.by_type_name["Person"].property_shapes["dept"]
    assert not prop.is_polymorphic
    assert prop.union_members == ()
    assert prop.value_shape_iri == EX + "OrgShape"
    assert prop.value_classes == (EX + "Org",)


def test_inheritance_carries_polymorphic_field() -> None:
    """A child shape inheriting a ``sh:or`` field flattens it — the members
    arrive resolved to (shape, class) pairs on the child exactly as on the
    parent."""
    registry = parse_shapes(
        _shapes_graph(
            """
            @prefix ex: <http://example.org/> .
            @prefix sh: <http://www.w3.org/ns/shacl#> .
            @prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
            ex:OrgShape a sh:NodeShape ; sh:codeIdentifier "Org" ;
                sh:targetClass ex:Org .
            ex:UnitShape a sh:NodeShape ; sh:codeIdentifier "Unit" ;
                sh:targetClass ex:Unit .
            ex:ParentShape a sh:NodeShape ; sh:codeIdentifier "Parent" ;
                sh:targetClass ex:Parent ;
                sh:property [
                    sh:path ex:dept ;
                    sh:or ( [ sh:class ex:Org ] [ sh:node ex:UnitShape ] )
                ] .
            ex:ChildShape a sh:NodeShape ; sh:codeIdentifier "Child" ;
                sh:targetClass ex:Child ;
                sh:node ex:ParentShape ;
                sh:property [ sh:path ex:grade ; sh:datatype xsd:integer ] .
            """
        )
    )
    child = registry.by_type_name["Child"]
    prop = child.property_shapes["dept"]
    assert prop.is_polymorphic
    assert prop.union_members == (
        UnionMember(shape_iri=EX + "OrgShape", class_iri=EX + "Org"),
        UnionMember(shape_iri=EX + "UnitShape", class_iri=EX + "Unit"),
    )


def test_visibility_strictest_wins_over_members() -> None:
    """A private member inside a published union rejects loudly at parse —
    unions are introspectable (ADR-0026 boundaries)."""
    graph = _shapes_graph(
        """
        @prefix ex: <http://example.org/> .
        @prefix sh: <http://www.w3.org/ns/shacl#> .
        @prefix graphql: <http://datashapes.org/graphql#> .
        ex:OrgShape a sh:NodeShape ; sh:codeIdentifier "Org" ;
            sh:targetClass ex:Org .
        ex:GhostShape a sh:NodeShape ; sh:codeIdentifier "Ghost" ;
            sh:targetClass ex:Ghost .
        ex:PersonShape a sh:NodeShape ; sh:codeIdentifier "Person" ;
            sh:targetClass ex:Person ;
            sh:property [
                sh:path ex:dept ;
                sh:or ( [ sh:class ex:Org ] [ sh:node ex:GhostShape ] )
            ] .
        ex:Api a graphql:Schema ;
            graphql:publicShape ex:PersonShape, ex:OrgShape ;
            graphql:privateShape ex:GhostShape .
        """
    )
    with pytest.raises(VisibilityError, match=r"targets shape .*GhostShape"):
        parse_shapes(graph)


def test_registry_chokepoint_rejects_polymorphic_target_resolution() -> None:
    """``resolve_relationship_target`` is the single-target chokepoint — a
    polymorphic property rejects so a forgotten call site fails loudly."""
    registry = parse_shapes(
        _person_graph(
            "sh:path ex:dept ; sh:or ( [ sh:class ex:Company ] [ sh:class ex:Org ] ) ."
        )
    )
    prop = registry.by_type_name["Person"].property_shapes["dept"]
    with pytest.raises(ValueError, match=r"Relationship 'dept' is polymorphic"):
        registry.resolve_relationship_target(prop)
