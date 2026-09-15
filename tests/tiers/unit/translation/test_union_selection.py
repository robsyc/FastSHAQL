"""Union selections — ``core/translation/selection.py``'s union walk
(ADR-0026).

Tests the polymorphic translation mechanics on the shared fixture set:
selection-shape rejections (bare fields, spreads, conditionless or duplicate
or non-member fragments, directives at every level), the walk's lane
emission (``__typename`` skips, untouched members stay field-less, matching
fragments flatten at every nesting, fields survive a preceding fragment,
required fields drop the outer OPTIONAL), member-scope recursion (a nested
relationship — single-target or another union — inside a member fragment),
and the filter boundary's loud backstop.

Order: selection-shape rejections → selection walk → filter boundary.
"""

from __future__ import annotations

import pytest
from graphql.error import GraphQLSyntaxError
from graphql.language import ObjectValueNode

from fastshaql.core.kernel.io import load_shapes
from fastshaql.core.parser import parse_shapes
from fastshaql.core.translation.field_binding import FieldBindings
from fastshaql.core.translation.filters.exists_scope import RootFilterContext
from fastshaql.core.translation.query import translate_query
from fastshaql.core.translation.variables import Variable
from support.builders import POLY_ARTICLE_SHAPES
from support.cases import registry_for
from support.graphql_utils import root_field_node
from support.translation import translation_scope

ARTICLE_QUERY = "query {{ article {{ {inner} }} }}"


@pytest.fixture(scope="module")
def registry():
    return registry_for("polymorphic_relationships")


def _translate(registry, inner: str):
    shape = registry.by_type_name["Article"]
    return translate_query(
        shape, root_field_node(ARTICLE_QUERY.format(inner=inner)), registry
    )


# --- Selection-shape rejections ---


@pytest.mark.parametrize(
    ("inner", "error", "match"),
    [
        (
            "block { text }",
            TypeError,
            r"bare field 'text' on union field 'block'",
        ),
        (
            "block { ...frag }",
            TypeError,
            r"named fragments are not supported \(got 'FragmentSpreadNode'\)",
        ),
        (
            "block { ... { text } }",
            TypeError,
            r"inline fragment without a type condition",
        ),
        (
            "block { ... on Paragraph { text } ... on Paragraph { text } }",
            ValueError,
            r"two inline fragments on 'Paragraph'",
        ),
        (
            "block { ... on Table { rows } }",
            ValueError,
            r"inline fragment on non-member type \['Table'\] of union field 'block'",
        ),
    ],
    ids=["bare_field", "named_spread", "conditionless", "duplicate", "non_member"],
)
def test_union_selection_rejections(registry, inner: str, error, match: str) -> None:
    with pytest.raises(error, match=match):
        _translate(registry, inner)


def test_empty_inline_fragment_pair_is_unreachable_graphql() -> None:
    """A bodiless inline fragment is a GraphQL *syntax* error — the walker's
    body-required assert never sees one (grammar guarantee)."""
    with pytest.raises(GraphQLSyntaxError):
        root_field_node("query { article { ... on Article } }")


def test_directives_on_inline_fragments_reject(registry) -> None:
    """Directives on an object-level fragment reject — silently ignoring
    ``@include``/``@skip`` would fetch skipped fields (ADR-0026); the
    rejection names the nesting level the fragment sits in."""
    with pytest.raises(
        TypeError,
        match=(
            r"Directives on selections are not supported "
            r"\(on an inline fragment inside a 'Article' selection\)"
        ),
    ):
        _translate(registry, "title ... on Article @include(if: true) { t }")


def test_directives_on_union_member_fragments_reject(registry) -> None:
    """The same rejection inside a union selection — a different walker
    path, the same boundary, the field named."""
    with pytest.raises(
        TypeError,
        match=(
            r"Directives on selections are not supported "
            r"\(on an inline fragment in union field 'block'\)"
        ),
    ):
        _translate(registry, "block { ... on Paragraph @include(if: true) { text } }")


@pytest.mark.parametrize(
    ("inner", "field"),
    [
        ("title @include(if: true)", "title"),
        ("block { ... on Paragraph { text @skip(if: false) } }", "text"),
    ],
    ids=["object_level", "inside_member_fragment"],
)
def test_directives_on_fields_reject(registry, inner: str, field: str) -> None:
    """Directives on plain fields reject at every nesting level — the
    translation fetches what it walks, so a skipped field would still be
    fetched (ADR-0026); the rejection names the field."""
    with pytest.raises(
        TypeError,
        match=rf"Directives on selections are not supported \(on field '{field}'",
    ):
        _translate(registry, inner)


