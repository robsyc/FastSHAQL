"""Node shape inheritance — schema integration (ADR-0005).

Integration tier: inherited fields appear on object types and filter inputs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastshaql.core.ir import ValueType
from fastshaql.core.schema import build_schema
from support.schema_helpers import (
    field_shape,
    input_field_base,
    input_type,
    object_type,
)

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry


def test_manager_filter_includes_inherited_scalar_and_relationship(
    inheritance_registry: ShapeRegistry,
) -> None:
    schema = build_schema(inheritance_registry)
    manager_filter = input_type(schema, "ManagerFilter")

    assert "employeeId" in manager_filter.fields
    assert input_field_base(manager_filter.fields["employeeId"].type) == "StringFilter"
    assert "workLocation" in manager_filter.fields


def test_manager_object_type_has_inherited_fields(
    inheritance_registry: ShapeRegistry,
) -> None:
    schema = build_schema(inheritance_registry)
    manager = object_type(schema, "Manager")

    assert "employeeId" in manager.fields
    assert field_shape(manager.fields["employeeId"].type) == (True, False, "String")
    assert "workLocation" in manager.fields
    _, _, rel_base = field_shape(manager.fields["workLocation"].type)
    assert rel_base == "Location"


def test_inherited_enum_field_and_filter(inheritance_registry: ShapeRegistry) -> None:
    schema = build_schema(inheritance_registry)
    child = inheritance_registry.by_type_name["StatusChild"]
    status = child.property_shapes["status"]
    assert status.value_type is ValueType.ENUM

    status_child = object_type(schema, "StatusChild")
    assert "status" in status_child.fields

    status_filter = input_type(schema, "StatusChildFilter")
    assert "status" in status_filter.fields
    assert (
        input_field_base(status_filter.fields["status"].type)
        == "StatusChildStatusFilter"
    )
