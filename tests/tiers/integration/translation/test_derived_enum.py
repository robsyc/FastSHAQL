"""Derived enums — ``sh:values`` + ``sh:in`` (ADR-0015, SD-9).

Render tier: ``where``-filters over a derived enum binding — the
``enum_term_by_name`` NAME→term recovery compared against the value
variable the derived expression binds. Execution counterparts (row
selection, SD-9 serialization) live in ``integration/execution/``; the
happy-path select/filter E2E in ``node_expr/derived_enum_nested_if``.
"""

from __future__ import annotations

from fastshaql.core.translation import translate_query
from support.cases import registry_for
from support.graphql_utils import root_field_node


def test_derived_enum_filter_compares_against_derived_binding() -> None:
    """``where: {curationStatus: {eq: CURATED}}`` on a derived enum field
    filters the value variable the nested-if binds — bind-then-filter, the
    NAME→term recovery identical to the asserted-enum path (the two axes are
    independent; filter translation reads the type axis only)."""
    registry = registry_for("node_expr")
    shape = registry.by_type_name["Variant"]
    result = translate_query(
        shape,
        root_field_node("{ variants(where: {curationStatus: {eq: CURATED}}) { iri } }"),
        registry,
    )
    rendered = result.query.render()
    assert 'FILTER(?curationStatus = "curated")' in rendered
    # The nested-if BIND (the derived binding) precedes the FILTER it feeds.
    assert rendered.index("BIND(IF(EXISTS") < rendered.index("FILTER(?curationStatus")


def test_derived_enum_in_not_in_recover_terms_by_name() -> None:
    """``in``/``notIn`` over a derived enum recover their terms through the
    same NAME→term mapping and compare against the derived binding — the
    operator set is identical to asserted enums (only the type axis is
    read)."""
    registry = registry_for("node_expr")
    shape = registry.by_type_name["Variant"]
    result = translate_query(
        shape,
        root_field_node(
            "{ variants(where: {curationStatus: {in: [CURATED, UNREVIEWED],"
            " notIn: [CONFIRMED]}}) { iri } }"
        ),
        registry,
    )
    rendered = result.query.render()
    assert (
        'FILTER(?curationStatus IN ("curated", "unreviewed")'
        ' && !(?curationStatus IN ("confirmed")))' in rendered
    )