def test_directives_on_root_field_reject(registry) -> None:
    """The root query field's directives reject too — same boundary, one
    level up."""
    shape = registry.by_type_name["Article"]
    node = root_field_node("query { article @include(if: true) { title } }")
    with pytest.raises(TypeError, match=r"root query field 'article'"):
        translate_query(shape, node, registry)


# --- Selection walk ---


def test_object_level_typename_meta_field_is_skipped(registry) -> None:
    """``__typename`` on an object type resolves in the executor — the walk
    skips it and the field set is otherwise unchanged."""
    with_typename = _translate(registry, "__typename title").var_map
    without = _translate(registry, "title").var_map
    assert with_typename.fields == without.fields


def test_union_level_typename_meta_field_is_skipped(registry) -> None:
    """``__typename`` inside a union selection skips — the union walker
    reserves it for the converter's stamp, never a bare-field rejection —
    and may stand alone: a fragment-free selection keeps the discriminator
    with every member field-less, and with one member fragment touched the
    untouched member's lane stays guard-only."""
    alone = _translate(registry, "block { __typename }")
    binding = alone.var_map.relationships["block"]
    assert binding.discriminator == Variable("block_member")
    paragraph_map, image_map = (m.map for m in binding.members)
    assert paragraph_map.fields == {}
    assert image_map.fields == {}
    result = _translate(registry, "block { __typename ... on Image { url } }")
    binding = result.var_map.relationships["block"]
    paragraph_map, image_map = (m.map for m in binding.members)
    assert paragraph_map.fields == {}
    assert image_map.fields == {"url": Variable("block_2_url")}


def test_field_after_a_fragment_survives_flattening(registry) -> None:
    """The walker continues past a flattened fragment — a field *after* it
    is walked too, not dropped by an early exit."""
    result = _translate(registry, "... on Article { title } iri")
    assert set(result.var_map.fields) == {"title", "iri"}


def test_matching_fragments_flatten_recursively(registry) -> None:
    """An inline fragment naming the enclosing type flattens — even nested
    in another matching fragment (the recursion keeps the type context)."""
    result = _translate(registry, "... on Article { ... on Article { title } }")
    assert set(result.var_map.fields) == {"title"}


def test_matching_fragments_flatten_inside_relationships(registry) -> None:
    """The relationship walk hands its child type name down — matching
    fragments flatten inside a single-target relationship selection too."""
    result = _translate(registry, "asset { ... on Asset { ... on Asset { caption } } }")
    binding = result.var_map.relationships["asset"]
    assert set(binding.single_map.fields) == {"caption"}


def test_matching_fragments_flatten_inside_member_fragments(registry) -> None:
    """The union member walk hands its member type name down — matching
    fragments flatten inside a member fragment too."""
    result = _translate(
        registry, "block { ... on Paragraph { ... on Paragraph { text } } }"
    )
    binding = result.var_map.relationships["block"]
    paragraph_map, _image_map = (m.map for m in binding.members)
    assert set(paragraph_map.fields) == {"text"}


def test_relationship_inside_member_fragment_walks_member_scope(registry) -> None:
    """A member fragment may select a nested relationship — the walk
    recurses into the member's scope and allocates its variables there."""
    result = _translate(registry, "block { ... on Paragraph { text author { name } } }")
    binding = result.var_map.relationships["block"]
    paragraph_map, _image_map = (m.map for m in binding.members)
    author = paragraph_map.relationships["author"]
    assert author.subject_var == Variable("block_1_author_iri")
    assert set(author.single_map.fields) == {"name"}


def test_union_inside_member_fragment_recurses_union_scope() -> None:
    """A member fragment may select another polymorphic field — the member
    scope recurses as a *union* scope: the nested binding gets its own
    discriminator and per-member maps, variables allocated under the
    member's lane prefix."""
    registry = parse_shapes(
        load_shapes(
            POLY_ARTICLE_SHAPES
            + """
            ex:ImageShape sh:property [ sh:path ex:shot ;
                sh:or ( [ sh:class ex:Paragraph ] [ sh:class ex:Image ] ) ] .
            """
        )
    )
    result = _translate(
        registry, "block { ... on Image { shot { ... on Paragraph { text } } } }"
    )
    binding = result.var_map.relationships["block"]
    image_map = binding.members[1].map
    shot = image_map.relationships["shot"]
    assert shot.subject_var == Variable("block_2_shot_iri")
    assert shot.discriminator == Variable("block_2_shot_member")
    paragraph, image = shot.members
    assert paragraph.map.fields == {"text": Variable("block_2_shot_1_text")}
    assert image.map.fields == {}


