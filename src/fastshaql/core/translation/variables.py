"""Scoped SPARQL variable allocation and translation variable mapping.

See: docs/adr/0013-ast-driven-translation.md
"""

from __future__ import annotations

import dataclasses
from itertools import count
from typing import TYPE_CHECKING

from rdflib import URIRef, Variable

if TYPE_CHECKING:
    from fastshaql.core.sparql import SelectQuery


@dataclasses.dataclass(frozen=True)
class MemberBinding:
    """One union member lane's conversion binding (ADR-0026). ``class_iri``
    is the member discriminator — ``None`` on the degenerate single-target
    member (incl. the binding-union row)."""

    class_iri: URIRef | None
    map: VariableMap


@dataclasses.dataclass(frozen=True)
class RelationshipBinding:
    """A relationship field's row-conversion binding (ADR-0014, extended by
    ADR-0026): the child subject variable plus one member map per lane.
    ``discriminator`` is set iff the field lowers as a union type — then the
    converter stamps ``__typename`` by member-order priority; single-target
    relationships (asserted, derived, or the binding-union row) carry one
    member and no discriminator."""

    subject_var: Variable
    members: tuple[MemberBinding, ...]
    discriminator: Variable | None = None

    @classmethod
    def single(
        cls, subject_var: Variable, child_map: VariableMap
    ) -> RelationshipBinding:
        """Construct the degenerate single-target form — one member, no
        discriminator (asserted, derived, and binding-union relationships)."""
        return cls(
            subject_var=subject_var,
            members=(MemberBinding(None, child_map),),
        )

    @property
    def single_map(self) -> VariableMap:
        """The map of a single-target binding."""
        if self.discriminator is not None or len(self.members) != 1:
            raise ValueError(  # pragma: no cover — single-target construction invariant
                "single_map on a polymorphic binding — read its members instead"
            )
        return self.members[0].map


@dataclasses.dataclass(frozen=True)
class VariableMap:
    """Maps GraphQL field names to SPARQL variables at one nesting level.

    Produced during translation, consumed by the converter.
    """

    subject_var: Variable
    """SPARQL variable for the current subject at this nesting level."""

    fields: dict[str, Variable]
    """Scalar field name → bound variable."""

    relationships: dict[str, RelationshipBinding]
    """Relationship field name → conversion binding."""


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

    def reserve(self, name: str) -> Variable:
        """Mark *name* taken — for variables minted outside the allocator
        (name-derived guards); returns it unchanged, never suffixes. A
        taken name rejects loudly: silently aliasing an allocated variable
        would corrupt both bindings."""
        if name in self._used:
            raise ValueError(f"?{name} is already taken — cannot reserve")
        self._used.add(name)
        return Variable(name)
