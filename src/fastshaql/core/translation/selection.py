"""GraphQL field selection → SPARQL graph patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING

from graphql.language.ast import (
    FieldNode,
    FragmentSpreadNode,
    InlineFragmentNode,
)

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR, ValueType
from fastshaql.core.kernel.constants import IRI_FIELD

from .field_binding import (
    FieldBindings,
    begin_relationship_selection,
    bind_scalar_field,
    complete_relationship_selection,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastshaql.core.sparql import Pattern

    from .scope import TranslationScope


def iter_field_selections(field_node: FieldNode) -> Iterator[FieldNode]:
    """Yield ``FieldNode`` children from a selection set."""
    if field_node.selection_set is None:
        return  # pragma: no cover — object-type fields require selection set
    for sel in field_node.selection_set.selections:
        if isinstance(sel, FieldNode):
            yield sel
            continue
        kind = type(sel).__name__
        if isinstance(sel, (FragmentSpreadNode, InlineFragmentNode)):
            raise TypeError(f"GraphQL fragments are not supported (got {kind!r})")
        raise TypeError(
            f"Unsupported selection kind {kind!r}"
        )  # pragma: no cover — AST is closed union (FieldNode/FragmentSpread/InlineFragment)


def translate_selection(
    selection: FieldNode,
    shape: NodeShapeIR,
    scope: TranslationScope,
    bindings: FieldBindings | None = None,
) -> list[Pattern]:
    """Translate a single field selection into SPARQL graph pattern(s).

    *bindings* carries this level's promotion state (ADR-0009); the field is
    recorded as selected and its bound-ness consulted there. Child selections
    recurse without it — promotion scope is per level.
    """
    if bindings is None:
        bindings = FieldBindings()
    field_name = selection.name.value
    bindings.note_selected(field_name)
    if field_name == IRI_FIELD:
        scope.fields[IRI_FIELD] = scope.subject
        return []
    try:
        prop = shape.property_shapes[field_name]
    except KeyError as exc:
        raise ValueError(
            f"Unknown field {field_name!r} on shape {shape.graphql_type_name!r}"
        ) from exc

    match prop.value_type:
        case ValueType.RELATIONSHIP:
            return _translate_relationship_selection(
                selection, prop, scope, field_name, bindings
            )
        # ``case`` fall-through below the last arm is unreachable: the
        # ValueType union is closed (no wildcard arm).
        case ValueType.ENUM | ValueType.SCALAR:  # pragma: no branch — closed union
            _, patterns = bind_scalar_field(
                field_name,
                prop,
                scope,
                project=True,
                bound=bindings.field_is_bound(prop, field_name),
            )
            return patterns


def _translate_relationship_selection(
    selection: FieldNode,
    prop: PropertyShapeIR,
    scope: TranslationScope,
    field_name: str,
    bindings: FieldBindings,
) -> list[Pattern]:
    """Translate a relationship field selection and recurse into child fields."""
    child_shape = scope.registry.resolve_relationship_target(prop)
    child_subject, join_patterns, child_scope = begin_relationship_selection(
        field_name, prop, scope
    )
    child_patterns: list[Pattern] = list(join_patterns)
    for child_selection in iter_field_selections(selection):
        child_patterns.extend(
            translate_selection(child_selection, child_shape, child_scope)
        )
    return complete_relationship_selection(
        field_name,
        child_subject,
        child_scope,
        scope,
        child_patterns,
        bound=bindings.field_is_bound(prop, field_name),
    )
