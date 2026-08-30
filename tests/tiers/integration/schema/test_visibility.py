"""Schema visibility at build time — ``core/schema/`` + ``core/registry.py`` (ADR-0008).

Integration tier: ``build_schema`` emits root fields per PUBLIC/PROTECTED/EXCLUDED declarations.

Order: protected no-root → public class closure → protected class closure → private override.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastshaql.core.schema import build_schema
from support.schema_helpers import field_shape, object_type

if TYPE_CHECKING:
    from fastshaql.core.registry import ShapeRegistry

# --- Protected no-root ---


def test_build_schema_protected_shape_no_root_field(
    visibility_registry: ShapeRegistry,
) -> None:
    """``PROTECTED`` shapes are registered for traversal but get no root query field."""
    schema = build_schema(visibility_registry)
    query = schema.query_type
    assert query is not None

    assert "auditlogs" not in query.fields
    assert "persons" in query.fields
    assert schema.get_type("AuditLog") is not None

    person = object_type(schema, "Person")
    assert field_shape(person.fields["audit"].type) == (False, False, "AuditLog")


# --- Public class closure ---


def test_build_schema_public_class_closure_root_fields(
    visibility_registry: ShapeRegistry,
) -> None:
    """``graphql:publicClass`` makes subclass-targeted shapes ``PUBLIC`` root candidates."""
    schema = build_schema(visibility_registry)
    query = schema.query_type
    assert query is not None

    assert "dogs" in query.fields
    assert "cats" not in query.fields
    assert schema.get_type("Dog") is not None
    assert schema.get_type("Cat") is None


# --- Protected class closure ---


def test_build_schema_protected_class_closure_no_root_field(
    visibility_registry: ShapeRegistry,
) -> None:
    """``graphql:protectedClass`` makes subclass-targeted shapes ``PROTECTED``: type registered, no root field."""
    schema = build_schema(visibility_registry)
    query = schema.query_type
    assert query is not None

    assert "cars" not in query.fields
    assert schema.get_type("Car") is not None


# --- Private override ---


def test_build_schema_private_shape_no_root_field(
    visibility_registry: ShapeRegistry,
) -> None:
    """``graphql:privateShape`` overrides ``graphql:publicShape`` — no root field or type."""
    schema = build_schema(visibility_registry)
    query = schema.query_type
    assert query is not None

    assert "secrets" not in query.fields
    assert schema.get_type("Secret") is None
