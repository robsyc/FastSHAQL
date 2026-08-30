"""FilterContext protocol — the strategy interface for ``where`` translation.

Extracted from ``context.py`` so the concrete contexts, the EXISTS builder
(``exists.py``), and field dispatch (``fields.py``) all depend on the
interface, not on each other (breaks the context ↔ exists import cycle).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from graphql.language.ast import ObjectValueNode
    from rdflib import Variable

    from fastshaql.core.ir import PropertyShapeIR
    from fastshaql.core.registry import ShapeRegistry
    from fastshaql.core.sparql import Expression, Pattern


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
