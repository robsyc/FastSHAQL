"""GraphQL field selection → SPARQL graph patterns."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from graphql.language.ast import (
    FieldNode,
    FragmentSpreadNode,
    InlineFragmentNode,
    NamedTypeNode,
)
from rdflib import URIRef

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR, ValueType
from fastshaql.core.kernel.constants import IRI_FIELD, TYPENAME_FIELD

from .field_binding import (
    FieldBindings,
    begin_relationship_selection,
    begin_union_selection,
    bind_scalar_field,
    complete_relationship_selection,
    complete_union_selection,
)
from .joins import member_lane_patterns, membership_guard
from .scope import TranslationScope
from .variables import MemberBinding

if TYPE_CHECKING:
    from collections.abc import Iterator, Sequence

    from graphql.language.ast import SelectionNode

    from fastshaql.core.sparql import Pattern


def iter_field_selections(
    field_node: FieldNode | InlineFragmentNode, type_name: str
) -> Iterator[FieldNode]:
    """Yield ``FieldNode`` children of a field's or inline fragment's
    selection set, flattening nested inline fragments that apply here — no
    condition, or one naming *type_name* (ADR-0026); ``__typename``
    meta-fields are skipped (the executor resolves them). Union fields do
    not use this walker: their fragments route members instead of
    flattening."""

    if field_node.selection_set is None:
        return  # pragma: no cover — object-type selections require selection set
    yield from _field_selections(field_node.selection_set.selections, type_name)


def _field_selections(
    selections: Sequence[SelectionNode], type_name: str
) -> Iterator[FieldNode]:
    for sel in selections:
        if isinstance(sel, FieldNode):
            if sel.name.value == TYPENAME_FIELD:
                continue
            reject_directives(
                sel, where=f"field {sel.name.value!r} inside a {type_name!r} selection"
            )
            yield sel
            continue
        if isinstance(sel, InlineFragmentNode):
            reject_directives(
                sel, where=f"an inline fragment inside a {type_name!r} selection"
            )
            type_condition = cast(NamedTypeNode | None, sel.type_condition)
            if type_condition is not None and type_condition.name.value != type_name:
                raise ValueError(
                    f"Inline fragment on {type_condition.name.value!r} inside "
                    f"a {type_name!r} selection — the field never returns that type"
                )
            yield from _field_selections(sel.selection_set.selections, type_name)
            continue
        raise TypeError(
            f"GraphQL named fragments are not supported (got {type(sel).__name__!r})"
        )


def reject_directives(node: FieldNode | InlineFragmentNode, *, where: str) -> None:
    """Directives on selections are not consumed — silently ignoring
    ``@include``/``@skip`` would fetch fields the client meant to skip."""
    if node.directives:
        raise TypeError(f"Directives on selections are not supported (on {where})")


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
        case ValueType.RELATIONSHIP if prop.is_polymorphic:
            return _translate_union_selection(
                selection, prop, scope, field_name, bindings
            )
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
    _, join_patterns, child_scope = begin_relationship_selection(
        field_name, prop, scope
    )
    child_patterns: list[Pattern] = list(join_patterns)
    for child_selection in iter_field_selections(
        selection, child_shape.graphql_type_name
    ):
        child_patterns.extend(
            translate_selection(child_selection, child_shape, child_scope)
        )
    return complete_relationship_selection(
        field_name,
        child_scope,
        scope,
        child_patterns,
        bound=bindings.field_is_bound(prop, field_name),
    )


def _translate_union_selection(
    selection: FieldNode,
    prop: PropertyShapeIR,
    scope: TranslationScope,
    field_name: str,
    bindings: FieldBindings,
) -> list[Pattern]:
    """Translate a polymorphic field selection (ADR-0026): the link
    emission, the VALUES membership guard, then one OPTIONAL member lane
    per declared member carrying its type guard and the fragment's branch
    field patterns. Member field variables live in per-member allocator
    scopes (``?block_1_text``) so overlap rows never fight over one name."""
    child_subject, discriminator, join_patterns, child_scope = begin_union_selection(
        field_name, prop, scope
    )
    fragments = _union_fragments(selection, field_name)
    member_shapes = [
        scope.registry.member_shape(member) for member in prop.union_members
    ]
    unknown = set(fragments) - {shape.graphql_type_name for shape in member_shapes}
    if unknown:
        raise ValueError(
            f"inline fragment on non-member type {sorted(unknown)} of union "
            f"field {field_name!r}"
        )
    patterns: list[Pattern] = list(join_patterns)
    patterns.extend(membership_guard(child_subject, discriminator, prop))
    members: list[MemberBinding] = []
    for index, (member, member_shape) in enumerate(
        zip(prop.union_members, member_shapes, strict=True), start=1
    ):
        member_scope = TranslationScope.child(child_subject, scope)
        branch: list[Pattern] = []
        fragment = fragments.get(member_shape.graphql_type_name)
        if fragment is not None:
            scope.allocator.push_scope(str(index))
            for child_selection in iter_field_selections(
                fragment, member_shape.graphql_type_name
            ):
                branch.extend(
                    translate_selection(child_selection, member_shape, member_scope)
                )
            scope.allocator.pop_scope()
        patterns.append(
            member_lane_patterns(child_subject, cast(URIRef, member.class_iri), branch)
        )
        members.append(MemberBinding(member.class_iri, member_scope.var_map()))
        for var in member_scope.projection:
            child_scope.append_projection(var)
    return complete_union_selection(
        field_name,
        child_scope,
        scope,
        patterns,
        tuple(members),
        discriminator,
        bound=bindings.field_is_bound(prop, field_name),
    )


def _union_fragments(
    selection: FieldNode, field_name: str
) -> dict[str, InlineFragmentNode]:
    """Inline fragments of a union selection keyed by type condition
    (ADR-0026). Bare fields (``__typename`` aside) and named spreads reject
    loudly — unions are selectable only through member fragments."""
    fragments: dict[str, InlineFragmentNode] = {}
    if selection.selection_set is None:
        return fragments  # pragma: no cover — union fields require selection set
    for sel in selection.selection_set.selections:
        if isinstance(sel, FieldNode):
            if sel.name.value == TYPENAME_FIELD:
                continue
            raise TypeError(
                f"bare field {sel.name.value!r} on union field {field_name!r} — "
                "select member fields through inline fragments"
            )
        if isinstance(sel, FragmentSpreadNode):
            raise TypeError(
                f"GraphQL named fragments are not supported (got {type(sel).__name__!r})"
            )
        inline = cast(InlineFragmentNode, sel)
        reject_directives(
            inline, where=f"an inline fragment in union field {field_name!r}"
        )
        if inline.type_condition is None:
            raise TypeError(
                f"inline fragment without a type condition on union field "
                f"{field_name!r}"
            )
        type_name = inline.type_condition.name.value
        if type_name in fragments:
            raise ValueError(
                f"two inline fragments on {type_name!r} in union field {field_name!r}"
            )
        fragments[type_name] = inline
    return fragments
