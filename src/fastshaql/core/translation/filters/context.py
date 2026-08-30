"""Concrete FilterContext strategies for root-level and EXISTS-internal translation."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from rdflib import Variable

from ..joins import relationship_join_patterns
from ..patterns import scalar_bind_patterns
from .exists import build_exists_expr, translate_exists_relationship
from .naming import rf_var_name

if TYPE_CHECKING:
    from graphql.language.ast import ObjectValueNode

    from fastshaql.core.ir import PropertyShapeIR
    from fastshaql.core.registry import ShapeRegistry
    from fastshaql.core.sparql import Expression, Pattern

    from ..scope import TranslationScope
    from ..variables import VariableMap


@dataclasses.dataclass
class RootFilterContext:
    """Root-level filter translation — flat or paginated inner sub-SELECT.

    ``isolated=True`` (pagination inner sub-SELECT) re-emits bind triples for
    selected fields so filters constrain the paginated entity set (ADR-0010).
    """

    subject: Variable
    """Subject variable for the root scope."""
    fields: dict[str, Variable]
    """GraphQL field name → bound SPARQL variable for scalars."""
    relationships: dict[str, tuple[Variable, VariableMap]]
    """GraphQL field name → (join variable, child variable map)."""
    isolated: bool = False
    """``True`` when emitting inside the pagination inner sub-SELECT."""
    selected: frozenset[str] = frozenset()
    """Field names whose bind triples must be re-emitted when isolated."""
    lang_tags: tuple[str, ...] = ()
    """Language preference chain for literal filtering (ADR-0012)."""

    @classmethod
    def from_scope(
        cls,
        scope: TranslationScope,
        *,
        isolated: bool,
        selected: frozenset[str],
    ) -> RootFilterContext:
        """Build a context sharing *scope*'s live variable maps."""
        return cls(
            subject=scope.subject,
            fields=scope.fields,
            relationships=scope.relationships,
            isolated=isolated,
            selected=selected,
            lang_tags=scope.lang_tags,
        )

    def _reemit_bind(self, field_name: str) -> bool:
        """Whether bind triples must be re-emitted for a selected field."""
        return self.isolated and field_name in self.selected

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
        if not self._reemit_bind(field_name):
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
        child_shape = registry.resolve_relationship_target(prop, field_name=field_name)
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
        if not self._reemit_bind(field_name):
            return [], exists_expr
        join_patterns = relationship_join_patterns(
            self.subject, join_var, prop, emit_type_triple=True
        )
        return join_patterns, exists_expr


@dataclasses.dataclass
class ExistsContext:
    """Inside a FILTER EXISTS block — fresh variables with triple emission.

    Doubles as the EXISTS scope object passed through ``exists.py`` builders.
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
        child_shape = registry.resolve_relationship_target(prop, field_name=field_name)
        return translate_exists_relationship(
            self, field_name, node, prop, child_shape, registry
        )
