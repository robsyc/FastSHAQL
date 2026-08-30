# ADR-0003 — Enforced module boundaries (tach)

**Status:** Active

## Context

The package's layering (ADR-0001's Core/Adapter split; load → parse → schema → translate → render → store → convert) was enforced only by a framework-import test and convention. Deep refactoring needed a mechanical gate keeping the import graph a DAG matching the architecture, and the public API needed a pinned surface — adapters and the demo were importing stage internals directly.

## Decision

- **Fine-grained tach modules** (`tach.toml`, `just architecture`, blocking in CI) in a strict DAG matching the architecture, with `exact = true` (declared-but-unused dependencies fail), `forbid_circular_dependencies`, and `root_module = "forbid"`. The module decomposition itself lives in `tach.toml` and the DAG diagram in `docs/ARCHITECTURE.md` — they are the source of truth, not this record.
- **Single-module pins**: `parser/` and `translation/` are each one tach module. Their internal parent↔child import cycles are a design property (recursive descent over mutually referring nodes) and stay hidden inside the module instead of being banned apart.
- **Interfaces pinned at exactly three seams**: root `fastshaql` = the three entry points; `fastshaql.core` = the advanced surface (the `core/__init__` re-export list, every symbol with a real in-repo consumer); `fastshaql.adapters` = the two builders. Stage modules carry **no** interface — tests legitimately import stage internals, so stage internality stays a doc-level rule, not a config one.
- **Composition root at the package root** (`fastshaql/executable.py`): `fastshaql.core` does **not** re-export `build_executable_schema` — root-only — so the DAG is strictly downward. An earlier draft had core-init re-export from the root, which made `fastshaql.core` sit above the root package and made import order in `fastshaql/__init__` load-bearing (reordering two imports crashed with a partial-initialization `ImportError`); with no upward edge there is no ordering constraint at all.
- **Two rejected forks, recorded with revisit triggers**:
  - *envelope in adapters* — would permanently foreclose the envelope symbols from the `fastshaql.core` surface (core-init can never re-export from adapters without a cycle). Revisit if a consumer that is neither adapter nor core-dependent needs the envelope.
  - *kernel strictly bottom* — moving the `ComparisonOp` alias out of `sparql` would give `sparql` — the zero-fastshaql-dependency pure SPARQL AST library — a fastshaql dependency. The load-bearing invariant is sparql's purity, not kernel's position. Revisit if sparql is ever extracted into its own distribution.

`tests/` and `demo/` sit outside the source roots: tach governs `src` only, and the evaluation tier imports the demo workspace member, which must stay un-checkable by construction.

## Consequences

- Adding a cross-stage import now requires a deliberate `tach.toml` edit and fails CI otherwise — architecture drift is a build failure, not a review comment
- `just module-graph` regenerates the mermaid DAG in `docs/ARCHITECTURE.md` between markers (manual — the diagram is documentation)
