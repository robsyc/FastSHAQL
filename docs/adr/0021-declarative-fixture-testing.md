# ADR-0021 — Declarative fixture testing

**Status:** Active

## Decision

**Tests as data.** RDF and GraphQL/SPARQL are declarative, so e2e test cases are defined as data — co-located shapes/data plus per-"case" `query.graphql` and expected JSON/SPARQL — driven by **explicit** pytest modules, not directory auto-discovery. Cases stay minimal, focused, readable; the tier vocabulary and harness mechanics live in `tests/README.md`.

**Five tiers, each with a contract** (what it tests / how it builds inputs / what it asserts):


| Tier        | What                                        | Inputs                 | Asserts                                |
| ----------- | ------------------------------------------- | ---------------------- | -------------------------------------- |
| unit        | one module's public interface               | hand-built             | direct values, error paths             |
| integration | 2+ modules composed                         | shared fixtures        | produced SPARQL, variable maps         |
| e2e         | full pipeline                               | declarative case files | GraphQL JSON + executed-SPARQL goldens |
| evaluation  | parity + performance vs a real triple store | generated scenarios    | Same as e2e + timing metrics           |
| adapter     | HTTP contract per adapter                   | framework test clients | envelope behaviour                     |


Tier markers are stamped automatically from the `tests/tiers/` directory — no per-test decoration.

**Registries are explicit, not auto-discovered.** Which case directories run is an opt-in registry; a case can live on disk but stay opted out (work-in-progress) by being unlisted.

**Cases vs scenarios — the provenance/scale seam.** Correctness cases are hand-authored, committed, small, run every CI against the in-memory store; evaluation scenarios generate uncommitted synthetic data at scale against a real store. Two roots, two registries, two guards, sharing only the low-level case-loading and execute-against-store primitives. Scenario axes are flat parameter mappings so each scenario names its own (`entities`, `multi_value`, `langs`, `depth`, …) without the harness knowing parameter names.

`data` **is an explicit argument** to `run_case` — the caller controls provenance; case loading stays strictly read-only.

**Self-describing fixtures (the metadata contract).** A shapes graph declares what it is; a case declares what it proves: the `graphql:Schema` resource carries `rdfs:comment` — consumed as the built `GraphQLSchema` description; node shapes carry `rdfs:comment`; property shapes carry `sh:description`; `sh:intent` bullets add optional why-this-shape-exists prose (inert for now). Case prose is the GraphQL operation's `"""description"""` in `query.graphql` echoed by the runner on golden mismatches. `data.ttl` comments stay informal.

**The case contract.** Per case, all required: `query.graphql` (named operation + description), `expected.json`, `expected.sparql` (the executed-query golden, byte-asserted), and `config.json` — the request-scoped envelope (`lang_tags` / `read_graphs`, strict keys, `{}` when empty). At the set root: `shapes.ttl` (with exactly one described `graphql:Schema`) and `data.ttl`/`data.trig`.

## Consequences

- Adding a scenario is one directory, one generator function, one registry entry
- Expected exceptions, parse/build failures, and behaviour without an operation or dataset stay in unit/integration — imperative tests, not fixtures
- Fixture metadata doubles as GraphQL schema documentation (types, fields, root fields, the schema itself) and is the seed of the docs/playground site (ROADMAP) — one authoring pass, three consumers (GraphiQL, site, failure output)
- Scenarios carry shape-level metadata only; their smoke anchors are not cases and follow no case contract
