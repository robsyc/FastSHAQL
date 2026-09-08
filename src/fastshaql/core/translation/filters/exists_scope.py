"""The two FilterContext strategies and the FILTER EXISTS builder (ADR-0009).

The :class:`FilterContext` Protocol lives here beside its only
implementations — :class:`RootFilterContext` (root level, flat or the
paginated inner sub-SELECT) and :class:`ExistsContext` (inside a
``FILTER EXISTS`` block) — together with the EXISTS construction they share
and the ``_rf_`` variable naming that namespaces relationship-filter
variables.
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Protocol

from rdflib import Variable

from fastshaql.core.sparql import (
    ExistsExpr,
    Expression,
    FilterPattern,
    GroupPattern,
    Pattern,
)

from ..joins import relationship_join_patterns, relationship_type_patterns
from ..patterns import scalar_bind_patterns
from .where import translate_fields

if TYPE_CHECKING:
    from graphql.language.ast import ObjectValueNode

    from fastshaql.core.ir import NodeShapeIR, PropertyShapeIR
    from fastshaql.core.registry import ShapeRegistry

    from ..field_binding import FieldBindings
    from ..scope import TranslationScope
    from ..variables import VariableMap


class FilterContext(Protocol):
    """Strategy adapting field dispatch to root-level or EXISTS-internal scope."""

    subject: Variable
    """Subject variable for the scope's triple patterns."""
    lang_tags: tuple[str, ...]
    """Language preference chain for literal filtering (ADR-0012)."""

    def scalar_var(
        self, field_name: str, prop: PropertyShapeIR
    ) -> tuple[Variable, list[Pattern]]:
        """Return the SPARQL variable and any emitted triple/filter patterns."""
        ...  # pragma: no cover — Protocol stub

    def translate_relationship(
        self,
        field_name: str,
        node: ObjectValueNode,
        prop: PropertyShapeIR,
        registry: ShapeRegistry,
    ) -> tuple[list[Pattern], Expression | None]:
        """Translate a relationship filter into patterns and/or an expression."""
        ...  # pragma: no cover — Protocol stub


# --- Variable naming for FILTER EXISTS internal scopes ---

# ``_rf_`` abbreviates **relationship-filter** — variables allocated inside
# ``FILTER EXISTS`` blocks for relationship filter conditions. They are
# namespaced separately from selection-walk variables (see ADR-0009).


def rf_var_name(prefix: str, field_name: str) -> str:
    """Return a relationship-filter variable name inside an EXISTS block."""
    if prefix:
        return f"_rf_{prefix}_{field_name}"
    return f"_rf_{field_name}"  # pragma: no cover — rf_prefix invariant: always seeded and grown non-empty


def exists_join_var_name(prefix: str, field_name: str) -> str:
    """Return the join subject variable for a nested relationship in EXISTS."""
    if prefix:
        return f"{prefix}_{field_name}_iri"
    return f"{field_name}_iri"  # pragma: no cover — rf_prefix invariant: always seeded and grown non-empty


# --- FILTER EXISTS construction for relationship filters ---


def build_exists_expr(
    node: ObjectValueNode,
    shape: NodeShapeIR,
    relationship_prop: PropertyShapeIR,
    registry: ShapeRegistry,
    scope: ExistsContext,
) -> ExistsExpr:
    """Build an ``EXISTS { ... }`` expression for a relationship filter."""
    inner = exists_inner_patterns(node, shape, relationship_prop, registry, scope)
    return ExistsExpr(GroupPattern(tuple(inner)))


def exists_inner_patterns(
    node: ObjectValueNode,
    shape: NodeShapeIR,
    relationship_prop: PropertyShapeIR,
    registry: ShapeRegistry,
    scope: ExistsContext,
) -> list[Pattern]:
    """Build pattern list inside an ``EXISTS { ... }`` block."""
    child_patterns, child_expr = translate_fields(node, shape, scope, registry)

    patterns: list[Pattern] = []
    patterns.extend(relationship_type_patterns(scope.subject, relationship_prop))
    patterns.extend(child_patterns)
    if child_expr is not None:
        patterns.append(FilterPattern(child_expr))
    return patterns


def translate_exists_relationship(
    ctx: ExistsContext,
    field_name: str,
    node: ObjectValueNode,
    prop: PropertyShapeIR,
    child_shape: NodeShapeIR,
    registry: ShapeRegistry,
) -> tuple[list[Pattern], Expression | None]:
    """Translate a nested relationship filter inside an EXISTS block."""
    child_subject = Variable(exists_join_var_name(ctx.rf_prefix, field_name))
    join_patterns = relationship_join_patterns(ctx.subject, child_subject, prop)
    child_scope = ctx.child_scope(child_subject, field_name)
    exists_expr = build_exists_expr(node, child_shape, prop, registry, child_scope)
    return join_patterns, exists_expr


