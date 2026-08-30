"""ShapeRegistry lookup helpers — ``core/registry.py``.

Unit tier: ``resolve_relationship_target`` success and error paths with
hand-built registries, and visibility-scoped shape lists.

Order: relationship target resolution (success + errors) → visibility scoping.
"""

from __future__ import annotations

import dataclasses

import pytest

from fastshaql.core.ir.node_expr import InstancesOfNodeExpr
from fastshaql.core.registry import ShapeRegistry
from support.builders import EX, node_shape, relationship_property

# --- resolve_relationship_target ---


def test_resolve_relationship_target(relationship_registry) -> None:
    person = relationship_registry.by_type_name["Person"]
    employer = person.property_shapes["employer"]
    target = relationship_registry.resolve_relationship_target(employer)
    assert target.graphql_type_name == "Company"


def test_resolve_relationship_target_missing_iri(relationship_registry) -> None:
    person = relationship_registry.by_type_name["Person"]
    broken = dataclasses.replace(
        person.property_shapes["employer"],
        value_shape_iri=None,
    )
    with pytest.raises(ValueError, match="no resolved value_shape_iri"):
        relationship_registry.resolve_relationship_target(broken, field_name="employer")


def test_resolve_relationship_target_unknown_shape() -> None:
    registry = ShapeRegistry(
        shapes=[
            node_shape(
                "Person",
                property_shapes={
                    "employer": relationship_property(
                        "employer",
                        EX + "MissingShape",
                        min_count=0,
                        max_count=1,
                    ),
                },
            )
        ]
    )
    person = registry.by_type_name["Person"]
    with pytest.raises(ValueError, match="unknown shape"):
        registry.resolve_relationship_target(person.property_shapes["employer"])


# --- visibility scoping ---


def test_visible_shapes_excludes_private_and_closed_world(
    visibility_registry: ShapeRegistry,
) -> None:
    """``visible_shapes`` returns PUBLIC and PROTECTED shapes only."""
    type_names = {s.graphql_type_name for s in visibility_registry.visible_shapes()}
    assert type_names == {"Person", "Address", "AuditLog", "Dog", "Car"}


def test_public_root_shapes(visibility_registry: ShapeRegistry) -> None:
    """Root query fields require PUBLIC visibility and a ``sh:targetClass``."""
    type_names = {s.graphql_type_name for s in visibility_registry.public_root_shapes()}
    assert type_names == {"Person", "Address", "Dog"}


def test_public_root_shapes_include_derived_target_shapes() -> None:
    """A ``sh:targetNode`` shape publishes like a class-targeted one (ADR-0016)."""
    registry = ShapeRegistry(
        [
            node_shape("ClassThing"),
            dataclasses.replace(
                node_shape("ExprThing", target_class=None),
                target_expr=InstancesOfNodeExpr(classes=(EX + "Thing",)),
            ),
        ]
    )
    type_names = {s.graphql_type_name for s in registry.public_root_shapes()}
    assert type_names == {"ClassThing", "ExprThing"}


# --- Duplicate class targets ---


def test_duplicate_target_class_raises() -> None:
    """Two shapes targeting the same class raise ``ValueError``."""
    shape_a = node_shape("ThingA", target_class=EX + "Thing")
    shape_b = node_shape("ThingB", target_class=EX + "Thing")
    with pytest.raises(ValueError, match="Duplicate class target"):
        ShapeRegistry([shape_a, shape_b])


def test_duplicate_implicit_and_explicit_class_target_raises() -> None:
    """An implicit-class shape and a ``sh:targetClass`` shape claiming the
    same class IRI reject — the shape *is* the class there (§3.1.3.3)."""
    shape_a = node_shape(
        "ThingA",
        target_class=None,
        target_expr=InstancesOfNodeExpr(classes=(EX + "ThingAShape",)),
        implicit_class=True,
    )
    shape_b = node_shape("ThingB", target_class=EX + "ThingAShape")
    with pytest.raises(ValueError, match="Duplicate class target"):
        ShapeRegistry([shape_a, shape_b])


def test_explicit_self_instances_of_target_is_not_class_indexed() -> None:
    """ADR-0016: an explicit ``sh:targetNode`` shape is never class-indexed —
    even when its expression happens to enumerate the shape's own instances
    (structurally identical to the implicit target's lowering). The flag is
    recorded at parse time, not re-derived from the expression."""
    shape = node_shape(
        "Thing",
        target_class=None,
        target_expr=InstancesOfNodeExpr(classes=(EX + "ThingShape",)),
    )
    assert shape.indexed_class is None
    registry = ShapeRegistry([shape])
    assert EX + "ThingShape" not in registry.by_target_class
