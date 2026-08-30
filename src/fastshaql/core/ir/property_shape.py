"""``sh:PropertyShape`` — value constraints on a single ``sh:path``.

Includes ``FieldKind`` (GraphQL cardinality derived from ``sh:minCount`` /
``sh:maxCount``), computed by :attr:`PropertyShapeIR.kind`.

See:
- https://www.w3.org/TR/shacl12-core/#property-shapes
- https://www.w3.org/TR/shacl12-core/#core-components-count
"""

from __future__ import annotations

import dataclasses
import enum
from functools import cached_property
from typing import TYPE_CHECKING

from rdflib.namespace import XSD

from fastshaql.core.kernel.constants import LANGUAGE_DATATYPES
from fastshaql.core.kernel.identifiers import enum_member_names

from .base import ShapeIR

if TYPE_CHECKING:
    from rdflib import URIRef
    from rdflib.term import Node

    from .node_expr import NodeExprIR
    from .shacl_path import ShaclPropertyPath


class FieldKind(enum.Enum):
    """GraphQL field multiplicity implied by SHACL cardinality — not a SHACL term."""

    REQUIRED_SCALAR = "required_scalar"
    """``minCount >= 1``, ``maxCount == 1`` — maps to ``field: Type!``."""

    OPTIONAL_SCALAR = "optional_scalar"
    """``minCount == 0``, ``maxCount == 1`` — maps to ``field: Type``."""

    REQUIRED_LIST = "required_list"
    """``minCount >= 1``, ``maxCount > 1`` or absent — maps to ``field: [Type!]!``."""

    OPTIONAL_LIST = "optional_list"
    """``minCount == 0``, ``maxCount > 1`` or absent — maps to ``field: [Type!]``."""

    @property
    def is_required(self) -> bool:
        """True when ``minCount >= 1``."""
        return self in (FieldKind.REQUIRED_SCALAR, FieldKind.REQUIRED_LIST)

    @property
    def is_list(self) -> bool:
        """True when ``maxCount`` is absent or ``> 1``."""
        return self in (FieldKind.REQUIRED_LIST, FieldKind.OPTIONAL_LIST)


class ValueType(enum.Enum):
    """What a property's values *are* — the type axis of the two-axis
    classification (ADR-0004).

    Single source of truth for the type axis — consumers ``match`` on this so
    a missed branch is a non-exhaustive-match error rather than silent
    wrong-SPARQL. Precedence: **relationship** > **enum** > **scalar**.
    Orthogonal to :class:`ValueSource` (how values are obtained).
    """

    RELATIONSHIP = "relationship"
    """``sh:class`` / ``sh:node`` — navigates to another shape."""

    ENUM = "enum"
    """Non-relationship ``sh:in`` — maps to a GraphQL enum."""

    SCALAR = "scalar"
    """A literal datatype field."""


class ValueSource(enum.Enum):
    """How a property's values are *obtained* — the source axis of the
    two-axis classification (ADR-0004).

    Binary presence of ``sh:values``. Only the value-binding splice sites
    (``scalar_bind_patterns``, the relationship join) dispatch on this axis.
    """

    ASSERTED = "asserted"
    """Triples at the path."""

    DERIVED = "derived"
    """Evaluated by a node expression (``sh:values``, ADR-0015)."""


class LiteralSpace(enum.Enum):
    """A scalar Property's classification on the datatype axis — the
    parse-side input to language-preference-chain semantics (ADR-0012).

    Distinct from :class:`ValueType` (the type axis: what values *are*);
    the literal space subclasses the scalar arm only. Total over
    parser-producible datatype sets: anything the parser accepts classifies
    into exactly one space.
    """

    PLAIN = "plain"
    """Datatypes empty, or all non-language datatypes — the chain ignores
    such a Property entirely."""

    LANGUAGE = "language"
    """Datatypes ⊆ {``rdf:langString``, ``rdf:dirLangString``} and non-empty —
    every value is language-tagged; the chain applies strictly (no implicit
    terminal)."""

    UNION = "union"
    """Datatypes span ≥1 language type and ≥1 ``xsd:string`` and nothing else
    — a **string-union Property**; the chain applies with an implicit
    untagged terminal appended last."""


