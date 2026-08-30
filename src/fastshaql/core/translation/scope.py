"""Translation scope — mutable accumulator for one nesting level.

Carries SPARQL variables and projections through the recursive selection walk.
Shared by :mod:`query` (selection translation) and :mod:`filters` (top-level
``where`` translation).
"""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from .variables import VariableAllocator, VariableMap

if TYPE_CHECKING:
    from rdflib import Variable

    from fastshaql.core.registry import ShapeRegistry


@dataclasses.dataclass
class TranslationScope:
    """Mutable accumulator for one nesting level of translation.

    Relationship children construct their own :class:`TranslationScope` in
    :func:`~fastshaql.core.translation.selection.translate_selection`.
    """

    subject: Variable
    """SPARQL variable for the current subject."""

    allocator: VariableAllocator
    """Scoped variable allocator for the current operation."""

    registry: ShapeRegistry
    """Shape lookup for nested relationship traversal."""

    projection: list[Variable] = dataclasses.field(default_factory=list)
    """Accumulator for projected SPARQL variables."""

    _projection_seen: set[Variable] = dataclasses.field(default_factory=set, repr=False)
    """Set of variables that have been projected."""

    fields: dict[str, Variable] = dataclasses.field(default_factory=dict)
    """Scalar field name → bound variable at this nesting level."""

    relationships: dict[str, tuple[Variable, VariableMap]] = dataclasses.field(
        default_factory=dict
    )
    """Relationship field name → (child subject variable, child map)."""

    lang_tags: tuple[str, ...] = ()
    """Language preference chain for language-accepting bindings (ADR-0012):
    the request's chain, inherited by child scopes."""

    def append_projection(self, var: Variable) -> None:
        """Append *var* to :attr:`projection` once."""
        if var in self._projection_seen:
            return  # pragma: no cover — VariableAllocator guarantees unique variables
        self._projection_seen.add(var)
        self.projection.append(var)

    def var_map(self) -> VariableMap:
        """Build a :class:`VariableMap` snapshot of this scope."""
        return VariableMap(
            subject_var=self.subject,
            fields=self.fields,
            relationships=self.relationships,
        )
