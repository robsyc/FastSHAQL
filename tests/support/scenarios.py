"""Generated-data scenarios for evaluation: scale-parametric data + degradation sweeps.

A *scenario* is a case source whose data is synthetically generated (rather than
hand-authored) and that carries a scale axis for performance-degradation probing.
Scenario data lives under ``tests/fixtures/scenarios/<name>/``: committed
``shapes.ttl`` + correctness-anchor cases (``smoke/``); the generated ``data.ttl``
is gitignored (produced by ``generate.py`` for manual runs, or in-memory by the
harness via ``Scenario.data_at``).

Each scenario declares its own generator and names its own scale parameters; the
harness is parameter-name agnostic. Contrast ``support.cases`` (hand-authored,
committed data, correctness e2e). See ADR-0021 (tier model and the
cases/scenarios split).
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from rdflib import Graph

from support.cases import E2eCase, load_case_from

SCENARIOS_ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "scenarios"


@dataclass(frozen=True)
class Scale:
    """One point on a scenario's scale axis.

    A flat ``params`` mapping lets each scenario name its own axes
    (``entities`` / ``multi_value`` / ``langs`` / ``depth`` …) without the harness
    knowing the parameter names. Frozen → hashable → cacheable.
    """

    params: Mapping[str, int]
    label: str


# Pure: Scale → Turtle text (deterministic, seeded). No I/O.
DataGenerator = Callable[[Scale], str]


@dataclass(frozen=True)
class Scenario:
    """One generated-data scenario under ``tests/fixtures/scenarios/<name>/``.

    Satisfies ``support.cases.CaseSource`` structurally (``name`` + ``load_case``),
    so the same ``run_case`` / ``run_case_on_store`` runners serve cases and scenarios.
    """

    name: str
    cases: tuple[str, ...]
    generator: DataGenerator
    anchor_scale: Scale
    sweep: tuple[Scale, ...]
    # Prose for report rendering, one or two lines: exercises X;
    # scale axis Y; expected degradation Z.
    notes: str

    @property
    def root(self) -> Path:
        return SCENARIOS_ROOT / self.name

    def shapes_path(self) -> Path:
        return self.root / "shapes.ttl"

    def case_dir(self, case: str) -> Path:
        return self.root / case

    def load_case(self, case: str) -> E2eCase:
        return load_case_from(self.case_dir(case), case)

    def data_at(self, scale: Scale) -> Graph:
        """Generate scenario data at *scale* in-memory (pure — no disk write)."""
        graph = Graph()
        graph.parse(data=self.generator(scale), format="turtle")
        return graph


# Entity IRIs are hashed (not index-labelled) so nothing downstream can quietly
# lean on lexical IRI order; each scenario mints within its own namespace.
def _mint_iri(namespace: str, seed: int, *parts: str) -> str:
    digest = hashlib.sha256(f"{seed}|{'|'.join(parts)}".encode()).hexdigest()[:12]
    return f"{namespace}{digest}"


# ---------------------------------------------------------------------------
# Cartesian row-explosion scenario (ADR-0014). One child per Thing; per-entity
# row count is K^4 (K tags x K altLabels x K child-tags x K child-altLabels).
# Distinct lexical forms keep the dedup-coercion wrinkle observable, not masked.
# ---------------------------------------------------------------------------

_CARTESIAN_NS = "http://example.org/cartesian/"


def _emit_cartesian_data(*, entities: int, multi_value: int, seed: int = 0) -> str:
    lines = ["@prefix ex: <http://example.org/> .\n\n"]
    for i in range(entities):
        thing = f"<{_mint_iri(_CARTESIAN_NS, seed, 'thing', str(i))}>"
        child = f"<{_mint_iri(_CARTESIAN_NS, seed, 'child', str(i))}>"
        lines.append(f"{thing} a ex:Thing .\n")
        for slot in range(multi_value):
            lines.append(f'{thing} ex:tag "tag-e{i}-v{slot}" .\n')
            lines.append(f'{thing} ex:altLabel "alt-e{i}-v{slot}" .\n')
        lines.append(f"{thing} ex:hasChild {child} .\n")
        lines.append(f"{child} a ex:Child .\n")
        for slot in range(multi_value):
            lines.append(f'{child} ex:tag "ctag-e{i}-v{slot}" .\n')
            lines.append(f'{child} ex:altLabel "calt-e{i}-v{slot}" .\n')
    return "".join(lines)


def _generate_cartesian(scale: Scale) -> str:
    return _emit_cartesian_data(**scale.params)


CARTESIAN = Scenario(
    name="cartesian",
    cases=("smoke",),
    generator=_generate_cartesian,
    anchor_scale=Scale({"entities": 1, "multi_value": 2}, "anchor"),
    notes=(
        "Exercises cross-product row explosion with dedup coercion (ADR-0014); "
        "scale axis multi_value (per-entity row count K^4); expected degradation "
        "superlinear in materialized row count."
    ),
    sweep=(
        Scale({"entities": 10, "multi_value": 2}, "N10-K2"),
        Scale({"entities": 50, "multi_value": 2}, "N50-K2"),
        Scale({"entities": 50, "multi_value": 4}, "N50-K4"),
        Scale({"entities": 100, "multi_value": 4}, "N100-K4"),
        Scale({"entities": 50, "multi_value": 8}, "N50-K8"),
    ),
)

# ---------------------------------------------------------------------------
# Deep-nesting scenario. A self-referencing tree: ex:Node --ex:hasChild--> ex:Node,
# each entity a chain of the requested depth (one child per node). The smoke
# query nests a FIXED 3 hasChild levels and every node is a target-class root,
# so a deeper chain surfaces more root entities: the depth axis grows root
# count (per-level regrouping at fixed query depth), not grouping depth — and
# row cardinality stays linear in nodes.
# ---------------------------------------------------------------------------

_DEEP_NESTING_NS = "http://example.org/deep-nesting/"


def _emit_deep_nesting_data(*, entities: int, depth: int, seed: int = 0) -> str:
    lines = ["@prefix ex: <http://example.org/> .\n\n"]
    for i in range(entities):
        for d in range(depth + 1):
            node = f"<{_mint_iri(_DEEP_NESTING_NS, seed, 'node', str(i), str(d))}>"
            lines.append(f"{node} a ex:Node .\n")
            lines.append(f'{node} ex:label "label-e{i}-d{d}" .\n')
            if d < depth:
                child = (
                    f"<{_mint_iri(_DEEP_NESTING_NS, seed, 'node', str(i), str(d + 1))}>"
                )
                lines.append(f"{node} ex:hasChild {child} .\n")
    return "".join(lines)


def _generate_deep_nesting(scale: Scale) -> str:
    return _emit_deep_nesting_data(**scale.params)


DEEP_NESTING = Scenario(
    name="deep-nesting",
    cases=("smoke",),
    generator=_generate_deep_nesting,
    anchor_scale=Scale({"entities": 2, "depth": 3}, "anchor"),
    notes=(
        "Exercises nested-selection row grouping (the smoke query nests a "
        "fixed 3 levels); scale axis entities/depth — depth grows root-entity "
        "count at fixed query depth, not deeper grouping; expected degradation "
        "per-level regrouping cost."
    ),
    sweep=(
        Scale({"entities": 2, "depth": 3}, "d3-e2"),
        Scale({"entities": 2, "depth": 6}, "d6-e2"),
        Scale({"entities": 10, "depth": 4}, "d4-e10"),
        Scale({"entities": 50, "depth": 4}, "d4-e50"),
        Scale({"entities": 100, "depth": 4}, "d4-e100"),
    ),
)

# ---------------------------------------------------------------------------
# Derived-heavy scenario. Five derived fields (SHACL 1.2 node expressions at
# sh:values, all flat tier: pathValues lookup, CONCAT select, if/exists,
# exists boolean, constant) over four asserted scalars on one shape. Field
# count is static; entities is the axis — the flat-tier expression cost is
# per-row, so it should scale linearly, never super-linearly.
# ---------------------------------------------------------------------------

_DERIVED_HEAVY_NS = "http://example.org/derived-heavy/"


def _emit_derived_heavy_data(*, entities: int, seed: int = 0) -> str:
    lines = ["@prefix ex: <http://example.org/> .\n\n"]
    for i in range(entities):
        thing = f"<{_mint_iri(_DERIVED_HEAVY_NS, seed, 'thing', str(i))}>"
        lines.append(f"{thing} a ex:Thing .\n")
        lines.append(f'{thing} ex:givenName "Given-e{i}" .\n')
        lines.append(f'{thing} ex:familyName "Family-e{i}" .\n')
        lines.append(f'{thing} ex:shortName "Short-e{i}" .\n')
        # Even entities carry a review so the if/exists derivations exercise
        # both branches; odd entities take the else/unreviewed lane.
        if i % 2 == 0:
            lines.append(f'{thing} ex:review "review-e{i}" .\n')
    return "".join(lines)


def _generate_derived_heavy(scale: Scale) -> str:
    return _emit_derived_heavy_data(**scale.params)


DERIVED_HEAVY = Scenario(
    name="derived-heavy",
    cases=("smoke",),
    generator=_generate_derived_heavy,
    anchor_scale=Scale({"entities": 2}, "anchor"),
    notes=(
        "Exercises flat-tier sh:values derivation (5 derived fields over 4 "
        "asserted scalars; if/exists branches via even/odd entities); scale "
        "axis entities; expected degradation linear per-row expression cost."
    ),
    sweep=(
        Scale({"entities": 10}, "N10"),
        Scale({"entities": 50}, "N50"),
        Scale({"entities": 100}, "N100"),
        Scale({"entities": 500}, "N500"),
        Scale({"entities": 1000}, "N1000"),
    ),
)

# ---------------------------------------------------------------------------
# Lang-multiplicity scenario. One langString title per document per language
# (en, nl, fr, ... up to ``langs``); the smoke case resolves through the
# [en, nl, ""] preference chain. ``langs`` is the axis: every step of the chain
# is another OPTIONAL+FILTER per field, so chain-resolution cost grows with the
# language multiplicity of the underlying literals.
# ---------------------------------------------------------------------------

_LANG_MULTIPLICITY_NS = "http://example.org/lang-multiplicity/"

# Fixed tag pool (first ``langs`` entries used) — BCP 47 primary tags, no
# subtags, so no two steps of a chain ever overlap via prefix matching.
_LANG_MULTIPLICITY_LANGS = ("en", "nl", "fr", "de", "es", "it", "pt", "sv")


def _emit_lang_multiplicity_data(*, entities: int, langs: int, seed: int = 0) -> str:
    lines = ["@prefix ex: <http://example.org/> .\n\n"]
    for i in range(entities):
        doc = f"<{_mint_iri(_LANG_MULTIPLICITY_NS, seed, 'doc', str(i))}>"
        lines.append(f"{doc} a ex:Doc .\n")
        lines.extend(
            f'{doc} ex:title "Title-e{i}-{lang}"@{lang} .\n'
            for lang in _LANG_MULTIPLICITY_LANGS[:langs]
        )
    return "".join(lines)


def _generate_lang_multiplicity(scale: Scale) -> str:
    return _emit_lang_multiplicity_data(**scale.params)


LANG_MULTIPLICITY = Scenario(
    name="lang-multiplicity",
    cases=("smoke",),
    generator=_generate_lang_multiplicity,
    anchor_scale=Scale({"entities": 2, "langs": 2}, "anchor"),
    notes=(
        "Exercises language-preference-chain lowering — each chain step is "
        "another OPTIONAL+FILTER over the literal multiplicity (the ROADMAP "
        "chain-efficiency prerequisite); scale axis langs; expected "
        "degradation chain-resolution cost growing with multiplicity."
    ),
    sweep=(
        Scale({"entities": 100, "langs": 2}, "N100-L2"),
        Scale({"entities": 100, "langs": 4}, "N100-L4"),
        Scale({"entities": 100, "langs": 8}, "N100-L8"),
        Scale({"entities": 500, "langs": 4}, "N500-L4"),
        Scale({"entities": 1000, "langs": 4}, "N1000-L4"),
    ),
)

# ---------------------------------------------------------------------------
# Wide-results scenario. Rows with ten selected fields (eight single-valued
# scalars, a two-value tag list, a two-part relationship) so the decoded SPARQL
# row is wide before it is tall. Entities is the axis with parts pinned at 2 —
# decode/convert cost should track row count (entities x parts) at fixed width.
# ---------------------------------------------------------------------------

_WIDE_RESULTS_NS = "http://example.org/wide-results/"


def _emit_wide_results_data(*, entities: int, parts: int, seed: int = 0) -> str:
    lines = ["@prefix ex: <http://example.org/> .\n\n"]
    for i in range(entities):
        row = f"<{_mint_iri(_WIDE_RESULTS_NS, seed, 'row', str(i))}>"
        lines.append(f"{row} a ex:Row .\n")
        lines.append(f'{row} ex:code "code-e{i}" .\n')
        lines.append(f'{row} ex:name "name-e{i}" .\n')
        lines.append(f'{row} ex:description "description-e{i}" .\n')
        lines.append(f'{row} ex:category "category-e{i}" .\n')
        lines.append(f"{row} ex:quantity {i} .\n")
        lines.append(f"{row} ex:sequence {i} .\n")
        lines.append(f"{row} ex:weight {i} .\n")
        lines.append(f"{row} ex:version {i} .\n")
        lines.append(f'{row} ex:tag "tag-e{i}-a" .\n')
        lines.append(f'{row} ex:tag "tag-e{i}-b" .\n')
        for j in range(parts):
            part = f"<{_mint_iri(_WIDE_RESULTS_NS, seed, 'part', str(i), str(j))}>"
            lines.append(f"{row} ex:hasPart {part} .\n")
            lines.append(f"{part} a ex:Part .\n")
            lines.append(f'{part} ex:partCode "part-e{i}-{j}" .\n')
            lines.append(f'{part} ex:partName "Part-name-e{i}-{j}" .\n')
    return "".join(lines)


def _generate_wide_results(scale: Scale) -> str:
    return _emit_wide_results_data(**scale.params)


WIDE_RESULTS = Scenario(
    name="wide-results",
    cases=("smoke",),
    generator=_generate_wide_results,
    anchor_scale=Scale({"entities": 3, "parts": 1}, "anchor"),
    notes=(
        "Exercises wide-row decoding (13 projected variables per row); scale "
        "axis entities with parts pinned at 2, capped at 2000 rows; expected "
        "degradation superlinear wide-join cost in stores."
    ),
    # Capped at 2000 materialized rows: OSS stores answer the wide join
    # superlinearly (Oxigraph: 0.06s @ 100 rows → 8.9s @ 2000), and larger
    # points overwhelm a serial 12-sample harness — cartesian already probes
    # big row explosions.
    sweep=(
        Scale({"entities": 50, "parts": 2}, "N50-P2"),
        Scale({"entities": 100, "parts": 2}, "N100-P2"),
        Scale({"entities": 250, "parts": 2}, "N250-P2"),
        Scale({"entities": 500, "parts": 2}, "N500-P2"),
    ),
)

# Canonical scenario registry — single source of truth (mirrors
# support.cases.CASES). Alphabetical by scenario name.
SCENARIOS: dict[str, Scenario] = {
    "cartesian": CARTESIAN,
    "deep-nesting": DEEP_NESTING,
    "derived-heavy": DERIVED_HEAVY,
    "lang-multiplicity": LANG_MULTIPLICITY,
    "wide-results": WIDE_RESULTS,
}