def test_required_polymorphic_field_emits_bound_join(registry) -> None:
    """minCount 1 drops the outer OPTIONAL — the link and guard are inner
    joins and childless parents drop; only the two member lanes stay
    OPTIONAL by design. The fixture's ``lead`` is the required union."""
    rendered = _translate(registry, "lead { ... on Paragraph { text } }").query.render()
    first_lane = rendered.index("OPTIONAL {")
    assert rendered.index("?iri <http://example.org/lead> ?lead_iri .") < first_lane
    assert rendered.index("VALUES ?lead_member") < first_lane
    assert rendered.count("OPTIONAL {") == 2


# --- Filter boundary ---


def test_filter_on_polymorphic_field_rejects_loudly(registry) -> None:
    """The slice-3 boundary: a ``where`` reaching a polymorphic field
    rejects with the remedy (member-keyed inputs arrive with the filter
    slice, per ADR-0026)."""
    shape = registry.by_type_name["Article"]
    root = root_field_node(
        'query { article(where: { block: { iri: { eq: "x" } } }) { title } }'
    )
    with pytest.raises(
        ValueError,
        match=r"Filters on polymorphic field 'block' are not supported yet .*\(ADR-0026\)",
    ):
        translate_query(shape, root, registry)


def test_promoted_polymorphic_field_rejects_even_with_null_filter(registry) -> None:
    """A ``where`` naming a polymorphic field rejects even at a null filter
    value — the where walker's null early-return skips the filter-side
    boundary, but promotion binding still rejects (slice 3): no completing
    translation ever reaches a promoted polymorphic field."""
    shape = registry.by_type_name["Article"]
    root = root_field_node("query { article(where: { block: null }) { title } }")
    with pytest.raises(
        ValueError,
        match=r"Filters on polymorphic field 'block' are not supported yet .*\(ADR-0026\)",
    ):
        translate_query(shape, root, registry)


def test_empty_where_object_on_polymorphic_field_rejects_with_teaching_message(
    registry,
) -> None:
    """The empty where-object must hit the filter boundary's teaching
    message, not slip through promotion to the registry chokepoint."""
    shape = registry.by_type_name["Article"]
    root = root_field_node("query { article(where: { block: {} }) { title } }")
    with pytest.raises(
        ValueError, match=r"Filters on polymorphic field 'block' are not supported yet"
    ):
        translate_query(shape, root, registry)


def test_nested_filter_on_polymorphic_field_rejects_loudly() -> None:
    """The same boundary inside a nested relationship filter — the EXISTS
    context raises identically (slice 3)."""
    registry = parse_shapes(
        load_shapes(
            POLY_ARTICLE_SHAPES
            + """
            ex:OuterShape a sh:NodeShape ; sh:codeIdentifier "Outer" ;
                sh:targetClass ex:Outer ;
                sh:property [ sh:path ex:name ; sh:datatype xsd:string ] ;
                sh:property [ sh:path ex:rel ; sh:node ex:ArticleShape ] .
            """
        )
    )
    shape = registry.by_type_name["Outer"]
    root = root_field_node(
        'query { outer(where: { rel: { block: { iri: { eq: "x" } } } }) { name } }'
    )
    with pytest.raises(
        ValueError, match=r"Filters on polymorphic field 'block' are not supported yet"
    ):
        translate_query(shape, root, registry)


def test_root_filter_context_backstop_rejects_polymorphic(registry) -> None:
    """Direct-call backstop: the root filter strategy rejects polymorphic
    fields even when reached outside the query pipeline (promotion normally
    raises first)."""
    scope = translation_scope(registry)
    ctx = RootFilterContext.from_scope(scope, bindings=FieldBindings())
    prop = registry.by_type_name["Article"].property_shapes["block"]
    with pytest.raises(
        ValueError, match=r"Filters on polymorphic field 'block' are not supported yet"
    ):
        ctx.translate_relationship("block", ObjectValueNode(fields=()), prop, registry)