@dataclasses.dataclass(frozen=True, kw_only=True)
class PropertyShapeIR(ShapeIR):
    """Parsed ``sh:PropertyShape``. Exactly one ``path`` (SHACL §3.3).

    Two-axis classification (ADR-0004): :attr:`value_type`
    (**relationship** > **enum** > **scalar**) x :attr:`source`
    (**asserted** | **derived**). ``sh:in`` on a relationship is stored but
    read-ignored (overlay). Datatype-only ``sh:or`` normalizes into
    :attr:`datatypes`; any other ``sh:or`` is parse-recognized-and-inert.
    Deferred: ``sh:and``/``sh:not``.
    """

    graphql_field_name: str
    """Adapter-facing GraphQL field name. Resolution: ``sh:codeIdentifier``, else
    local name of the predicate in ``path`` (SHACL 1.2 §8.4). Not a SHACL term."""

    path: ShaclPropertyPath
    """SHACL property path. Parser: ``sh:path`` (SHACL §4)."""

    datatypes: tuple[URIRef, ...] = ()
    """Declared literal datatype constraints, order preserved from the shape
    (order carries no semantics but is kept for messages — multi-entry
    sets are UNION by parser rule, so first-entry access is
    order-invariant). Parser: ``sh:datatype`` as an IRI or SHACL list
    (SHACL 1.2 §7.1.2), or the datatype-only ``sh:or`` form. Singleton for
    the plain IRI form; a multi-entry set is restricted to the string
    family (parser rule)."""

    min_count: int | None = None
    """Minimum value count. Parser: ``sh:minCount`` (SHACL §7.2.1)."""

    max_count: int | None = None
    """Maximum value count. Parser: ``sh:maxCount`` (SHACL §7.2.2)."""

    value_class: URIRef | None = None
    """Target class IRI. Parser: ``sh:class`` (SHACL §7.1.1).
    Emitted as type triple in SPARQL translation. Distinct from ``target_class`` on :class:`NodeShapeIR`
    ``sh:class`` is a value constraint, ``sh:targetClass`` is a targeting mechanism."""

    value_shape_iri: URIRef | None = None
    """IRI of the resolved target shape for relationship properties.
    Populated in :func:`~fastshaql.core.parser.parse_shapes`
    from ``sh:class`` (via ``by_target_class``; SHACL §7.1.1)
    or ``sh:node`` (via ``by_iri``; SHACL §7.8.1)."""

    in_values: tuple[Node, ...] | None = None
    """Closed value set from ``sh:in`` (SHACL §7.9.3), preserving rdflib terms."""

    values_expr: NodeExprIR | None = None
    """Node expression from ``sh:values`` (ADR-0015); ``None`` for asserted fields.
    Parsed by ``core/parser/node_expr/parse.py``; emitted in place of the
    ``?this sh:path ?var`` triple by the translation dispatcher."""

    default_expr: NodeExprIR | None = None
    """Node expression from ``sh:defaultValue`` (SHACL Core §3.3, §6.8.2
    step 3 — ADR-0015); ``None`` when absent. Scalar-only (maxCount
    1, statically single-valued): the fallback fires when the path/values
    yield nothing, lowered as ``OPTIONAL { … } BIND(COALESCE(?v, d) AS ?out)``
    — per-entity set-emptiness is flat-expressible exactly in the single-value
    case. A defaulted field is non-nullable (SD-6)."""

    @property
    def datatype(self) -> URIRef | None:
        """The sole declared datatype, or ``None`` for empty/union sets;
        space-aware consumers dispatch on :attr:`literal_space` instead."""
        if len(self.datatypes) == 1:
            return self.datatypes[0]
        return None

    @property
    def literal_space(self) -> LiteralSpace:
        """The datatype-axis classification (:class:`LiteralSpace`).

        Meaningful on the scalar arm (value-type precedence is untouched).
        Raises for a set mixing a language type with a non-string
        non-language type — the parser rejects those loudly (multi-entry
        sets are restricted to the string family), so they never reach the
        IR; direct construction fails here rather than misclassifying.
        """
        if not any(dt in LANGUAGE_DATATYPES for dt in self.datatypes):
            return LiteralSpace.PLAIN
        non_language = [dt for dt in self.datatypes if dt not in LANGUAGE_DATATYPES]
        if all(dt == XSD.string for dt in non_language):
            return LiteralSpace.UNION if non_language else LiteralSpace.LANGUAGE
        raise ValueError(
            f"property {self.graphql_field_name!r} mixes language-tagged and "
            "non-string datatypes — unsupported (the parser restricts "
            "multi-entry datatype sets to the string family)"
        )

    @property
    def kind(self) -> FieldKind:
        """GraphQL cardinality pattern derived from ``min_count`` /
        ``max_count`` — the single home of the field's nullability.

        ``minCount >= 1`` is required; ``maxCount == 1`` is scalar; otherwise
        list. A defaulted field (``default_expr``) is non-null at any
        ``minCount`` (SD-6): the ``COALESCE`` always binds the value
        variable, and the path must stay optional so the default can serve
        the entities it fills — exact for the scalar-only default boundary
        the parser enforces.
        """
        required = (self.min_count or 0) >= 1 or self.default_expr is not None
        scalar = self.max_count == 1
        if scalar:
            return FieldKind.REQUIRED_SCALAR if required else FieldKind.OPTIONAL_SCALAR
        return FieldKind.REQUIRED_LIST if required else FieldKind.OPTIONAL_LIST

    @property
    def value_type(self) -> ValueType:
        """What this property's values are — the type axis (ADR-0004).

        ``relationship`` > ``enum`` > ``scalar``. This axis is independent of
        :attr:`source`: ``sh:values`` + ``sh:class``/``sh:node`` is a *derived
        relationship* and ``sh:values`` + ``sh:in`` a *derived enum* (ADR-0015) —
        both land on their arm here and carry
        ``ValueSource.DERIVED``.
        """
        if self.value_class is not None or self.value_shape_iri is not None:
            return ValueType.RELATIONSHIP
        if self.in_values is not None:
            return ValueType.ENUM
        return ValueType.SCALAR

    @property
    def source(self) -> ValueSource:
        """How this property's values are obtained — the source axis."""
        if self.values_expr is not None:
            return ValueSource.DERIVED
        return ValueSource.ASSERTED

    @cached_property
    def enum_term_by_name(self) -> dict[str, Node]:
        """Map GraphQL enum member NAME to the original rdflib term."""
        if self.in_values is None:
            return {}  # pragma: no cover — enum filters only built for properties with sh:in
        return dict(zip(enum_member_names(self.in_values), self.in_values, strict=True))

    @property
    def is_language_typed(self) -> bool:
        """Whether this Property accepts language-tagged values: the LANGUAGE
        and UNION literal spaces (:attr:`literal_space`). ``sh:languageIn``
        support would re-key language-awareness beyond datatype alone.
        """
        return self.literal_space in (LiteralSpace.LANGUAGE, LiteralSpace.UNION)
