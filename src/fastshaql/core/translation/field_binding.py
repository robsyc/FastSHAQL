"""Unified field binding for selection walk and filter promotion.

Single entry point for scalar triple emission (including language preference)
and relationship join patterns. Selection translation and promotion pre-scan
both call here; :class:`FieldBindings` is the one state object they consult
for bound-ness, promoted-field emission, and sub-SELECT re-emission
(ADR-0009/0010).

Note: SPARQL ``BindPattern`` (``core/sparql/patterns.py``) is unrelated —
that node renders ``BIND(expr AS ?var)`` for derived fields (ADR-0015).
"""

from __future__ import annotations

import dataclasses
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


@dataclasses.dataclass
class FieldBindings:
    """Promotion state for one translation level (ADR-0009/0010).

    Owns the promoted set (fields the ``where`` argument binds as bound
    triples, computed once from that argument via the promotion pre-scan),
    the selected set (fields the selection walk binds), and the pagination
    isolation flag. The query pipeline, the selection walk, and the
    FilterContext strategies consult this object instead of threading
    ``promoted``/``selected``/``isolated``/``bound`` flags. Promotion scope is
    per level: the object never propagates into child selections (ADR-0009).
    """

    promoted: frozenset[str] = frozenset()
    """Field names the root ``where`` argument promotes to bound triples."""
    isolated: bool = False
    """``True`` when filters evaluate inside the pagination sub-SELECT."""
    selected: set[str] = dataclasses.field(default_factory=set)
    """Field names bound by the selection walk at this level."""

    def note_selected(self, field_name: str) -> None:
        """Record a field bound by the selection walk."""
        self.selected.add(field_name)

    def field_is_bound(
        self,
        prop: PropertyShapeIR,
        field_name: str,
    ) -> bool:
        """Return whether a field's triples are bound (not OPTIONAL)."""
        return prop.kind.is_required or field_name in self.promoted

    def reemit_bind(self, field_name: str) -> bool:
        """Whether bind triples must be re-emitted for a selected field
        inside the pagination sub-SELECT (ADR-0010)."""
        return self.isolated and field_name in self.selected

    def bind_promoted_fields(
        self,
        shape: NodeShapeIR,
        scope: TranslationScope,
    ) -> list[Pattern]:
        """Emit bound triples for promoted fields omitted from the selection."""
        patterns: list[Pattern] = []
        for field_name in sorted(self.promoted):
            if field_name in self.selected:
                continue
            prop = shape.property_shapes.get(field_name)
            if prop is None:
                continue  # pragma: no cover — promoted names guaranteed in property_shapes
            match prop.value_type:
                case ValueType.RELATIONSHIP:
                    patterns.extend(
                        _promote_relationship_field(field_name, prop, scope)
                    )
                # ``case`` fall-through below the last arm is unreachable: the
                # ValueType union is closed (no wildcard arm).
                case (
                    ValueType.ENUM | ValueType.SCALAR
                ):  # pragma: no branch — closed union
                    _, scalar_patterns = bind_scalar_field(
                        field_name, prop, scope, project=False, bound=True
                    )
                    patterns.extend(scalar_patterns)
        return patterns

    def assert_promoted_bound(self, scope: TranslationScope) -> None:
        """Invariant (ADR-0009): every field the ``where`` argument references
        owns a bound variable where its FILTER evaluates — selected fields are
        bound by the selection walk, unselected ones by
        :meth:`bind_promoted_fields`; the query pipeline calls this after
        WHERE assembly."""
        bound = scope.fields.keys() | scope.relationships.keys()
        unbound = self.promoted - bound
        if unbound:
            raise AssertionError(
                f"promoted filter fields never bound: {sorted(unbound)}"
            )


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
    join_patterns = relationship_join_patterns(scope.subject, child_subject, prop)
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
