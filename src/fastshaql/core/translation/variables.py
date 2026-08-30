"""Scoped SPARQL variable allocation and translation variable mapping.

See: docs/adr/0013-ast-driven-translation.md
"""

from __future__ import annotations

import dataclasses
from itertools import count
from typing import TYPE_CHECKING

from rdflib import Variable

if TYPE_CHECKING:
    from fastshaql.core.sparql import SelectQuery


@dataclasses.dataclass(frozen=True)
class VariableMap:
    """Maps GraphQL field names to SPARQL variables at one nesting level.

    Produced during translation, consumed by the converter.
    """

    subject_var: Variable
    """SPARQL variable for the current subject at this nesting level."""

    fields: dict[str, Variable]
    """Scalar field name → bound variable."""

    relationships: dict[str, tuple[Variable, VariableMap]]
    """Relationship field name → (child subject variable, child map)."""


@dataclasses.dataclass(frozen=True)
class TranslationResult:
    """Output of :func:`~fastshaql.core.translation.query.translate_query`."""

    query: SelectQuery
    """Renderable SPARQL SELECT query."""

    var_map: VariableMap
    """Variable map for recursive row grouping."""


class VariableAllocator:
    """Assigns unique SPARQL variables from GraphQL field-name stems within scopes."""

    def __init__(self) -> None:
        self._scope_stack: list[str] = []
        self._used: set[str] = set()

    def push_scope(self, prefix: str) -> None:
        """Enter a nested relationship scope with *prefix* (the field name)."""
        self._scope_stack.append(prefix)

    def pop_scope(self) -> None:
        """Leave the current nested scope."""
        self._scope_stack.pop()

    def allocate(self, stem: str) -> Variable:
        """Return a scoped unique variable for *stem*.

        At root: ``?{stem}``. In scope ``employer``: ``?employer_{stem}``.
        Nested scopes join with underscores: ``?knows_knows_iri``.
        Collisions append ``_2``, ``_3``, … globally.
        """
        scoped = "_".join([*self._scope_stack, stem]) if self._scope_stack else stem
        if scoped not in self._used:
            self._used.add(scoped)
            return Variable(scoped)
        for suffix in count(2):
            candidate = f"{scoped}_{suffix}"
            if candidate not in self._used:
                self._used.add(candidate)
                return Variable(candidate)
        raise AssertionError(
            "unreachable"
        )  # pragma: no cover — count(2) always finds unused name