# --- The two concrete strategies ---


@dataclasses.dataclass
class RootFilterContext:
    """Root-level filter translation — flat or paginated inner sub-SELECT.

    The :class:`FieldBindings` promotion state owns the isolation flag and
    the selected set: ``bindings.isolated`` (pagination inner sub-SELECT,
    ADR-0010) re-emits bind triples for selected fields so filters constrain
    the paginated entity set.
    """

    subject: Variable
    """Subject variable for the root scope."""
    fields: dict[str, Variable]
    """GraphQL field name → bound SPARQL variable for scalars."""
    relationships: dict[str, tuple[Variable, VariableMap]]
    """GraphQL field name → (join variable, child variable map)."""
    bindings: FieldBindings
    """Promotion state for the root translation level (ADR-0009/0010)."""
    lang_tags: tuple[str, ...] = ()
    """Language preference chain for literal filtering (ADR-0012)."""

    @classmethod
    def from_scope(
        cls,
        scope: TranslationScope,
        *,
        bindings: FieldBindings,
    ) -> RootFilterContext:
        """Build a context sharing *scope*'s live variable maps."""
        return cls(
            subject=scope.subject,
            fields=scope.fields,
            relationships=scope.relationships,
            bindings=bindings,
            lang_tags=scope.lang_tags,
        )

    def scalar_var(
        self, field_name: str, prop: PropertyShapeIR
    ) -> tuple[Variable, list[Pattern]]:
        """Return the bound scalar variable, re-emitting bind triples when isolated."""
        try:
            var = self.fields[field_name]
        except KeyError as exc:  # pragma: no cover — promotion invariant guarantees field is pre-bound
            raise ValueError(
                f"Filter field {field_name!r} has no bound variable"
            ) from exc
        if not self.bindings.reemit_bind(field_name):
            return var, []
        patterns = scalar_bind_patterns(
            prop,
            var,
            subject=self.subject,
            lang_tags=self.lang_tags,
            bound=True,
        )
        return var, patterns

    def translate_relationship(
        self,
        field_name: str,
        node: ObjectValueNode,
        prop: PropertyShapeIR,
        registry: ShapeRegistry,
    ) -> tuple[list[Pattern], Expression | None]:
        """Build a ``FILTER EXISTS`` expression, emitting join triples when isolated."""
        if not node.fields:
            return [], None
        child_shape = registry.resolve_relationship_target(prop)
        try:
            join_var = self.relationships[field_name][0]
        except KeyError as exc:  # pragma: no cover — promotion invariant guarantees relationship is pre-bound
            raise ValueError(
                f"Relationship filter {field_name!r} requires a bound join variable"
            ) from exc
        scope = ExistsContext(
            subject=join_var, rf_prefix=field_name, lang_tags=self.lang_tags
        )
        exists_expr = build_exists_expr(node, child_shape, prop, registry, scope)
        if not self.bindings.reemit_bind(field_name):
            return [], exists_expr
        join_patterns = relationship_join_patterns(
            self.subject, join_var, prop, emit_type_triple=True
        )
        return join_patterns, exists_expr


@dataclasses.dataclass
class ExistsContext:
    """Inside a FILTER EXISTS block — fresh variables with triple emission.

    Doubles as the EXISTS scope object passed through the EXISTS builders.
    """

    subject: Variable
    """Subject variable inside the EXISTS block."""
    rf_prefix: str
    """Relationship-filter prefix chain namespacing ``_rf_*`` variables."""

    lang_tags: tuple[str, ...] = ()
    """Language preference chain for literal filtering (ADR-0012)."""

    def child_scope(self, child_subject: Variable, field_name: str) -> ExistsContext:
        """Nested EXISTS scope — *field_name* appended to the prefix chain."""
        prefix = f"{self.rf_prefix}_{field_name}" if self.rf_prefix else field_name
        return ExistsContext(
            subject=child_subject, rf_prefix=prefix, lang_tags=self.lang_tags
        )

    def scalar_var(
        self, field_name: str, prop: PropertyShapeIR
    ) -> tuple[Variable, list[Pattern]]:
        """Allocate a fresh ``_rf_*`` variable and emit its bind patterns."""
        var = Variable(rf_var_name(self.rf_prefix, field_name))
        patterns = scalar_bind_patterns(
            prop,
            var,
            subject=self.subject,
            lang_tags=self.lang_tags,
            bound=True,
        )
        return var, patterns

    def translate_relationship(
        self,
        field_name: str,
        node: ObjectValueNode,
        prop: PropertyShapeIR,
        registry: ShapeRegistry,
    ) -> tuple[list[Pattern], Expression | None]:
        """Recursively translate a nested relationship within the EXISTS block."""
        if not node.fields:
            return [], None
        child_shape = registry.resolve_relationship_target(prop)
        return translate_exists_relationship(
            self, field_name, node, prop, child_shape, registry
        )
