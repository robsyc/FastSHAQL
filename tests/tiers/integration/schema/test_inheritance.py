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


def test_workshop_filter_includes_inherited_scalar_and_relationship(
    inheritance_registry: ShapeRegistry,
) -> None:
    schema = build_schema(inheritance_registry)
    workshop_filter = input_type(schema, "WorkshopFilter")

    assert "heldOn" in workshop_filter.fields
    assert input_field_base(workshop_filter.fields["heldOn"].type) == "DateTimeFilter"
    assert "host" in workshop_filter.fields


def test_workshop_object_type_has_inherited_fields(
    inheritance_registry: ShapeRegistry,
) -> None:
    schema = build_schema(inheritance_registry)
    workshop = object_type(schema, "Workshop")

    assert "heldOn" in workshop.fields
    assert field_shape(workshop.fields["heldOn"].type) == (True, False, "String")
    assert "host" in workshop.fields
    _, _, rel_base = field_shape(workshop.fields["host"].type)
    assert rel_base == "Person"


def test_inherited_enum_field_and_filter(inheritance_registry: ShapeRegistry) -> None:
    schema = build_schema(inheritance_registry)
    child = inheritance_registry.by_type_name["Workshop"]
    fmt = child.property_shapes["format"]
    assert fmt.value_type is ValueType.ENUM

    workshop = object_type(schema, "Workshop")
    assert "format" in workshop.fields

    workshop_filter = input_type(schema, "WorkshopFilter")
    assert "format" in workshop_filter.fields
    assert (
        input_field_base(workshop_filter.fields["format"].type)
        == "WorkshopFormatFilter"
    )
