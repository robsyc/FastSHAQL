"""Root emission for derived targets — ``translate_query`` target dispatch (ADR-0016).

Integration tier: the root ``rdf:type`` triple is replaced by the target
expression's lowering when ``target_expr`` is set; pagination and ``where``
filters compose unchanged (the emission sits in ``parts.entity`` inside the
ADR-0010 inner sub-SELECT).
"""

from __future__ import annotations

import dataclasses

import pytest
from rdflib.namespace import RDFS

from fastshaql.core.ir.node_expr import InstancesOfNodeExpr, PathValuesNodeExpr
from fastshaql.core.ir.shacl_path import InversePath, PredicatePath
from fastshaql.core.registry import ShapeRegistry
from fastshaql.core.translation import translate_query
from support.builders import EX, node_shape, scalar_property
from support.graphql_utils import root_field_node

_SUBCLASS_STAR = f"a/<{RDFS.subClassOf}>*"


def _targeted_shape(target_expr):
    return dataclasses.replace(
        node_shape(
            "Variant",
            target_class=None,
            property_shapes={
                "label": scalar_property("label", min_count=1, max_count=1)
            },
        ),
        target_expr=target_expr,
    )


def test_root_emission_instances_of_subclass_closing() -> None:
    registry = ShapeRegistry(
        [_targeted_shape(InstancesOfNodeExpr(classes=(EX + "Variant",)))]
    )
    result = translate_query(
        registry.by_type_name["Variant"],
        root_field_node("{ variants { label } }"),
        registry,
    )
    golden = f"""SELECT ?iri ?label
WHERE {{
  ?iri {_SUBCLASS_STAR} <http://example.org/Variant> .
  ?iri <http://example.org/label> ?label .
}}"""
    assert result.query.render() == golden


def test_root_emission_instances_of_list_binds_class_values() -> None:
    registry = ShapeRegistry(
        [
            _targeted_shape(
                InstancesOfNodeExpr(classes=(EX + "Substitution", EX + "Deletion"))
            )
        ]
    )
    result = translate_query(
        registry.by_type_name["Variant"],
        root_field_node("{ variants { label } }"),
        registry,
    )
    golden = f"""SELECT ?iri ?label
WHERE {{
  ?iri {_SUBCLASS_STAR} ?_class_iri .
  VALUES ?_class_iri {{
    <http://example.org/Substitution>
    <http://example.org/Deletion>
  }}
  ?iri <http://example.org/label> ?label .
}}"""
    assert result.query.render() == golden


def test_root_emission_path_values_focus_is_shape_iri() -> None:
    """``pathValues`` at target position evaluates the path at the shape IRI
    (spec-faithful, usually empty)."""
    registry = ShapeRegistry(
        [
            _targeted_shape(
                PathValuesNodeExpr(path=InversePath(PredicatePath(RDFS.subClassOf)))
            )
        ]
    )
    result = translate_query(
        registry.by_type_name["Variant"],
        root_field_node("{ variants { label } }"),
        registry,
    )
    golden = f"""SELECT ?iri ?label
WHERE {{
  <http://example.org/VariantShape> ^<{RDFS.subClassOf}> ?iri .
  ?iri <http://example.org/label> ?label .
}}"""
    assert result.query.render() == golden


def test_root_emission_composes_with_pagination() -> None:
    """The target emission sits inside the ADR-0010 inner sub-SELECT."""
    registry = ShapeRegistry(
        [_targeted_shape(InstancesOfNodeExpr(classes=(EX + "Variant",)))]
    )
    result = translate_query(
        registry.by_type_name["Variant"],
        root_field_node("{ variants(limit: 2) { label } }"),
        registry,
    )
    rendered = result.query.render()
    assert "SELECT DISTINCT ?iri" in rendered
    assert f"?iri {_SUBCLASS_STAR} <http://example.org/Variant> ." in rendered
    assert "LIMIT 2" in rendered


def test_root_emission_implicit_class_target_uses_shape_iri() -> None:
    """An implicit class target (Core §3.1.3.3) lowers through the
    ``instancesOf`` arm at the shape's own IRI — identical emission."""
    shape = dataclasses.replace(
        node_shape(
            "Change",
            target_class=None,
            property_shapes={
                "label": scalar_property("label", min_count=1, max_count=1)
            },
        ),
        target_expr=InstancesOfNodeExpr(classes=(EX + "Change",)),
    )
    registry = ShapeRegistry([shape])
    result = translate_query(
        registry.by_type_name["Change"],
        root_field_node("{ changes { label } }"),
        registry,
    )
    golden = f"""SELECT ?iri ?label
WHERE {{
  ?iri {_SUBCLASS_STAR} <http://example.org/Change> .
  ?iri <http://example.org/label> ?label .
}}"""
    assert result.query.render() == golden


def test_translate_raises_on_shape_without_any_target() -> None:
    shape = node_shape("Orphan", target_class=None)
    registry = ShapeRegistry([shape])
    with pytest.raises(ValueError, match="no supported target"):
        translate_query(shape, root_field_node("{ orphans { label } }"), registry)
