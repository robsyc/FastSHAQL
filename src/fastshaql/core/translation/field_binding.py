"""Unified field binding for selection walk and filter promotion.

Single entry point for scalar triple emission (including language preference)
and relationship join patterns. Selection translation and promotion pre-scan
both call here with different ``project`` / ``bound`` flags (ADR-0009).

Note: SPARQL ``BindPattern`` (``core/sparql/patterns.py``) is unrelated —
that node renders ``BIND(expr AS ?var)`` for derived fields (ADR-0015).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR, ValueType

from .joins import relationship_join_patterns
from .patterns import scalar_bind_patterns, wrap_if_unbound
from .scope import TranslationScope
from .variables import VariableMap

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rdflib import Variable

    from fastshaql.core.sparql import Pattern


def field_is_bound(
    prop: PropertyShapeIR,
    field_name: str,
    promoted: frozenset[str],
) -> bool:
    """Return whether a field's triples are bound (not OPTIONAL)."""
    return prop.kind.is_required or field_name in promoted


def bind_scalar_field(
    field_name: str,
    prop: PropertyShapeIR,
    scope: TranslationScope,
    *,
    project: bool,
    bound: bool,
) -> tuple[Variable, list[Pattern]]:
    """Bind a scalar property and register it on *scope*."""
    var = scope.allocator.allocate(field_name)
    patterns = scalar_bind_patterns(
        prop,
        var,
        subject=scope.subject,
        lang_tags=scope.lang_tags,
        bound=bound,
    )
    if project:
        scope.append_projection(var)
    scope.fields[field_name] = var
    return var, patterns


def _promote_relationship_field(
    field_name: str,
    prop: PropertyShapeIR,
    scope: TranslationScope,
) -> list[Pattern]:
    """Bind a promoted relationship field omitted from the selection."""
    scope.allocator.push_scope(field_name)
    child_subject = scope.allocator.allocate("iri")
    join_patterns = relationship_join_patterns(
        scope.subject,
        child_subject,
        prop,
        emit_type_triple=False,
    )
    scope.allocator.pop_scope()
    scope.relationships[field_name] = (
        child_subject,
        VariableMap(subject_var=child_subject, fields={}, relationships={}),
    )
    return join_patterns


def begin_relationship_selection(
    field_name: str,
    prop: PropertyShapeIR,
    scope: TranslationScope,
) -> tuple[Variable, list[Pattern], TranslationScope]:
    """Open a relationship scope for selection translation."""
    scope.allocator.push_scope(field_name)
    child_subject = scope.allocator.allocate("iri")
    join_patterns = relationship_join_patterns(
        scope.subject,
        child_subject,
        prop,
        emit_type_triple=True,
    )
    child_scope = TranslationScope(
        subject=child_subject,
        allocator=scope.allocator,
        registry=scope.registry,
        lang_tags=scope.lang_tags,
    )
    child_scope.append_projection(child_subject)
    return child_subject, join_patterns, child_scope


def complete_relationship_selection(
    field_name: str,
    child_subject: Variable,
    child_scope: TranslationScope,
    scope: TranslationScope,
    patterns: Sequence[Pattern],
    *,
    bound: bool,
) -> list[Pattern]:
    """Register a relationship binding and return wrapped selection patterns."""
    scope.relationships[field_name] = (
        child_subject,
        child_scope.var_map(),
    )
    wrapped = wrap_if_unbound(patterns, bound=bound)
    for var in child_scope.projection:
        scope.append_projection(var)
    scope.allocator.pop_scope()
    return wrapped


def bind_promoted_fields(
    shape: NodeShapeIR,
    scope: TranslationScope,
    promoted: frozenset[str],
    selected: frozenset[str],
) -> list[Pattern]:
    """Emit bound triples for promoted fields omitted from the selection."""
    patterns: list[Pattern] = []
    for field_name in promoted:
        if field_name in selected:
            continue
        prop = shape.property_shapes.get(field_name)
        if prop is None:
            continue  # pragma: no cover — promoted names guaranteed in property_shapes
        match prop.value_type:
            case ValueType.RELATIONSHIP:
                patterns.extend(_promote_relationship_field(field_name, prop, scope))
            # ``case`` fall-through below the last arm is unreachable: the
            # ValueType union is closed (no wildcard arm).
            case ValueType.ENUM | ValueType.SCALAR:  # pragma: no branch — closed union
                _, scalar_patterns = bind_scalar_field(
                    field_name, prop, scope, project=False, bound=True
                )
                patterns.extend(scalar_patterns)
    return patterns
